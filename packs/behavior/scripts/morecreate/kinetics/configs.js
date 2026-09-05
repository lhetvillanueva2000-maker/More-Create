/**
 * Kinetic face configurations for the blocks More Create adds.
 *
 * These are handed to Create through `create_compat:register_kinetic`, so they
 * travel as plain JSON - no functions, no imports from the Create pack. The
 * face shapes below mirror `rpmConfigs.js` in Create exactly, which is what
 * lets an encased cogwheel mesh with a normal one and an encased shaft sit in
 * the middle of an ordinary shaft run.
 */

// Mirrors Create's private helpers so connections resolve identically.
const shaft = (extra = {}) => ({ type: "shaft", ...extra });

const cogwheel = (extra = {}) => ({
    type: "cogwheel",
    sense: "invert",
    alignment: "sameAxis",
    ratios: { large_cogwheel: 0.5 },
    ...extra
});

const largeCogwheel = (extra = {}) => ({
    type: "large_cogwheel",
    sense: "invert",
    alignment: "sameAxis",
    ratios: { cogwheel: 2, large_cogwheel: 1 },
    ...extra
});

const speedController = (extra = {}) => ({
    type: "speed_controller",
    alignment: "perpendicular",
    ...extra
});

/** A shaft port that also mates with a Steam Engine shaft, like `create:shaft`. */
const shaftPort = () => shaft({
    accepts: ["shaft", "steam_engine_shaft"],
    ratios: { steam_engine_shaft: 1 }
});

/**
 * Encased shaft: identical wiring to `create:shaft`.
 *
 * `noEntity` is the whole trick. Create draws shafts with a visual entity on
 * top of an invisible block; skipping that entity means there is nothing left
 * to see, so the shaft is completely hidden inside the solid casing while the
 * network still carries RPM and stress through it. It also removes one entity
 * per shaft, which is where the optimisation comes from.
 */
export const ENCASED_SHAFT_CONFIG = {
    rotationState: "minecraft:block_face",
    noEntity: true,
    faces: {
        north: shaftPort(),
        south: shaftPort()
    }
};

/** Encased cogwheel: same face map as `create:cogwheel`, different visual. */
export const ENCASED_COGWHEEL_CONFIG = {
    rotationState: "minecraft:facing_direction",
    entityType: "morecreate:encased_cogwheel_entity",
    faces: {
        north: shaft(),
        south: shaft(),
        east: cogwheel(),
        west: cogwheel(),
        above: cogwheel(),
        below: cogwheel(),
        aboveEast: cogwheel({ accepts: ["large_cogwheel"] }),
        aboveWest: cogwheel({ accepts: ["large_cogwheel"] }),
        belowEast: cogwheel({ accepts: ["large_cogwheel"] }),
        belowWest: cogwheel({ accepts: ["large_cogwheel"] })
    }
};

/** Encased large cogwheel: same face map as `create:large_cogwheel`. */
export const ENCASED_LARGE_COGWHEEL_CONFIG = {
    rotationState: "minecraft:facing_direction",
    entityType: "morecreate:encased_large_cogwheel_entity",
    faces: {
        north: shaft(),
        south: shaft(),
        below: speedController({ accepts: ["speed_controller"] }),
        aboveEast: largeCogwheel({ accepts: ["cogwheel"] }),
        aboveWest: largeCogwheel({ accepts: ["cogwheel"] }),
        belowEast: largeCogwheel({ accepts: ["cogwheel"] }),
        belowWest: largeCogwheel({ accepts: ["cogwheel"] }),
        eastNorth: largeCogwheel({ sense: "cross", alignment: "perpendicular", accepts: ["large_cogwheel"] }),
        westNorth: largeCogwheel({ sense: "cross", alignment: "perpendicular", accepts: ["large_cogwheel"] }),
        eastSouth: largeCogwheel({ sense: "cross", alignment: "perpendicular", accepts: ["large_cogwheel"] }),
        westSouth: largeCogwheel({ sense: "cross", alignment: "perpendicular", accepts: ["large_cogwheel"] }),
        aboveNorth: largeCogwheel({ sense: "cross", alignment: "perpendicular", accepts: ["large_cogwheel"] }),
        belowNorth: largeCogwheel({ sense: "cross", alignment: "perpendicular", accepts: ["large_cogwheel"] }),
        aboveSouth: largeCogwheel({ sense: "cross", alignment: "perpendicular", accepts: ["large_cogwheel"] }),
        belowSouth: largeCogwheel({ sense: "cross", alignment: "perpendicular", accepts: ["large_cogwheel"] })
    }
};

/**
 * Encased Chain Drive.
 *
 * Create's own ponder text describes the behaviour: drives relay rotation to
 * each other in a row, everything in that row turns the *same* way, and any
 * part of the row may be rotated by 90 degrees. So the four side faces share
 * rotation 1:1 with `sense: "equal"` and carry no alignment constraint, while
 * the two axis faces are ordinary shaft ports. Because a side face only lists
 * a ratio for `chain_drive`, an axis face can never mate with a side one -
 * which is the "must touch on their sides, not axis to side" rule.
 */
const chainLink = () => ({
    type: "chain_drive",
    sense: "equal",
    ratios: { chain_drive: 1 }
});

export const ENCASED_CHAIN_DRIVE_CONFIG = {
    rotationState: "minecraft:block_face",
    entityType: "morecreate:encased_chain_drive_entity",
    faces: {
        north: shaftPort(),
        south: shaftPort(),
        east: chainLink(),
        west: chainLink(),
        above: chainLink(),
        below: chainLink()
    }
};

export const CASINGS = ["andesite", "brass", "copper", "creative"];

/** Every kinetic block More Create registers, as `[blockId, config]` pairs. */
export function kineticRegistrations() {
    const entries = [["morecreate:encased_chain_drive", ENCASED_CHAIN_DRIVE_CONFIG]];
    for (const casing of CASINGS) {
        entries.push([`morecreate:${casing}_encased_shaft`, ENCASED_SHAFT_CONFIG]);
        entries.push([`morecreate:${casing}_encased_cogwheel`, ENCASED_COGWHEEL_CONFIG]);
        entries.push([`morecreate:${casing}_encased_large_cogwheel`, ENCASED_LARGE_COGWHEEL_CONFIG]);
    }
    return entries;
}
