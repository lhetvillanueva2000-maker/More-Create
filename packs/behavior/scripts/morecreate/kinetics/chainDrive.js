/**
 * Encased Chain Drive connections, and cleanup of stranded visual entities.
 *
 * Two jobs live here:
 *
 * 1. Keeping the `morecreate:chain` block state in step with the drive's
 *    neighbours, so a row of drives renders as one continuous chain instead of
 *    a line of unconnected sprockets. Create draws the chain on the drive's
 *    *axis* faces - the faces where blocks touch are hidden between two solid
 *    blocks, so the chain would never be seen there.
 *
 * 2. Removing visual entities whose block has gone. Create's kinetic system
 *    despawns them when a block breaks, but anything that removes a block
 *    without going through that path - another add-on, a command, a piston -
 *    leaves the entity floating. It has no collision, but it still looks like a
 *    block you cannot break, so a sweep clears any that outlive their block.
 */

import { world, system } from "@minecraft/server";

const CHAIN_DRIVE = "morecreate:encased_chain_drive";
const CHAIN_STATE = "morecreate:chain";
// Drives orient by where the player is looking, like Create's own cogwheel, so
// putting one down on the ground gives a horizontal drive rather than one
// standing on end.
const FACE_STATE = "minecraft:facing_direction";

const OFFSETS = {
    north: { x: 0, y: 0, z: -1 },
    south: { x: 0, y: 0, z: 1 },
    east: { x: 1, y: 0, z: 0 },
    west: { x: -1, y: 0, z: 0 },
    up: { x: 0, y: 1, z: 0 },
    down: { x: 0, y: -1, z: 0 }
};

const FACE_BY_INDEX = { 0: "down", 1: "up", 2: "north", 3: "south", 4: "west", 5: "east" };

/**
 * Drive axis -> the two perpendicular run axes, in the order the block states
 * use. Must stay in step with `AXES` in tools/gen_chain_drive.py, which decides
 * which texture each state paints.
 */
const PERPENDICULAR = {
    z: { a: ["east", "west"], b: ["up", "down"] },
    x: { a: ["south", "north"], b: ["up", "down"] },
    y: { a: ["east", "west"], b: ["south", "north"] }
};

/** Visual entities More Create spawns, and the blocks allowed to own them. */
const VISUALS = new Map([
    ["morecreate:encased_chain_drive_entity", new Set([CHAIN_DRIVE])],
    ["morecreate:encased_cogwheel_entity", new Set([
        "morecreate:andesite_encased_cogwheel", "morecreate:brass_encased_cogwheel",
        "morecreate:copper_encased_cogwheel", "morecreate:creative_encased_cogwheel"
    ])],
    ["morecreate:encased_large_cogwheel_entity", new Set([
        "morecreate:andesite_encased_large_cogwheel", "morecreate:brass_encased_large_cogwheel",
        "morecreate:copper_encased_large_cogwheel", "morecreate:creative_encased_large_cogwheel"
    ])]
]);

function readFace(block) {
    let value;
    try {
        value = block.permutation.getState(FACE_STATE);
    } catch {
        return "north";
    }
    if (typeof value === "number") return FACE_BY_INDEX[value] ?? "north";
    return value ?? "north";
}

function axisOf(face) {
    if (face === "east" || face === "west") return "x";
    if (face === "up" || face === "down") return "y";
    return "z";
}

function blockAt(dimension, location, offset) {
    try {
        return dimension.getBlock({
            x: location.x + offset.x,
            y: location.y + offset.y,
            z: location.z + offset.z
        });
    } catch {
        return undefined;
    }
}

/**
 * Where this drive sits in its run.
 *
 * Create draws a drive with neighbours on both sides differently from one at
 * the end of a row: the end has the chain leaving one side only. Painting every
 * connected drive with the "through" texture is what made a row read as a
 * repeating pattern instead of a single chain.
 *
 * Returns "none", "mid_a"/"mid_b" for a drive with both neighbours on that run
 * axis, or "end_a1".."end_b2" naming the single neighbour's direction.
 */
function resolveChain(block) {
    const perpendicular = PERPENDICULAR[axisOf(readFace(block))];
    for (const key of ["a", "b"]) {
        const [first, second] = perpendicular[key];
        const hasFirst = blockAt(block.dimension, block.location, OFFSETS[first])?.typeId === CHAIN_DRIVE;
        const hasSecond = blockAt(block.dimension, block.location, OFFSETS[second])?.typeId === CHAIN_DRIVE;
        if (hasFirst && hasSecond) return `mid_${key}`;
        if (hasFirst) return `end_${key}1`;
        if (hasSecond) return `end_${key}2`;
    }
    return "none";
}

function refreshDrive(block) {
    if (block?.typeId !== CHAIN_DRIVE) return;
    const wanted = resolveChain(block);
    let current;
    try {
        current = block.permutation.getState(CHAIN_STATE);
    } catch {
        return;
    }
    if (current === wanted) return;
    try {
        block.setPermutation(block.permutation.withState(CHAIN_STATE, wanted));
    } catch {
        /* the chunk unloaded between reading and writing */
    }
}

/** Refresh a drive and every drive touching it. */
function refreshAround(dimension, location) {
    const centre = blockAt(dimension, location, { x: 0, y: 0, z: 0 });
    refreshDrive(centre);
    for (const offset of Object.values(OFFSETS)) {
        refreshDrive(blockAt(dimension, location, offset));
    }
}

/** Remove any More Create visual entity sitting at a location. */
function clearVisualsAt(dimension, location) {
    const centre = { x: location.x + 0.5, y: location.y + 0.5, z: location.z + 0.5 };
    for (const type of VISUALS.keys()) {
        let found;
        try {
            found = dimension.getEntities({ type, location: centre, maxDistance: 0.9 });
        } catch {
            continue;
        }
        for (const entity of found) {
            try { entity.remove(); } catch { /* already gone */ }
        }
    }
}

/**
 * Sweep for visual entities whose block is no longer there.
 *
 * Runs rarely and only touches entities of our own three types, so the cost is
 * proportional to how many encased blocks are actually loaded.
 */
function sweepStrandedVisuals() {
    for (const dimension of world.getDimensions?.() ?? [
        world.getDimension("overworld"),
        world.getDimension("nether"),
        world.getDimension("the_end")
    ]) {
        if (!dimension) continue;
        for (const [type, owners] of VISUALS) {
            let entities;
            try {
                entities = dimension.getEntities({ type });
            } catch {
                continue;
            }
            for (const entity of entities) {
                let block;
                try {
                    block = dimension.getBlock(entity.location);
                } catch {
                    continue; // chunk not loaded - leave it alone
                }
                if (block && !owners.has(block.typeId)) {
                    try { entity.remove(); } catch { /* already gone */ }
                }
            }
        }
    }
}

export function initChainDrives() {
    world.afterEvents.playerPlaceBlock.subscribe((event) => {
        const block = event.block;
        if (!block) return;
        if (block.typeId !== CHAIN_DRIVE) {
            // A neighbour appearing can still complete somebody else's run.
            const location = { ...block.location };
            const dimension = block.dimension;
            system.run(() => refreshAround(dimension, location));
            return;
        }
        const location = { ...block.location };
        const dimension = block.dimension;
        system.run(() => refreshAround(dimension, location));
    });

    world.afterEvents.playerBreakBlock.subscribe((event) => {
        const location = { ...event.block.location };
        const dimension = event.dimension;
        const brokenId = event.brokenBlockPermutation?.type?.id;
        system.run(() => {
            // Create despawns the visual itself, but only for blocks broken
            // through its own handler; this covers the rest.
            if (brokenId && (VISUALS.has(`${brokenId}_entity`) || brokenId === CHAIN_DRIVE ||
                brokenId.startsWith("morecreate:"))) {
                clearVisualsAt(dimension, location);
            }
            refreshAround(dimension, location);
        });
    });

    // Self-healing pass every 10 seconds for anything the events missed.
    system.runInterval(sweepStrandedVisuals, 200);
}

export { clearVisualsAt, refreshAround };
