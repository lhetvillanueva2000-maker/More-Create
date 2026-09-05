/**
 * More Create - an add-on for the Create Bedrock addon by Vatonage.
 *
 * Everything that touches Create goes through its Compatibility API v2 over
 * script events, so this pack never imports from the Create pack. If Create is
 * not enabled the registrations simply go unanswered and nothing here throws.
 */

import { world, system } from "@minecraft/server";

import { watchAcknowledgements, registrationFailures, pendingRegistrations } from "./compat.js";
import { registerMissingRecipes } from "./recipes/index.js";
import { registerKineticBlocks, initKinetics } from "./kinetics/index.js";
import { initCannon } from "./cannon/index.js";
import { initRecipeBook } from "./book/index.js";

watchAcknowledgements();

// Interaction handlers are safe to attach immediately.
initKinetics();
initCannon();
initRecipeBook();

// Registrations wait for world load so Create's compatibility bridge is
// guaranteed to be listening, whatever order the packs' scripts loaded in.
world.afterEvents.worldLoad.subscribe(() => {
    const recipes = registerMissingRecipes();
    const kinetics = registerKineticBlocks();
    console.log(`[More Create] sent ${recipes} recipes and ${kinetics} kinetic blocks to Create.`);

    // Give Create a moment to answer, then report anything it refused or
    // never acknowledged - the usual cause is the Create pack being absent.
    system.runTimeout(() => {
        const failed = registrationFailures();
        const silent = pendingRegistrations();
        if (failed.length) {
            console.error(`[More Create] ${failed.length} registration(s) rejected by Create.`);
        }
        if (silent.length) {
            console.warn(
                `[More Create] ${silent.length} registration(s) unanswered - ` +
                "is the Create behaviour pack enabled and above More Create?"
            );
        }
    }, 100);
});
