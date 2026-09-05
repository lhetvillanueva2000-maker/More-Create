/**
 * Thin wrapper over Create's Compatibility API v2.
 *
 * Everything More Create adds to Create's machines goes through
 * `system.sendScriptEvent`, which is the documented cross-pack bridge (see
 * `scripts/create/compatibility/README.md` in the Create behaviour pack).
 * Talking to Create this way means we never import from its pack, so More
 * Create simply does nothing if Create is missing instead of crashing.
 */

import { system } from "@minecraft/server";

const PREFIX = "morecreate";

let requestCounter = 0;
const pending = new Map();
const failures = [];

/** Registered so we can surface a readable error if Create rejects something. */
export function watchAcknowledgements() {
    system.afterEvents.scriptEventReceive.subscribe((event) => {
        if (event.id !== "create_compat:registration_ack") return;
        let data;
        try {
            data = JSON.parse(event.message || "{}");
        } catch {
            return;
        }
        if (typeof data.requestId !== "string" || !data.requestId.startsWith(PREFIX)) return;
        const label = pending.get(data.requestId) ?? data.requestId;
        pending.delete(data.requestId);
        if (data.ok) return;
        failures.push(label);
        console.error(`[More Create] Create rejected ${label}: ${data.error}`);
    });
}

function send(eventId, payload, label) {
    const requestId = `${PREFIX}:${requestCounter++}`;
    pending.set(requestId, label);
    try {
        system.sendScriptEvent(eventId, JSON.stringify({ ...payload, requestId }));
    } catch (error) {
        pending.delete(requestId);
        console.error(`[More Create] could not send ${eventId} for ${label}: ${error}`);
        return false;
    }
    return true;
}

/**
 * Register one processing recipe.
 * `machine` is one of millstone, crushing, pressing, mixing, spouting,
 * blasting, smoking, splashing, haunting, sequenced, crafting,
 * crafting_shapeless.
 */
export function registerRecipe(machine, recipe, label) {
    return send("create_compat:register_recipe", { machine, recipe },
        label ?? `${machine} recipe`);
}

/** Register a block that participates in the rotation network. */
export function registerKinetic(blockId, config) {
    return send("create_compat:register_kinetic", { blockId, config }, `kinetic ${blockId}`);
}

/** Registrations Create refused, for the summary line in the console. */
export function registrationFailures() {
    return failures.slice();
}

/** Registrations that never came back with an acknowledgement. */
export function pendingRegistrations() {
    return [...pending.values()];
}
