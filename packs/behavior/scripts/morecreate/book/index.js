/**
 * The Recipe Book.
 *
 * Bedrock has no recipe browser for script-driven machines, so Create's
 * processing recipes are invisible unless you already know them. This item
 * lists all of them: pick a machine, then read what goes in and what comes out,
 * or search for an item to see every machine that will accept it.
 */

import { world, system } from "@minecraft/server";
import { ActionFormData, ModalFormData } from "@minecraft/server-ui";

import { MACHINES, RECIPES, STONECUTTING_NOTE, TOTAL } from "./recipes_data.js";

const BOOK = "morecreate:recipe_book";
const PAGE_SIZE = 40;

/** "minecraft:iron_nugget" -> "Iron Nugget". Ids are all we have to work with. */
function pretty(id) {
    if (typeof id !== "string") return String(id);
    if (id.includes(" ")) {
        // Composite labels (mixer inputs, spout inputs) are already readable
        // apart from the ids inside them.
        return id.replace(/[a-z0-9_.]+:[a-z0-9_.]+/g, (match) => pretty(match));
    }
    const name = id.includes(":") ? id.split(":")[1] : id;
    return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatOutputs(outputs) {
    return outputs.map(([item, count, chance]) => {
        const amount = count > 1 ? `${count} x ` : "";
        const odds = chance !== undefined ? ` §7(${Math.round(chance * 100)}%)§r` : "";
        return `${amount}${pretty(item)}${odds}`;
    }).join(", ");
}

function recipeLines(rows) {
    return rows.map(([input, outputs]) =>
        `§f${pretty(input)}\n  §7-> §a${formatOutputs(outputs)}`).join("\n\n");
}

/** Show one machine's recipes, paged so a long list still fits in the form. */
function showMachine(player, machine, page = 0) {
    const rows = RECIPES[machine.key] ?? [];
    const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
    const clamped = Math.min(Math.max(page, 0), pages - 1);
    const slice = rows.slice(clamped * PAGE_SIZE, (clamped + 1) * PAGE_SIZE);

    const header = `§7${machine.subtitle}§r\n\n` +
        (pages > 1 ? `§8Page ${clamped + 1} of ${pages} - ${rows.length} recipes§r\n\n` : "");

    const form = new ActionFormData()
        .title(`§e${machine.title}`)
        .body(header + (slice.length ? recipeLines(slice) : "§7No recipes."));

    const actions = [];
    if (clamped > 0) {
        form.button("§8< Previous page");
        actions.push(() => showMachine(player, machine, clamped - 1));
    }
    if (clamped < pages - 1) {
        form.button("§8Next page >");
        actions.push(() => showMachine(player, machine, clamped + 1));
    }
    form.button("§8< Back to menu", "textures/ui/undoArrow");
    actions.push(() => openBook(player));

    form.show(player).then((response) => {
        if (response.canceled) return;
        actions[response.selection]?.();
    });
}

/** Look up one item across every machine at once. */
function showSearch(player) {
    new ModalFormData()
        .title("§eSearch Recipes")
        .textField("Item name or id:", "e.g. gravel", { defaultValue: "" })
        .show(player)
        .then((response) => {
            if (response.canceled) return;
            const term = String(response.formValues?.[0] ?? "").trim().toLowerCase();
            if (!term) return openBook(player);

            const found = [];
            for (const machine of MACHINES) {
                for (const [input, outputs] of RECIPES[machine.key] ?? []) {
                    const asInput = String(input).toLowerCase().includes(term);
                    const asOutput = outputs.some(([item]) => String(item).toLowerCase().includes(term));
                    if (!asInput && !asOutput) continue;
                    found.push(`§6${machine.title}§r\n§f${pretty(input)}\n  §7-> §a${formatOutputs(outputs)}`);
                }
            }

            const body = found.length
                ? `§7${found.length} match(es) for "${term}"§r\n\n` + found.slice(0, 60).join("\n\n") +
                  (found.length > 60 ? `\n\n§8... and ${found.length - 60} more.` : "")
                : `§7Nothing uses or produces "${term}".`;

            new ActionFormData()
                .title("§eSearch Results")
                .body(body)
                .button("§8Search again", "textures/ui/magnifyingGlass")
                .button("§8< Back to menu", "textures/ui/undoArrow")
                .show(player)
                .then((res) => {
                    if (res.canceled) return;
                    if (res.selection === 0) showSearch(player);
                    else openBook(player);
                });
        });
}

function openBook(player) {
    const form = new ActionFormData()
        .title("§8§lMore Create - Recipe Book")
        .body(`§7Every processing recipe in the game - §f${TOTAL}§7 of them.\n` +
              "Pick a machine to see what it takes and what it gives back.");

    for (const machine of MACHINES) {
        const count = (RECIPES[machine.key] ?? []).length;
        form.button(`§l${machine.title}\n§r§8${count} recipes`);
    }
    form.button("§lSearch by item\n§r§8Find every machine that uses it", "textures/ui/magnifyingGlass");
    form.button("§lStonecutter\n§r§8Stone family variants");

    form.show(player).then((response) => {
        if (response.canceled) return;
        const index = response.selection;
        if (index < MACHINES.length) return showMachine(player, MACHINES[index]);
        if (index === MACHINES.length) return showSearch(player);
        new ActionFormData()
            .title("§eStonecutter")
            .body(`§7${STONECUTTING_NOTE}`)
            .button("§8< Back to menu", "textures/ui/undoArrow")
            .show(player)
            .then((res) => {
                if (!res.canceled) openBook(player);
            });
    });
}

export function initRecipeBook() {
    world.afterEvents.itemUse.subscribe((event) => {
        if (event.itemStack?.typeId !== BOOK) return;
        const player = event.source;
        system.run(() => openBook(player));
    });
}
