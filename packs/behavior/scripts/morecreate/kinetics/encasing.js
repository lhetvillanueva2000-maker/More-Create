/**
 * Encasing: hiding a shaft or cogwheel inside a casing block.
 *
 *   right-click a shaft / cogwheel / large cogwheel with any casing
 *     -> it becomes the matching encased block
 *   right-click an encased block with a *different* casing
 *     -> the casing is swapped and the old one is returned
 *   sneak + right-click an encased block with a wrench
 *     -> the casing comes back off
 *
 * The encased shaft is a solid, full casing block with no visual entity, so the
 * shaft is hidden completely; rotation and stress keep flowing through it
 * because the block still carries Create's `create:rpm_system` component and is
 * registered with the same face wiring as a plain shaft.
 */

import { world, system, BlockPermutation, ItemStack, GameMode } from "@minecraft/server";

const CASING_ITEMS = new Map([
    ["create:andesite_casing", "andesite"],
    ["create:brass_casing", "brass"],
    ["create:copper_casing", "copper"],
    ["create:creative_casing", "creative"]
]);

const CASING_BLOCK_BY_NAME = new Map([
    ["andesite", "create:andesite_casing"],
    ["brass", "create:brass_casing"],
    ["copper", "create:copper_casing"],
    ["creative", "create:creative_casing"]
]);

/** kinetic block -> [encased suffix, state that stores its orientation] */
const ENCASABLE = new Map([
    ["create:shaft", { kind: "shaft", state: "minecraft:block_face" }],
    ["create:cogwheel", { kind: "cogwheel", state: "minecraft:facing_direction" }],
    ["create:large_cogwheel", { kind: "large_cogwheel", state: "minecraft:facing_direction" }]
]);

/** encased block -> what it was made of */
const ENCASED = new Map();
for (const [casing] of CASING_BLOCK_BY_NAME) {
    for (const [source, info] of ENCASABLE) {
        ENCASED.set(`morecreate:${casing}_encased_${info.kind}`, {
            casing,
            source,
            state: info.state
        });
    }
}

const FACE_BY_INDEX = { 0: "down", 1: "up", 2: "north", 3: "south", 4: "west", 5: "east" };

function readOrientation(block, state) {
    let value;
    try {
        value = block.permutation.getState(state);
    } catch {
        return undefined;
    }
    if (typeof value === "number") return FACE_BY_INDEX[value];
    return value;
}

function swapBlock(block, newTypeId, state, orientation) {
    const states = orientation === undefined ? {} : { [state]: orientation };
    let permutation;
    try {
        permutation = BlockPermutation.resolve(newTypeId, states);
    } catch {
        // Orientation states differ between shafts and cogwheels; fall back to
        // the default permutation rather than leaving the block untouched.
        try {
            permutation = BlockPermutation.resolve(newTypeId);
        } catch {
            return false;
        }
    }
    try {
        block.setPermutation(permutation);
    } catch {
        return false;
    }
    return true;
}

function isCreative(player) {
    try {
        return player.getGameMode() === GameMode.Creative;
    } catch {
        return false;
    }
}

function consumeMainhand(player, amount = 1) {
    if (isCreative(player)) return;
    try {
        const equippable = player.getComponent("equippable");
        const held = equippable?.getEquipment("Mainhand");
        if (!held) return;
        if ((held.amount ?? 1) <= amount) {
            equippable.setEquipment("Mainhand", undefined);
            return;
        }
        const next = held.clone();
        next.amount -= amount;
        equippable.setEquipment("Mainhand", next);
    } catch {
        /* inventory raced with another script; nothing safe to do here */
    }
}

function give(player, dimension, location, itemId) {
    if (isCreative(player)) return;
    let stack;
    try {
        stack = new ItemStack(itemId, 1);
    } catch {
        return;
    }
    try {
        const container = player.getComponent("inventory")?.container;
        if (container && container.emptySlotsCount > 0) {
            container.addItem(stack);
            return;
        }
    } catch {
        /* fall through to dropping it */
    }
    try {
        dimension.spawnItem(stack, location);
    } catch {
        /* the block was unloaded before we could drop anything */
    }
}

function playCasingSound(dimension, block) {
    try {
        dimension.playSound("use.wood", block.center(), { volume: 0.7, pitch: 1.1 });
    } catch {
        /* sound is cosmetic */
    }
}

function tryEncase(player, block, heldTypeId) {
    const casing = CASING_ITEMS.get(heldTypeId);
    if (!casing) return false;

    const existing = ENCASED.get(block.typeId);
    if (existing) {
        // Already encased - swap the casing material, unless it is the same one.
        if (existing.casing === casing) return false;
        const orientation = readOrientation(block, existing.state);
        const location = { ...block.location };
        const dimension = block.dimension;
        const target = `morecreate:${casing}_encased_${ENCASABLE.get(existing.source).kind}`;
        system.run(() => {
            const current = dimension.getBlock(location);
            if (current?.typeId !== block.typeId) return;
            if (!swapBlock(current, target, existing.state, orientation)) return;
            consumeMainhand(player);
            give(player, dimension, current.center(), CASING_BLOCK_BY_NAME.get(existing.casing));
            playCasingSound(dimension, current);
        });
        return true;
    }

    const info = ENCASABLE.get(block.typeId);
    if (!info) return false;

    const orientation = readOrientation(block, info.state);
    const location = { ...block.location };
    const dimension = block.dimension;
    const sourceType = block.typeId;
    const target = `morecreate:${casing}_encased_${info.kind}`;

    system.run(() => {
        const current = dimension.getBlock(location);
        if (current?.typeId !== sourceType) return;
        if (!swapBlock(current, target, info.state, orientation)) return;
        consumeMainhand(player);
        playCasingSound(dimension, current);
    });
    return true;
}

function tryUnencase(player, block, heldTypeId) {
    if (heldTypeId !== "create:wrench" || !player?.isSneaking) return false;
    const info = ENCASED.get(block.typeId);
    if (!info) return false;

    const orientation = readOrientation(block, info.state);
    const location = { ...block.location };
    const dimension = block.dimension;
    const encasedType = block.typeId;

    system.run(() => {
        const current = dimension.getBlock(location);
        if (current?.typeId !== encasedType) return;
        if (!swapBlock(current, info.source, info.state, orientation)) return;
        give(player, dimension, current.center(), CASING_BLOCK_BY_NAME.get(info.casing));
        playCasingSound(dimension, current);
    });
    return true;
}

export function initEncasing() {
    world.beforeEvents.playerInteractWithBlock.subscribe((event) => {
        const { player, block, itemStack, isFirstEvent } = event;
        if (!isFirstEvent || !player || !block || !itemStack) return;

        const heldTypeId = itemStack.typeId;
        if (heldTypeId !== "create:wrench" && !CASING_ITEMS.has(heldTypeId)) return;

        if (tryUnencase(player, block, heldTypeId) || tryEncase(player, block, heldTypeId)) {
            // Stop the casing from being placed as a block / the wrench from
            // running Create's own wrench handling on top of ours.
            event.cancel = true;
        }
    });
}

export { ENCASED, CASING_ITEMS };
