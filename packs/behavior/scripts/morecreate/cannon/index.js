/**
 * Schematic Cannon module.
 *
 * Ported from the Create Cannon / Schematic addon: renamed into the
 * `morecreate` namespace, translated to English, and updated from
 * `@minecraft/server` 1.x / `server-ui` 1.x to the 2.x APIs this pack targets.
 *
 * Both modules attach their own event handlers when imported, so `initCannon`
 * only exists to make the dependency explicit from `main.js`.
 */

import "./cannon.js";
import "./cannon_guide.js";
import { initCannonRepair } from "./repair.js";

export function initCannon() {
    // cannon.js and cannon_guide.js attach their handlers on import; the
    // repair pass has to be started explicitly.
    initCannonRepair();
}
