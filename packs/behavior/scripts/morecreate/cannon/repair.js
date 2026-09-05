/**
 * Keeps every placed Schematic Cannon paired with its inventory entity.
 *
 * The cannon's screen is the container of a hidden entity sitting inside the
 * block - the same trick Create uses for its vault. If that entity is ever
 * lost, right-clicking the cannon does nothing at all and the machine looks
 * broken with no way to recover it.
 *
 * Two things guard against that: the entity is now marked persistent, and this
 * pass re-creates it (with its control buttons) for any cannon base found
 * without one.
 */

import { world, system } from "@minecraft/server";

const CANNON_BASE = "morecreate:cannon_base";
const CANNON_ENTITY = "morecreate:cannon_entity";
const CONTAINER_NAME = "CreateCanon";

/** Control buttons and the container slot each one lives in. */
const BUTTONS = [
    [1, "morecreate:clipboard_button"],
    [6, "morecreate:stop_button"],
    [7, "morecreate:start_button"],
    [8, "morecreate:reset_button"],
    [9, "morecreate:confirm_button"],
    [10, "morecreate:configures_button"]
];

/** Slots the player fills themselves - fuel, schematic, output - stay empty. */
function fitOutButtons(entity) {
    const container = entity.getComponent("minecraft:inventory")?.container;
    if (!container) return;
    for (const [slot, itemId] of BUTTONS) {
        if (slot >= container.size) continue;
        const existing = container.getItem(slot);
        if (existing?.typeId === itemId) continue;
        try {
            entity.dimension.runCommand(
                `item replace entity @e[type=${CANNON_ENTITY},x=${Math.floor(entity.location.x)},` +
                `y=${Math.floor(entity.location.y)},z=${Math.floor(entity.location.z)},r=1] ` +
                `slot.inventory ${slot} with ${itemId} 1`);
        } catch {
            /* older command syntax, or the chunk went away */
        }
    }
}

function cannonEntityAt(dimension, location) {
    try {
        return dimension.getEntities({
            type: CANNON_ENTITY,
            location: { x: location.x + 0.5, y: location.y, z: location.z + 0.5 },
            maxDistance: 1.2
        })[0];
    } catch {
        return undefined;
    }
}

/** Give a cannon base its inventory entity back. */
export function ensureCannonEntity(dimension, location) {
    let block;
    try {
        block = dimension.getBlock(location);
    } catch {
        return false;
    }
    if (block?.typeId !== CANNON_BASE) return false;
    if (cannonEntityAt(dimension, location)) return false;

    let entity;
    try {
        entity = dimension.spawnEntity(CANNON_ENTITY, {
            x: location.x + 0.5, y: location.y, z: location.z + 0.5
        });
    } catch {
        return false;
    }
    try { entity.nameTag = CONTAINER_NAME; } catch {}
    fitOutButtons(entity);
    return true;
}

export function initCannonRepair() {
    // Right-clicking a cannon that lost its entity puts it back, so the next
    // click opens the screen instead of doing nothing.
    world.beforeEvents.playerInteractWithBlock.subscribe((event) => {
        if (event.block?.typeId !== CANNON_BASE) return;
        const dimension = event.block.dimension;
        const location = { ...event.block.location };
        system.run(() => ensureCannonEntity(dimension, location));
    });

    // A small sweep around each player catches cannons in worlds saved before
    // this fix, without walking a large volume every tick. Right-clicking is
    // the main path; this is only a safety net, so it stays deliberately tight.
    const RADIUS = 3;
    system.runInterval(() => {
        for (const player of world.getAllPlayers()) {
            const dimension = player.dimension;
            const ox = Math.floor(player.location.x);
            const oy = Math.floor(player.location.y);
            const oz = Math.floor(player.location.z);
            for (let dx = -RADIUS; dx <= RADIUS; dx++) {
                for (let dy = -2; dy <= 2; dy++) {
                    for (let dz = -RADIUS; dz <= RADIUS; dz++) {
                        ensureCannonEntity(dimension, { x: ox + dx, y: oy + dy, z: oz + dz });
                    }
                }
            }
        }
    }, 300);
}
