/**
 * Hands every missing recipe to Create through the Compatibility API.
 *
 * Create matches compatibility recipes before its own built-in tables, which is
 * what lets `SPLASHING_FIXES` replace a broken recipe rather than sit alongside
 * it.
 */

import { registerRecipe } from "../compat.js";
import {
    CRUSHING,
    MILLSTONE,
    CRUSHING_FROM_MILLING,
    SPLASHING,
    SPLASHING_FIXES,
    HAUNTING,
    BLASTING,
    SMOKING,
    PRESSING,
    MIXING
} from "./missing.js";

function registerAll(machine, recipes) {
    let sent = 0;
    for (const recipe of recipes) {
        const label = `${machine}:${recipe.input ?? JSON.stringify(recipe.input)}`;
        if (registerRecipe(machine, recipe, label)) sent++;
    }
    return sent;
}

export function registerMissingRecipes() {
    let total = 0;

    // Crushing Wheels: the recipes Create has and Bedrock lacked, then the
    // milling fallback that makes a wheel able to run Millstone recipes.
    total += registerAll("crushing", CRUSHING);
    total += registerAll("crushing", CRUSHING_FROM_MILLING);

    total += registerAll("millstone", MILLSTONE);
    total += registerAll("pressing", PRESSING);
    total += registerAll("mixing", MIXING);

    // Encased Fan processing.
    total += registerAll("splashing", SPLASHING);   // bulk washing
    total += registerAll("splashing", SPLASHING_FIXES);
    total += registerAll("blasting", BLASTING);     // bulk smelting / melting
    total += registerAll("smoking", SMOKING);       // bulk smoking
    total += registerAll("haunting", HAUNTING);     // bulk haunting

    return total;
}
