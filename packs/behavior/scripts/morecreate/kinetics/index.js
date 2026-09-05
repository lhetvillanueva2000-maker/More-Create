/**
 * Registers every More Create block that takes part in Create's rotation
 * network, then wires up the encasing interaction.
 */

import { registerKinetic } from "../compat.js";
import { kineticRegistrations } from "./configs.js";
import { initEncasing } from "./encasing.js";

export function registerKineticBlocks() {
    let registered = 0;
    for (const [blockId, config] of kineticRegistrations()) {
        if (registerKinetic(blockId, config)) registered++;
    }
    return registered;
}

export function initKinetics() {
    initEncasing();
}
