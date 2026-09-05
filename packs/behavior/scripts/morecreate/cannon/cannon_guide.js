/**
 * The in-game Cannon Guide book.
 *
 * The original addon shipped Portuguese, Spanish and English side by side with
 * a language picker; More Create is English only, so the picker is gone and the
 * text lives in one place.
 */

import { world, system, GameMode } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";

const TEXT = {
    mainTitle: "§8§lAddon Guide - Cannons & Schematics",
    mainBody: "§7Welcome to the manual. Pick a topic below to learn how everything works:",
    btnCannon: "§lCannon\n§r§8[How to use and fire it]",
    btnSchematic: "§lSchematic\n§r§8[Quills and files]",
    btnTable: "§lSchematic Table\n§r§8[Importing and sealing]",
    btnAdmin: "§c§lAdmin\n§r§8[Global panel]",

    tutCannonTitle: "§eTutorial: Cannon",
    tutCannonBody:
        "§e§lHOW TO USE THE CANNON:\n\n" +
        "§7The cannon is the machine that builds the blocks of your schematics for you.\n\n" +
        "§f• Fuel: §7Put gunpowder in slot 0 of the cannon.\n" +
        "§f• Start: §7Insert a finished schematic and press §aStart§7.\n" +
        "§f• Pause / Stop: §7Press §cStop§7 to interrupt the build.\n" +
        "§f• Reset: §7Press §4Reset§7 to clear the current progress.",

    tutSchematicTitle: "§eTutorial: Schematic",
    tutSchematicBody:
        "§e§lHOW TO USE THE SCHEMATIC AND QUILL:\n\n" +
        "§7The Schematic and Quill map an area of the world, or read an external file.\n\n" +
        "§f• Mapping in the world: §7Hold the quill and click Point A, then Point B.\n" +
        "§f• Clipboard: §7Checks the materials you need against your inventory and nearby chests.\n" +
        "§f• Rotation: §7Turns the structure (0°, 90°, 180°, 270°).",

    tutTableTitle: "§eTutorial: Schematic Table",
    tutTableBody:
        "§e§lHOW TO USE THE SCHEMATIC TABLE:\n\n" +
        "§7The table is where external structure files are brought in.\n\n" +
        "§f• Importing: §7Hold an 'Empty Schematic', click the table and type the structure file name.",

    adminTitle: "§4§lGlobal Admin Panel",
    adminBody: "§7Creative-only controls for the whole world.",
    btnResetAll: "§cStop and Reset ALL Cannons",
    btnDeleteAll: "§4Delete ALL Saved Structures",

    backBtn: "§8< Back to Menu",
    msgReset: "§c[Admin] Reset %d cannon(s).",
    msgDelete: "§4[Admin] Deleted %d cached structure(s)."
};

/** Property prefixes written per cannon while it is running. */
const CANNON_RUN_PREFIXES = ["running_", "cannon_progress_", "cannon_initialized_"];
/** Property prefixes holding stored structure data. */
const STRUCTURE_PREFIXES = ["struct_", "cannon_struct_"];

function clearProperties(matches) {
    let cleared = 0;
    let ids;
    try {
        ids = world.getDynamicPropertyIds();
    } catch {
        return 0;
    }
    for (const id of ids) {
        if (!matches(id)) continue;
        try {
            world.setDynamicProperty(id, undefined);
            cleared++;
        } catch {
            /* property vanished between listing and clearing */
        }
    }
    return cleared;
}

function resetAllCannons() {
    return clearProperties((id) => CANNON_RUN_PREFIXES.some((p) => id.startsWith(p)));
}

function deleteAllStructures() {
    // Large structures are split across `<key>_chunk_<n>` / `<key>_chunks_count`
    // properties, so those have to go too or the leftovers stay forever.
    return clearProperties((id) =>
        STRUCTURE_PREFIXES.some((p) => id.startsWith(p)) ||
        /_chunk_\d+$/.test(id) ||
        id.endsWith("_chunks_count"));
}

world.afterEvents.itemUse.subscribe((event) => {
    const { source: player, itemStack } = event;
    if (itemStack?.typeId !== "morecreate:cannon_guide") return;
    system.run(() => openMainMenu(player));
});

function isCreative(player) {
    try {
        return player.getGameMode() === GameMode.Creative;
    } catch {
        return false;
    }
}

function openMainMenu(player) {
    const creative = isCreative(player);

    const form = new ActionFormData()
        .title(TEXT.mainTitle)
        .body(TEXT.mainBody)
        .button(TEXT.btnCannon, "textures/morecreate/items/cannon_imagem")
        .button(TEXT.btnSchematic, "textures/morecreate/items/schematic_and_quill")
        .button(TEXT.btnTable, "textures/morecreate/items/schematic_table_imagem");

    if (creative) form.button(TEXT.btnAdmin, "textures/blocks/command_block");

    form.show(player).then((response) => {
        if (response.canceled) return;
        switch (response.selection) {
            case 0: return openTopic(player, TEXT.tutCannonTitle, TEXT.tutCannonBody);
            case 1: return openTopic(player, TEXT.tutSchematicTitle, TEXT.tutSchematicBody);
            case 2: return openTopic(player, TEXT.tutTableTitle, TEXT.tutTableBody);
            case 3: if (creative) openAdminPanel(player); return;
        }
    });
}

function openTopic(player, title, body) {
    new ActionFormData()
        .title(title)
        .body(body)
        .button(TEXT.backBtn, "textures/ui/undoArrow")
        .show(player)
        .then((res) => {
            if (!res.canceled) openMainMenu(player);
        });
}

function openAdminPanel(player) {
    new ActionFormData()
        .title(TEXT.adminTitle)
        .body(TEXT.adminBody)
        .button(TEXT.btnResetAll)
        .button(TEXT.btnDeleteAll)
        .button(TEXT.backBtn, "textures/ui/undoArrow")
        .show(player)
        .then((response) => {
            if (response.canceled) return;
            if (response.selection === 0) {
                const cleared = resetAllCannons();
                player.sendMessage(TEXT.msgReset.replace("%d", String(cleared)));
            } else if (response.selection === 1) {
                const cleared = deleteAllStructures();
                player.sendMessage(TEXT.msgDelete.replace("%d", String(cleared)));
            } else if (response.selection === 2) {
                openMainMenu(player);
            }
        });
}
