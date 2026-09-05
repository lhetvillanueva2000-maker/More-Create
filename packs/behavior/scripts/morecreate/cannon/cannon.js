import { world, system, ItemStack, BlockPermutation } from "@minecraft/server";
import { ActionFormData, ModalFormData } from "@minecraft/server-ui";

const playerSelections = new Map();  
const uiDebounce = new Set();

const cannonSlotStates = new Map();

// Keeps reading the global build speed live, so the admin panel can change it mid-run.
function getGlobalBuildSpeed() {
    try {
        const speed = world.getDynamicProperty("admin_build_speed");
        if (speed !== undefined) return Number(speed);
    } catch (e) {}
    return 10;
}

const INDESTRUCTIBLE_BLOCKS = [
    "minecraft:bedrock",
    "minecraft:barrier",
    "minecraft:command_block",
    "minecraft:repeating_command_block",
    "minecraft:chain_command_block",
    "minecraft:structure_block",
    "minecraft:jigsaw"
];

const CREATIVE_ONLY_BLOCKS = [
    "minecraft:bedrock",
    "minecraft:barrier",
    "minecraft:border_block",
    "minecraft:structure_void",
    "minecraft:jigsaw",
    "minecraft:allow",
    "minecraft:deny",
    "minecraft:glowingobsidian",
    "minecraft:info_update",
    "minecraft:reserved6",
    "minecraft:command_block",
    "minecraft:repeating_command_block",
    "minecraft:chain_command_block",
    "minecraft:structure_block"
];

const IGNORED_ENTITIES = [
    "morecreate:cannon_projectile",
    "minecraft:donkey",
    "minecraft:mule",
    "minecraft:llama",
    "minecraft:trader_llama",
    "minecraft:horse",
    "minecraft:skeleton_horse",
    "minecraft:zombie_horse",
    "minecraft:boat",
    "minecraft:chest_boat",
    "minecraft:minecart",
    "minecraft:chest_minecart",
    "minecraft:hopper_minecart",
    "minecraft:tnt_minecart",
    "minecraft:command_block_minecart",
    "minecraft:player"
];

const CANNON_BUTTON_IDS = [
    "morecreate:clipboard_button",
    "morecreate:stop_button",
    "morecreate:start_button",
    "morecreate:reset_button",
    "morecreate:confirm_button",
    "morecreate:configures_button"
];

const MAX_RAYCAST_DISTANCE = 12;
const MAX_PROPERTY_LENGTH = 30000; 

function sleep(ticks = 1) {
    return new Promise((resolve) => {
        let count = 0;
        const id = system.runInterval(() => {
            count++;
            if (count >= ticks) {
                system.clearRun(id);
                resolve();
            }
        });
    });
}

function saveLargeDynamicProperty(key, fullString) {
    let index = 0;
    while (world.getDynamicProperty(`${key}_chunk_${index}`) !== undefined) {
        world.setDynamicProperty(`${key}_chunk_${index}`, "");
        index++;
    }

    let chunkIndex = 0;
    for (let i = 0; i < fullString.length; i += MAX_PROPERTY_LENGTH) {
        const chunk = fullString.substring(i, i + MAX_PROPERTY_LENGTH);
        world.setDynamicProperty(`${key}_chunk_${chunkIndex}`, chunk);
        chunkIndex++;
    }
    world.setDynamicProperty(`${key}_chunks_count`, chunkIndex);
}

function loadLargeDynamicProperty(key) {
    const count = world.getDynamicProperty(`${key}_chunks_count`);
    if (count === undefined || count === 0) {
        return world.getDynamicProperty(key);
    }

    let fullString = "";
    for (let i = 0; i < count; i++) {
        const chunk = world.getDynamicProperty(`${key}_chunk_${i}`);
        if (chunk) fullString += chunk;
    }
    return fullString;
}

function clearLargeDynamicProperty(key) {
    const count = world.getDynamicProperty(`${key}_chunks_count`) || 0;
    for (let i = 0; i < count; i++) {
        world.setDynamicProperty(`${key}_chunk_${i}`, "");
    }
    world.setDynamicProperty(`${key}_chunks_count`, 0);
    world.setDynamicProperty(key, "");
}

function cleanUpButtonDuplication(entity, buttonItemId) {
    const loc = entity.location;
    const dim = entity.dimension;

    try {
        const itemsOnGround = dim.getEntities({
            location: loc,
            maxDistance: 6,
            type: "minecraft:item"
        });

        for (const itemEnt of itemsOnGround) {
            const itemStack = itemEnt.getComponent("minecraft:item")?.itemStack;
            if (itemStack && itemStack.typeId === buttonItemId) {
                itemEnt.remove();
            }
        }
    } catch (e) {}

    try {
        const nearbyPlayers = dim.getPlayers({ location: loc, maxDistance: 8 });
        for (const player of nearbyPlayers) {
            const inv = player.getComponent("minecraft:inventory")?.container;
            if (!inv) continue;

            for (let slot = 0; slot < inv.size; slot++) {
                const item = inv.getItem(slot);
                if (item && item.typeId === buttonItemId) {
                    inv.setItem(slot, null);
                }
            }
        }
    } catch (e) {}
}

function respawnButtonInSlot(entity, slotIndex, buttonItemId) {
    const px = Math.floor(entity.location.x);
    const py = Math.floor(entity.location.y);
    const pz = Math.floor(entity.location.z);

    entity.dimension.runCommandAsync(
        `replaceitem entity @e[type=morecreate:cannon_entity,x=${px},y=${py},z=${pz},r=1] slot.inventory ${slotIndex} ${buttonItemId} 1`
    ).catch(() => {});
}

function forceCloseContainerAndTeleport(entity, player, callbackAfterClose = null) {
    const originalPos = { x: entity.location.x, y: entity.location.y, z: entity.location.z };
    const tempPos = { x: originalPos.x, y: originalPos.y + 30, z: originalPos.z };

    try {
        entity.teleport(tempPos);
    } catch (e) {}

    system.runTimeout(() => {
        try {
            entity.teleport(originalPos);
        } catch (e) {}

        if (callbackAfterClose) {
            system.runTimeout(() => {
                callbackAfterClose();
            }, 2);
        }
    }, 2);
}

system.runInterval(() => {
    for (const player of world.getAllPlayers()) {
        const inventory = player.getComponent("minecraft:inventory")?.container;
        if (!inventory) continue;

        for (let slot = 0; slot < inventory.size; slot++) {
            const itemInSlot = inventory.getItem(slot);
            if (itemInSlot && itemInSlot.typeId === "morecreate:cannon_base") {
                const newCannonItem = new ItemStack("morecreate:cannon", itemInSlot.amount);
                inventory.setItem(slot, newCannonItem);
            }
        }

        for (let slot = 0; slot < inventory.size; slot++) {
            const itemInSlot = inventory.getItem(slot);
            if (itemInSlot && CANNON_BUTTON_IDS.includes(itemInSlot.typeId)) {
                inventory.setItem(slot, null);
            }
        }

        const item = inventory.getItem(player.selectedSlotIndex);
        if (!item) continue;

        if (item.typeId === "morecreate:schematic_and_quill") {
            const cache = playerSelections.get(player.id);
            if (cache && cache.start) {
                const raycast = player.getBlockFromViewDirection({ maxDistance: MAX_RAYCAST_DISTANCE });
                if (raycast && raycast.block) {
                    renderSelectionBoxParticles(player.dimension, cache.start, raycast.block.location);
                } else {
                    const viewDir = player.getViewDirection();
                    const playerLoc = player.location; 
                    const airTarget = {
                        x: Math.floor(playerLoc.x + viewDir.x * 3),
                        y: Math.floor(playerLoc.y), 
                        z: Math.floor(playerLoc.z + viewDir.z * 3)
                    };
                    renderSelectionBoxParticles(player.dimension, cache.start, airTarget);
                }
            }
        }

        if (item.typeId === "morecreate:schematic") {
            const lore = item.getLore();
            if (lore && lore.length > 0) {
                const structName = lore[0].replace("§7Estrutura: ", "").trim();
                const rawData = loadLargeDynamicProperty(`struct_${structName}`);
                
                if (rawData) {
                    const data = JSON.parse(rawData);
                    
                    let isFixed = world.getDynamicProperty(`p_fixed_${player.id}_${structName}`) || false;
                    let savedLocRaw = world.getDynamicProperty(`p_loc_${player.id}_${structName}`);
                    let currentOffsetPos = savedLocRaw ? JSON.parse(savedLocRaw) : null;
                    
                    let isSelectingLocation = world.getDynamicProperty(`p_selecting_${player.id}_${structName}`) ?? false;
                    let previewType = world.getDynamicProperty(`p_preview_type_${player.id}_${structName}`) ?? 0;

                    const cache = playerSelections.get(player.id) || {};
                    cache.isFixed = isFixed;
                    cache.currentOffsetPos = currentOffsetPos;
                    cache.isSelectingLocation = isSelectingLocation;
                    cache.previewType = previewType;

                    if (cache.isSelectingLocation) {
                        if (!cache.isFixed) {
                            const raycast = player.getBlockFromViewDirection({ maxDistance: MAX_RAYCAST_DISTANCE });
                            let targetLoc;

                            if (raycast && raycast.block) {
                                targetLoc = { ...raycast.block.location };
                                if (raycast.face === "Up") targetLoc.y += 1;
                            } else {
                                const viewDir = player.getViewDirection();
                                const playerLoc = player.location;
                                targetLoc = {
                                    x: Math.floor(playerLoc.x + viewDir.x * 3),
                                    y: Math.floor(playerLoc.y),
                                    z: Math.floor(playerLoc.z + viewDir.z * 3)
                                };
                            }
                            
                            cache.currentOffsetPos = targetLoc;
                            playerSelections.set(player.id, cache);
                            
                            if (cache.previewType === 1) {
                                renderVisualizer(player.dimension, data.blocks, targetLoc, data.rotation ?? 0);
                            } else {
                                renderSelectionBoxFromData(player.dimension, data.blocks, targetLoc, data.rotation ?? 0);
                            }
                        } 
                        else if (cache.isFixed && cache.currentOffsetPos) {
                            if (cache.previewType === 1) {
                                renderVisualizer(player.dimension, data.blocks, cache.currentOffsetPos, data.rotation ?? 0);
                            } else {
                                renderSelectionBoxFromData(player.dimension, data.blocks, cache.currentOffsetPos, data.rotation ?? 0);
                            }
                        }
                    }
                }
            }
        }
    }

    for (const dimensionName of ["overworld", "nether", "the_end"]) {
        try {
            const dim = world.getDimension(dimensionName);
            
            for (const buttonId of CANNON_BUTTON_IDS) {
                const itemsOnGround = dim.getEntities({ type: "minecraft:item" });
                for (const itemEnt of itemsOnGround) {
                    const itemStack = itemEnt.getComponent("minecraft:item")?.itemStack;
                    if (itemStack && itemStack.typeId === buttonId) {
                        itemEnt.remove();
                    }
                }
            }

            const cannonEntities = dim.getEntities({ type: "morecreate:cannon_entity" });

            for (const entity of cannonEntities) {
                processCannonEntityInventory(entity);
            }
        } catch(e){}
    }
}, 2);

function processCannonEntityInventory(entity) {
    const invComp = entity.getComponent("minecraft:inventory");
    if (!invComp || !invComp.container) return;

    const container = invComp.container;
    const blockLoc = {
        x: Math.floor(entity.location.x),
        y: Math.floor(entity.location.y),
        z: Math.floor(entity.location.z)
    };
    const cannonKey = `${blockLoc.x}_${blockLoc.y}_${blockLoc.z}`;

    const requiredButtons = {
        1: "morecreate:clipboard_button",
        6: "morecreate:stop_button",
        7: "morecreate:start_button",
        8: "morecreate:reset_button",
        9: "morecreate:confirm_button",
        10: "morecreate:configures_button"
    };

    for (const [slotStr, buttonId] of Object.entries(requiredButtons)) {
        const slotIdx = parseInt(slotStr);
        const currentItem = container.getItem(slotIdx);
        
        if (!currentItem) {
            respawnButtonInSlot(entity, slotIdx, buttonId);
        } else if (currentItem.typeId !== buttonId) {
            const playersAround = entity.dimension.getPlayers({ location: entity.location, maxDistance: 6 });
            if (playersAround.length > 0) {
                const player = playersAround[0];
                const pInv = player.getComponent("minecraft:inventory")?.container;
                if (pInv) {
                    try {
                        pInv.addItem(currentItem);
                    } catch (err) {
                        entity.dimension.spawnItem(currentItem, entity.location);
                    }
                } else {
                    entity.dimension.spawnItem(currentItem, entity.location);
                }
            } else {
                entity.dimension.spawnItem(currentItem, entity.location);
            }
            container.setItem(slotIdx, null);
            respawnButtonInSlot(entity, slotIdx, buttonId);
        }
    }

    const previousState = cannonSlotStates.get(entity.id) || {};
    const currentState = {};

    for (let i = 0; i < container.size; i++) {
        const item = container.getItem(i);
        currentState[i] = item ? item.typeId : null;
    }

    // Mouse clicks on PC report entity-inventory slots differently; handle both.
    const isClickedOnPC = (slotIdx) => {
        return (previousState[slotIdx] && !currentState[slotIdx]) || (!previousState[slotIdx] && currentState[slotIdx] === null);
    };

    let powderPool = world.getDynamicProperty(`cannon_powder_${cannonKey}`) || 0;
    if (powderPool <= 0) {
        const slot0Item = container.getItem(0);
        if (slot0Item && slot0Item.typeId === "minecraft:gunpowder") {
            world.setDynamicProperty(`cannon_powder_${cannonKey}`, 400);

            if (slot0Item.amount > 1) {
                slot0Item.amount -= 1;
                container.setItem(0, slot0Item);
            } else {
                container.setItem(0, null);
            }
        }
    }

    const slot4Item = container.getItem(4);
    if (slot4Item && slot4Item.typeId === "morecreate:schematic") {
        const lore = slot4Item.getLore();
        if (lore && lore.length > 0) {
            const structName = lore[0].replace("§7Estrutura: ", "").trim();
            world.setDynamicProperty(`cannon_struct_${cannonKey}`, structName);
            world.setDynamicProperty(`cannon_progress_${cannonKey}`, 0);

            container.setItem(4, null);
            container.setItem(5, slot4Item);
        }
    }

    if (previousState[1] && !currentState[1]) {
        cleanUpButtonDuplication(entity, "morecreate:clipboard_button");
        respawnButtonInSlot(entity, 1, "morecreate:clipboard_button");

        const slot2Item = container.getItem(2);
        if (slot2Item && (slot2Item.typeId === "morecreate:clipboard" || slot2Item.typeId === "morecreate:empty_clipboard")) {
            const activeSelection = world.getDynamicProperty(`cannon_struct_${cannonKey}`) || "";
            if (activeSelection) {
                const rawData = loadLargeDynamicProperty(`struct_${activeSelection}`);
                if (rawData) {
                    const data = JSON.parse(rawData);
                    const required = {};
                    if (data.blocks) {
                        for (const b of data.blocks) {
                            if (b.isEntityAnchor) continue;
                            if (CREATIVE_ONLY_BLOCKS.includes(b.type)) continue;
                            required[b.type] = (required[b.type] || 0) + 1;
                        }
                    }

                    const containers = getAdjacentInventories(entity.dimension, blockLoc);
                    const storageCounts = countItemsInContainers(containers);

                    const newLore = [`§7Estrutura: ${activeSelection}`];
                    for (const [type, reqQty] of Object.entries(required)) {
                        const name = type.replace("minecraft:", "").replace(/_/g, " ").toUpperCase();
                        const available = storageCounts[type] || 0;
                        const progressColor = (available >= reqQty) ? "§a" : "§c";
                        const missingAmount = Math.max(0, reqQty - available);
                        const missingText = missingAmount > 0 ? formatPackQuantity(missingAmount) : "§a✓";
                        newLore.push(`§f• ${name}: ${progressColor}${available}§f/${reqQty} (${missingText})`);
                    }

                    const updatedClipboard = new ItemStack("morecreate:clipboard", 1);
                    updatedClipboard.setLore(newLore);

                    container.setItem(2, null);
                    container.setItem(3, updatedClipboard);
                }
            }
        }
    }

    if (previousState[6] && !currentState[6]) {
        cleanUpButtonDuplication(entity, "morecreate:stop_button");
        respawnButtonInSlot(entity, 6, "morecreate:stop_button");

        world.setDynamicProperty(`running_${cannonKey}`, false);
    }

    if (previousState[7] && !currentState[7]) {
        cleanUpButtonDuplication(entity, "morecreate:start_button");
        respawnButtonInSlot(entity, 7, "morecreate:start_button");

        const activeSelection = world.getDynamicProperty(`cannon_struct_${cannonKey}`) || "";
        const isRunning = world.getDynamicProperty(`running_${cannonKey}`);

        if (activeSelection && !isRunning) {
            const playersAround = entity.dimension.getPlayers({ location: entity.location, maxDistance: 10 });
            const triggerPlayer = playersAround[0];
            if (triggerPlayer) {
                executeCannonBuild(triggerPlayer, activeSelection, blockLoc);
            }
        }
    }

    if (previousState[8] && !currentState[8]) {
        cleanUpButtonDuplication(entity, "morecreate:reset_button");
        respawnButtonInSlot(entity, 8, "morecreate:reset_button");

        world.setDynamicProperty(`running_${cannonKey}`, false);
        world.setDynamicProperty(`cannon_progress_${cannonKey}`, 0);
        world.setDynamicProperty(`cannon_struct_${cannonKey}`, "");
    }

    if (previousState[9] && !currentState[9]) {
        cleanUpButtonDuplication(entity, "morecreate:confirm_button");
        respawnButtonInSlot(entity, 9, "morecreate:confirm_button");

        const playersAround = entity.dimension.getPlayers({ location: entity.location, maxDistance: 8 });
        const triggerPlayer = playersAround[0];
        if (triggerPlayer) {
            forceCloseContainerAndTeleport(entity, triggerPlayer, () => {
                openCannonStatusUI(triggerPlayer, cannonKey);
            });
        }
    }

    if (previousState[10] && !currentState[10]) {
        cleanUpButtonDuplication(entity, "morecreate:configures_button");
        respawnButtonInSlot(entity, 10, "morecreate:configures_button");

        const playersAround = entity.dimension.getPlayers({ location: entity.location, maxDistance: 8 });
        const triggerPlayer = playersAround[0];
        if (triggerPlayer) {
            forceCloseContainerAndTeleport(entity, triggerPlayer, () => {
                openConfigUI(triggerPlayer, cannonKey);
            });
        }
    }

    cannonSlotStates.set(entity.id, currentState);
}

function openCannonStatusUI(player, cannonKey) {
    const structName = world.getDynamicProperty(`cannon_struct_${cannonKey}`) || "nenhuma";
    const powderVal = world.getDynamicProperty(`cannon_powder_${cannonKey}`) || 0;
    const powderText = powderVal > 0 ? `${powderVal}/400` : "vazio";

    const skipMissing = world.getDynamicProperty(`skip_missing_${cannonKey}`) ? "✓" : "x";
    const replaceBlocks = world.getDynamicProperty(`replace_blocks_${cannonKey}`) ? "✓" : "x";
    const replaceContainers = world.getDynamicProperty(`replace_containers_${cannonKey}`) ? "✓" : "x";
    const waitMode = world.getDynamicProperty(`keep_active_${cannonKey}`) ? "✓" : "x";

    let isRunning = world.getDynamicProperty(`running_${cannonKey}`) || false;
    let cannonStateText = "reset";
    if (isRunning) {
        cannonStateText = "building";
    } else {
        const progress = world.getDynamicProperty(`cannon_progress_${cannonKey}`) || 0;
        if (progress > 0) {
            cannonStateText = "paused";
        }
    }

    const bodyText = 
        `§7Structure: §e${structName}\n` +
        `§7Fuel: §e${powderText}\n\n` +
        `§7Skip missing blocks [${skipMissing}]\n` +
        `§7Replace blocks [${replaceBlocks}]\n` +
        `§7Replace blocks with inventories [${replaceContainers}]\n` +
        `§7Standby mode [${waitMode}]\n\n` +
        `§7Cannon: §a${cannonStateText}`;

    system.run(() => {
        new ActionFormData()
            .title("§eCannon Status")
            .body(bodyText)
            .button("Back")
            .show(player);
    });
}

world.beforeEvents.playerBreakBlock.subscribe((ev) => {
    const { block, player } = ev;
    const inventory = player.getComponent("minecraft:inventory")?.container;
    const item = inventory?.getItem(player.selectedSlotIndex);

    if (item && item.typeId === "morecreate:schematic_and_quill") {
        let cache = playerSelections.get(player.id);
        if (cache && cache.start) {
            ev.cancel = true;
            playerSelections.delete(player.id);
            system.run(() => {
                player.sendMessage("§cPoint A selection cancelled. Pick a new spot.");
            });
            return;
        }
    }
    
    if (block.typeId === "morecreate:cannon_base") {
        const cannonKey = `${block.location.x}_${block.location.y}_${block.location.z}`;
        system.run(() => {
            try {
                const entities = block.dimension.getEntities({
                    type: "morecreate:cannon_entity",
                    location: { x: block.location.x + 0.5, y: block.location.y, z: block.location.z + 0.5 },
                    maxDistance: 0.6 
                });
                for (const ent of entities) ent.remove();
                
                world.setDynamicProperty(`running_${cannonKey}`, false);
            } catch(e){}
        });
    }
});

world.beforeEvents.playerInteractWithBlock.subscribe((ev) => {
    const { player, block, isFirstEvent } = ev;
    if (!isFirstEvent) return;

    if (block.typeId === "morecreate:schematic_table") {
        ev.cancel = true;
        if (uiDebounce.has(player.id)) return;
        uiDebounce.add(player.id);
        system.run(() => {
            openSchematicTableUI(player);
            system.runTimeout(() => uiDebounce.delete(player.id), 10);
        });
        return;
    }
});

function openSchematicTableUI(player) {
    const inv = player.getComponent("minecraft:inventory")?.container;
    if (!inv) return;

    const currentHandItem = inv.getItem(player.selectedSlotIndex);
    const hasEmptySchematic = currentHandItem && currentHandItem.typeId === "morecreate:empty_schematic";

    const validQuills = [];
    const quillNamesForDropdown = ["-- None Selected --"];
    
    for (let i = 0; i < inv.size; i++) {
        const slotItem = inv.getItem(i);
        if (slotItem && slotItem.typeId === "morecreate:schematic_and_quill") {
            const lore = slotItem.getLore();
            if (lore && lore.length > 0) {
                const structName = lore[0].replace("§7Estrutura: ", "").trim();
                validQuills.push({ slot: i, name: structName });
                quillNamesForDropdown.push(`Quill: ${structName}`);
            }
        }
    }

    const form = new ModalFormData()
        .title("§7Schematic Table")
        .textField("§7[Folder] Search by file name:", "e.g. modern_house", { defaultValue: "" })
        .dropdown("§7[Seal] Write a Quill draft:", quillNamesForDropdown, { defaultValueIndex: 0 });

    form.show(player).then((res) => {
        if (res.canceled) return;

        const typedText = res.formValues[0]?.trim();
        const quillDropdownIdx = res.formValues[1];

        if (typedText && typedText !== "") {
            if (!hasEmptySchematic) {
                player.sendMessage("§cYou need to hold an [Empty Schematic] to load it.");
                return;
            }
            processSafeStructureImport(player, typedText).catch(() => {});
            return;
        }

        if (quillDropdownIdx > 0) {
            const selectedQuill = validQuills[quillDropdownIdx - 1];
            const targetItem = inv.getItem(selectedQuill.slot);
            
            if (targetItem && targetItem.typeId === "morecreate:schematic_and_quill") {
                const officialSchematic = new ItemStack("morecreate:schematic", 1);
                officialSchematic.setLore([`§7Structure: ${selectedQuill.name}`]);
                inv.setItem(selectedQuill.slot, officialSchematic);
                player.sendMessage(`§a§l[!]§r §aStructure §e${selectedQuill.name}§a sealed successfully.`);
            }
            return;
        }
    });
}

async function processSafeStructureImport(player, structureName) {
    const inv = player.getComponent("minecraft:inventory")?.container;
    if (!inv) return;

    const currentHandItem = inv.getItem(player.selectedSlotIndex);
    if (!currentHandItem) return;

    try {
        const structManager = world.structureManager;
        const loadedStructure = structManager.get(structureName);

        if (!loadedStructure) {
            player.sendMessage(`§c[Error] Structure '${structureName}' was not found in your 'structures' folder.`);
            return;
        }

        const size = loadedStructure.size;
        const blocks = [];
        
        let processedThisTick = 0;
        const maxBlocksPerTick = 25000; 

        for (let x = 0; x < size.x; x++) {
            for (let y = 0; y < size.y; y++) {
                for (let z = 0; z < size.z; z++) {
                    const blockPerm = loadedStructure.getBlockPermutation({ x, y, z });
                    
                    if (blockPerm && blockPerm.type.id !== "minecraft:air") {
                        if (CREATIVE_ONLY_BLOCKS.includes(blockPerm.type.id)) {
                            processedThisTick++;
                            continue;
                        }

                        const states = {};
                        try {
                            const allStates = blockPerm.getAllStates();
                            for (const sKey in allStates) {
                                states[sKey] = allStates[sKey];
                            }
                        } catch(e){}

                        blocks.push({
                            type: blockPerm.type.id,
                            states: states,
                            relX: x,
                            relY: y,
                            relZ: z
                        });
                    }

                    processedThisTick++;
                    if (processedThisTick >= maxBlocksPerTick) {
                        processedThisTick = 0;
                        await sleep(1); 
                    }
                }
            }
        }

        if (blocks.length === 0) {
            player.sendMessage(`§c[Error] The structure that was read is completely empty.`);
            return;
        }

        if (currentHandItem.amount > 1) {
            currentHandItem.amount -= 1;
            inv.setItem(player.selectedSlotIndex, currentHandItem);
        } else {
            inv.setItem(player.selectedSlotIndex, null);
        }

        saveLargeDynamicProperty(`struct_${structureName}`, JSON.stringify({ blocks, rotation: 0 }));

        const newSchematic = new ItemStack("morecreate:schematic", 1);
        newSchematic.setLore([`§7Structure: ${structureName}`]);
        inv.addItem(newSchematic);

        player.sendMessage(`§a§l[!]§r §aDone. §e${structureName}§a mapped into memory (${blocks.length} blocks total).`);

    } catch (error) {
        player.sendMessage(`§c[Error] Could not read the structure from memory. Check the file dimensions.`);
    }
}

function scanArea(dimension, start, end) {
    const minX = Math.min(start.x, end.x);
    const minY = Math.min(start.y, end.y);
    const minZ = Math.min(start.z, end.z);
    const maxX = Math.max(start.x, end.x);
    const maxY = Math.max(start.y, end.y);
    const maxZ = Math.max(start.z, end.z);

    const list = [];
    for (let x = minX; x <= maxX; x++) {
        for (let y = minY; y <= maxY; y++) {
            for (let z = minZ; z <= maxZ; z++) {
                const block = dimension.getBlock({ x: x, y: y, z: z });
                if (block && !block.isAir) {
                    if (CREATIVE_ONLY_BLOCKS.includes(block.typeId)) continue;

                    const permutation = block.permutation;
                    const states = {};
                    if (permutation) {
                        try {
                            for (const [sKey, sVal] of Object.entries(permutation.getAllStates())) {
                                states[sKey] = sVal;
                            }
                        } catch(e){}
                    }
                    list.push({ type: block.typeId, states: states, relX: x - minX, relY: y - minY, relZ: z - minZ });
                }
            }
        }
    }
    return list;
}

world.afterEvents.itemUse.subscribe((event) => {
    const player = event.source;
    const item = event.itemStack;

    if (!item) return;

    const blockRay = player.getBlockFromViewDirection({ maxDistance: 5 });
    if (blockRay && blockRay.block && (blockRay.block.typeId === "morecreate:cannon" || blockRay.block.typeId === "morecreate:cannon_base" || blockRay.block.typeId === "morecreate:schematic_table")) return;

    if (uiDebounce.has(player.id)) return;

    if (item.typeId === "morecreate:schematic_and_quill") {
        const loreCheck = item.getLore();
        if (loreCheck && loreCheck.length > 0) {
            player.sendMessage("§eThis draft already holds data. Take it to the Schematic Table.");
            return;
        }

        uiDebounce.add(player.id);
        system.runTimeout(() => uiDebounce.delete(player.id), 10);

        const raycast = player.getBlockFromViewDirection({ maxDistance: MAX_RAYCAST_DISTANCE });
        let blockLoc;

        if (raycast && raycast.block) {
            blockLoc = { x: raycast.block.x, y: raycast.block.y, z: raycast.block.z };
        } else {
            const viewDir = player.getViewDirection();
            const playerLoc = player.location;
            blockLoc = {
                x: Math.floor(playerLoc.x + viewDir.x * 3),
                y: Math.floor(playerLoc.y),
                z: Math.floor(playerLoc.z + viewDir.z * 3)
            };
        }

        let cache = playerSelections.get(player.id) || { start: null };

        if (!cache.start) {
            cache.start = blockLoc;
            playerSelections.set(player.id, cache);
            player.sendMessage("§aPoint A set.");
        } else {
            const start = cache.start;
            const end = blockLoc;
            const blocks = scanArea(player.dimension, start, end);
            
            playerSelections.delete(player.id);

            system.run(() => {
                const nameForm = new ModalFormData()
                    .title("§7Save Structure")
                    .textField("Name your structure:", "e.g. Modern_House", { defaultValue: "" });

                nameForm.show(player).then((res) => {
                    if (res.canceled || !res.formValues[0]?.trim()) return;

                    const inputName = res.formValues[0].trim().replace(/\s+/g, "_");
                    
                    saveLargeDynamicProperty(`struct_${inputName}`, JSON.stringify({ blocks, rotation: cache.rotation ?? 0 }));
                    
                    try {
                        const minX = Math.min(start.x, end.x);
                        const minY = Math.min(start.y, end.y);
                        const minZ = Math.min(start.z, end.z);
                        const maxX = Math.max(start.x, end.x);
                        const maxY = Math.max(start.y, end.y);
                        const maxZ = Math.max(start.z, end.z);
                        
                        player.dimension.runCommandAsync(`structure save "mystruct_${inputName}" ${minX} ${minY} ${minZ} ${maxX} ${maxY} ${maxZ} true disk`).catch(() => {});
                    } catch(err) {
                        player.sendMessage("§c[Warning] Could not save the structure through a command: " + err);
                    }

                    let history = JSON.parse(world.getDynamicProperty("cannon_history_list") || "[]");
                    if (!history.includes(inputName)) history.push(inputName);
                    world.setDynamicProperty("cannon_history_list", JSON.stringify(history));

                    const updatedQuill = new ItemStack("morecreate:schematic_and_quill", 1);
                    updatedQuill.setLore([`§7Structure: ${inputName}`]);
                    
                    const inv = player.getComponent("minecraft:inventory").container;
                    inv.setItem(player.selectedSlotIndex, updatedQuill);

                    player.sendMessage("§aPoint B set. Structure saved safely.");
                });
            });
        }
    }

    if (item.typeId === "morecreate:schematic") {
        uiDebounce.add(player.id);
        system.runTimeout(() => uiDebounce.delete(player.id), 10);
        const lore = item.getLore();
        if (lore && lore.length > 0) {
            openSchematicOptionsUI(player, lore[0].replace("§7Estrutura: ", "").trim());
        }
    }

    if (item.typeId === "morecreate:clipboard") {
        uiDebounce.add(player.id);
        system.runTimeout(() => uiDebounce.delete(player.id), 10);
        
        const lore = item.getLore();
        if (lore && lore.length > 1) {
            let bodyText = `§dRecorded Structure List\n\n`;
            for (let i = 1; i < lore.length; i++) bodyText += `${lore[i]}\n`;
            system.run(() => {
                new ActionFormData().title("§7Material List").body(bodyText).button("OK").show(player);
            });
        } else if (lore && lore.length === 1) {
            const structName = lore[0].replace("§7Estrutura: ", "").trim();
            showMaterialList(player, structName, null);
        }
    }
});

world.afterEvents.playerPlaceBlock.subscribe((ev) => {
    const { block } = ev;
    if (block.typeId === "morecreate:cannon") {
        const loc = block.location;
        const dim = block.dimension;

        system.run(() => {
            dim.runCommandAsync(`setblock ${loc.x} ${loc.y} ${loc.z} morecreate:cannon_base`).catch(() => {});

            const cannonKey = `${loc.x}_${loc.y}_${loc.z}`;
            
            world.setDynamicProperty(`cannon_struct_${cannonKey}`, "");
            world.setDynamicProperty(`cannon_powder_${cannonKey}`, 0);
            world.setDynamicProperty(`cannon_progress_${cannonKey}`, 0);
            world.setDynamicProperty(`running_${cannonKey}`, false);
            world.setDynamicProperty(`cannon_initialized_${cannonKey}`, true);
            world.setDynamicProperty(`skip_missing_${cannonKey}`, false);
            world.setDynamicProperty(`replace_blocks_${cannonKey}`, false);
            world.setDynamicProperty(`replace_containers_${cannonKey}`, false);
            world.setDynamicProperty(`drop_on_replace_${cannonKey}`, false);
            world.setDynamicProperty(`keep_active_${cannonKey}`, false);

            try {
                const existingEntities = dim.getEntities({
                    type: "morecreate:cannon_entity",
                    location: { x: loc.x + 0.5, y: loc.y, z: loc.z + 0.5 },
                    maxDistance: 0.5
                });
                if (existingEntities.length === 0) {
                    const spawnedEntity = dim.spawnEntity("morecreate:cannon_entity", { x: loc.x + 0.5, y: loc.y, z: loc.z + 0.5 });
                    spawnedEntity.nameTag = "CreateCanon";

                    const px = Math.floor(spawnedEntity.location.x);
                    const py = Math.floor(spawnedEntity.location.y);
                    const pz = Math.floor(spawnedEntity.location.z);

                    dim.runCommandAsync(`replaceitem entity @e[type=morecreate:cannon_entity,x=${px},y=${py},z=${pz},r=1] slot.inventory 1 morecreate:clipboard_button 1`).catch(() => {});
                    dim.runCommandAsync(`replaceitem entity @e[type=morecreate:cannon_entity,x=${px},y=${py},z=${pz},r=1] slot.inventory 6 morecreate:stop_button 1`).catch(() => {});
                    dim.runCommandAsync(`replaceitem entity @e[type=morecreate:cannon_entity,x=${px},y=${py},z=${pz},r=1] slot.inventory 7 morecreate:start_button 1`).catch(() => {});
                    dim.runCommandAsync(`replaceitem entity @e[type=morecreate:cannon_entity,x=${px},y=${py},z=${pz},r=1] slot.inventory 8 morecreate:reset_button 1`).catch(() => {});
                    dim.runCommandAsync(`replaceitem entity @e[type=morecreate:cannon_entity,x=${px},y=${py},z=${pz},r=1] slot.inventory 9 morecreate:confirm_button 1`).catch(() => {});
                    dim.runCommandAsync(`replaceitem entity @e[type=morecreate:cannon_entity,x=${px},y=${py},z=${pz},r=1] slot.inventory 10 morecreate:configures_button 1`).catch(() => {});
                }
            } catch(e){}
        });
    }
});

function openSchematicOptionsUI(player, structName) {
    const rawData = loadLargeDynamicProperty(`struct_${structName}`);
    if (!rawData) return;

    let data = JSON.parse(rawData);
    
    let isFixed = world.getDynamicProperty(`p_fixed_${player.id}_${structName}`) || false;
    let savedLocRaw = world.getDynamicProperty(`p_loc_${player.id}_${structName}`);
    let currentOffsetPos = savedLocRaw ? JSON.parse(savedLocRaw) : null;
    
    let isSelectingLocation = world.getDynamicProperty(`p_selecting_${player.id}_${structName}`) ?? false;
    let previewType = world.getDynamicProperty(`p_preview_type_${player.id}_${structName}`) ?? 0;

    let cache = playerSelections.get(player.id) || {};
    cache.isSelectingLocation = isSelectingLocation;
    cache.isFixed = isFixed;
    cache.currentOffsetPos = currentOffsetPos;
    cache.previewType = previewType;

    let currentRotation = data.rotation ?? 0;

    system.run(() => {
        const form = new ModalFormData()
            .title("§7Edit Schematic")
            .textField("Structure name:", "e.g. My_Tower", { defaultValue: structName })
            .dropdown("Rotate Structure:", ["0°", "90°", "180°", "270°"], { defaultValueIndex: (currentRotation / 90) || 0 })
            .toggle("Show preview", { defaultValue: cache.isSelectingLocation })
            .dropdown("Preview Type:", ["Box (Outline)", "Dynamic (Per Block)"], { defaultValueIndex: cache.previewType })
            .toggle("Pin structure", { defaultValue: cache.isFixed ?? false });

        form.show(player).then((response) => {
            if (response.canceled) return;

            let newName = response.formValues[0]?.trim();
            data.rotation = response.formValues[1] * 90;
            cache.isSelectingLocation = response.formValues[2];
            cache.previewType = response.formValues[3];
            cache.isFixed = response.formValues[4];
            playerSelections.set(player.id, cache);

            world.setDynamicProperty(`p_selecting_${player.id}_${structName}`, cache.isSelectingLocation);
            world.setDynamicProperty(`p_preview_type_${player.id}_${structName}`, cache.previewType);
            world.setDynamicProperty(`p_fixed_${player.id}_${structName}`, cache.isFixed);
            if (cache.currentOffsetPos) {
                world.setDynamicProperty(`p_loc_${player.id}_${structName}`, JSON.stringify(cache.currentOffsetPos));
            }

            saveLargeDynamicProperty(`struct_${structName}`, JSON.stringify(data));

            if (newName && newName !== "" && newName !== structName) {
                saveLargeDynamicProperty(`struct_${newName}`, JSON.stringify(data));
                
                world.setDynamicProperty(`p_selecting_${player.id}_${newName}`, cache.isSelectingLocation);
                world.setDynamicProperty(`p_preview_type_${player.id}_${newName}`, cache.previewType);
                world.setDynamicProperty(`p_fixed_${player.id}_${newName}`, cache.isFixed);
                if (cache.currentOffsetPos) {
                    world.setDynamicProperty(`p_loc_${player.id}_${newName}`, JSON.stringify(cache.currentOffsetPos));
                }

                let history = JSON.parse(world.getDynamicProperty("cannon_history_list") || "[]");
                history = history.map(h => h === structName ? newName : h);
                world.setDynamicProperty("cannon_history_list", JSON.stringify(history));
                
                const inv = player.getComponent("minecraft:inventory").container;
                const item = inv.getItem(player.selectedSlotIndex);
                if (item) {
                    item.setLore([`§7Structure: ${newName}`]);
                    inv.setItem(player.selectedSlotIndex, item);
                }
                clearLargeDynamicProperty(`struct_${structName}`);
            }
        });
    });
}

function openConfigUI(player, cannonKey) {
    let skipMissing = world.getDynamicProperty(`skip_missing_${cannonKey}`) || false;
    let replaceBlocks = world.getDynamicProperty(`replace_blocks_${cannonKey}`) || false;
    let replaceContainers = world.getDynamicProperty(`replace_containers_${cannonKey}`) || false;
    let dropOnReplace = world.getDynamicProperty(`drop_on_replace_${cannonKey}`) || false;
    let keepActive = world.getDynamicProperty(`keep_active_${cannonKey}`) || false;

    const form = new ModalFormData()
        .title("§eCannon Settings")
        .toggle("§b>> §rSkip missing blocks", { defaultValue: skipMissing })
        .toggle("§a== §rReplace normal blocks", { defaultValue: replaceBlocks })
        .toggle("§d++ §rReplace blocks with inventories", { defaultValue: replaceContainers })
        .toggle("§6** §rDrop blocks when replacing", { defaultValue: dropOnReplace })
        .toggle("§e[*] §rKeep the cannon running without blocks (Standby)", { defaultValue: keepActive });

    form.show(player).then((response) => {
        if (response.canceled) return;
        world.setDynamicProperty(`skip_missing_${cannonKey}`, response.formValues[0]);
        world.setDynamicProperty(`replace_blocks_${cannonKey}`, response.formValues[1]);
        world.setDynamicProperty(`replace_containers_${cannonKey}`, response.formValues[2]);
        world.setDynamicProperty(`drop_on_replace_${cannonKey}`, response.formValues[3]);
        world.setDynamicProperty(`keep_active_${cannonKey}`, response.formValues[4]);
    });
}

function getAdjacentInventories(dimension, centerLoc) {
    const containers = [];
    const checkedLocations = new Set();
    const horizontalDirections = [{ x: 0, z: -1 }, { x: 0, z: 1 }, { x: 1, z: 0 }, { x: -1, z: 0 }];

    for (let x = -3; x <= 3; x++) {
        for (let y = -2; y <= 2; y++) {
            for (let z = -3; z <= 3; z++) {
                const targetX = centerLoc.x + x;
                const targetY = centerLoc.y + y;
                const targetZ = centerLoc.z + z;
                const key = `${targetX}_${targetY}_${targetZ}`;

                if (checkedLocations.has(key)) continue;

                try {
                    const block = dimension.getBlock({ x: targetX, y: targetY, z: targetZ });
                    const invComp = block?.getComponent("minecraft:inventory");
                    
                    if (invComp && invComp.container) {
                        containers.push(invComp.container);
                        checkedLocations.add(key);

                        if (block.typeId === "minecraft:chest") {
                            for (const hDir of horizontalDirections) {
                                const sideX = targetX + hDir.x;
                                const sideZ = targetZ + hDir.z;
                                const sideKey = `${sideX}_${targetY}_${sideZ}`;

                                if (checkedLocations.has(sideKey)) continue;

                                const sideBlock = dimension.getBlock({ x: sideX, y: targetY, z: sideZ });
                                if (sideBlock && sideBlock.typeId === "minecraft:chest") {
                                    const sideInvComp = sideBlock.getComponent("minecraft:inventory");
                                    if (sideInvComp && sideInvComp.container) {
                                        containers.push(sideInvComp.container);
                                        checkedLocations.add(sideKey);
                                    }
                                }
                            }
                        }
                    }
                } catch(e){}
            }
        }
    }

    try {
        const entitiesAround = dimension.getEntities({
            location: centerLoc,
            maxDistance: 6
        });

        for (const entity of entitiesAround) {
            if (IGNORED_ENTITIES.includes(entity.typeId)) continue;

            const entInventory = entity.getComponent("minecraft:inventory");
            if (entInventory && entInventory.container) {
                containers.push(entInventory.container);
            }
        }
    } catch(e){}

    return containers;
}

function countItemsInContainers(containers) {
    const counts = {};
    for (const container of containers) {
        for (let i = 0; i < container.size; i++) {
            const item = container.getItem(i);
            if (item) counts[item.typeId] = (counts[item.typeId] || 0) + item.amount;
        }
    }
    return counts;
}

function formatPackQuantity(totalBlocks) {
    if (totalBlocks <= 0) return "§a✓";
    const packs = Math.floor(totalBlocks / 64);
    const remainder = totalBlocks % 64;
    return packs > 0 ? `${packs} stacks + ${remainder}` : `${remainder} blocks`;
}

function showMaterialList(player, structName, canonLocation) {
    const rawData = loadLargeDynamicProperty(`struct_${structName}`);
    if (!rawData) return;

    const data = JSON.parse(rawData);
    const required = {};
    if (data.blocks) {
        for (const b of data.blocks) {
            if (b.isEntityAnchor) continue;
            if (CREATIVE_ONLY_BLOCKS.includes(b.type)) continue;
            required[b.type] = (required[b.type] || 0) + 1;
        }
    }

    let storageCounts = {};
    if (canonLocation) {
        const containers = getAdjacentInventories(player.dimension, canonLocation);
        storageCounts = countItemsInContainers(containers);
    }

    let bodyText = `§dMaterials required: ${structName}\n\n`;
    for (const [type, reqQty] of Object.entries(required)) {
        const name = type.replace("minecraft:", "").replace(/_/g, " ").toUpperCase();
        const available = storageCounts[type] || 0;
        const progressColor = (available >= reqQty) ? "§a" : "§c";
        const missingAmount = Math.max(0, reqQty - available);
        const missingText = missingAmount > 0 ? formatPackQuantity(missingAmount) : "§a✓";

        bodyText += `§f• ${name}: ${progressColor}${available}§f/${reqQty} (${missingText})\n`;
    }

    system.run(() => {
        new ActionFormData().title("§7Material List").body(bodyText).button("OK").show(player);
    });
}

function spawnBeamParticles(dimension, startLoc, endLoc) {
    const points = 5; 
    for (let i = 0; i <= points; i++) {
        const t = i / points;
        const pX = startLoc.x + (endLoc.x - startLoc.x) * t;
        const pY = startLoc.y + (endLoc.y - startLoc.y) * t;
        const pZ = startLoc.z + (endLoc.z - startLoc.z) * t;
        system.runTimeout(() => {
            try { dimension.spawnParticle("minecraft:basic_smoke_particle", { x: pX, y: pY, z: pZ }); } catch(e){}
        }, Math.floor(t * 2));
    }
}

const CARDINAL_CYCLE = ["north", "east", "south", "west"];
const FACING6_INT_MAP = ["down", "up", "north", "south", "west", "east"];
const WEIRDO_DIR_MAP = ["east", "west", "south", "north"];
const OLD_DIRECTION_MAP = ["south", "west", "north", "east"];

function rotateCardinalString(value, steps) {
    const idx = CARDINAL_CYCLE.indexOf(value);
    if (idx === -1) return value;
    return CARDINAL_CYCLE[(idx + steps) % 4];
}

function rotateBlockStates(typeId, states, steps) {
    if (!states || steps === 0) return states;
    const s = { ...states };

    if (typeof s["minecraft:cardinal_direction"] === "string") {
        s["minecraft:cardinal_direction"] = rotateCardinalString(s["minecraft:cardinal_direction"], steps);
    }

    if (typeof s["minecraft:facing_direction"] === "string" && CARDINAL_CYCLE.includes(s["minecraft:facing_direction"])) {
        s["minecraft:facing_direction"] = rotateCardinalString(s["minecraft:facing_direction"], steps);
    } else if (typeof s["facing_direction"] === "number") {
        const dir = FACING6_INT_MAP[s["facing_direction"]];
        if (CARDINAL_CYCLE.includes(dir)) {
            s["facing_direction"] = FACING6_INT_MAP.indexOf(rotateCardinalString(dir, steps));
        }
    }

    if (typeof s["minecraft:block_face"] === "string" && CARDINAL_CYCLE.includes(s["minecraft:block_face"])) {
        s["minecraft:block_face"] = rotateCardinalString(s["minecraft:block_face"], steps);
    }

    if (typeof s["weirdo_direction"] === "number") {
        const dir = WEIRDO_DIR_MAP[s["weirdo_direction"]];
        s["weirdo_direction"] = WEIRDO_DIR_MAP.indexOf(rotateCardinalString(dir, steps));
    }

    if (typeof s["direction"] === "number") {
        const dir = OLD_DIRECTION_MAP[s["direction"] % 4];
        s["direction"] = OLD_DIRECTION_MAP.indexOf(rotateCardinalString(dir, steps));
    }

    if (typeof s["door_direction"] === "number") {
        const dir = OLD_DIRECTION_MAP[s["door_direction"] % 4];
        s["door_direction"] = OLD_DIRECTION_MAP.indexOf(rotateCardinalString(dir, steps));
    }

    if (typeof s["torch_facing_direction"] === "string" && CARDINAL_CYCLE.includes(s["torch_facing_direction"])) {
        s["torch_facing_direction"] = rotateCardinalString(s["torch_facing_direction"], steps);
    }

    if (typeof s["ground_sign_direction"] === "number") {
        s["ground_sign_direction"] = (s["ground_sign_direction"] + steps * 4) % 16;
    }

    const axisKey = typeof s["minecraft:pillar_axis"] === "string" ? "minecraft:pillar_axis"
        : (typeof s["pillar_axis"] === "string" ? "pillar_axis" : null);
    if (axisKey && steps % 2 === 1) {
        if (s[axisKey] === "x") s[axisKey] = "z";
        else if (s[axisKey] === "z") s[axisKey] = "x";
    }

    return s;
}

function getTemporalBottleLevel(dimension, blockLocation) {
    try {
        const entities = dimension.getEntities({
            location: blockLocation,
            maxDistance: 1.5
        });

        for (const ent of entities) {
            let level = ent.getProperty("temporal_bottle:level") ?? ent.getProperty("level") ?? 0;
            if (level > 0) return level;
        }
    } catch (e) {}
    return 0;
}

function executeCannonBuild(player, structName, blockLocation) {
    const cannonKey = `${blockLocation.x}_${blockLocation.y}_${blockLocation.z}`;
    const rawData = loadLargeDynamicProperty(`struct_${structName}`);
    if (!rawData) return;

    const data = JSON.parse(rawData);
    
    playerSelections.set(`task_${cannonKey}`, true);

    let savedLocRaw = world.getDynamicProperty(`p_loc_${player.id}_${structName}`);
    const basePos = savedLocRaw ? JSON.parse(savedLocRaw) : null;

    if (!basePos) {
        world.setDynamicProperty(`running_${cannonKey}`, false);
        playerSelections.delete(`task_${cannonKey}`);
        return;
    }

    let powderPool = world.getDynamicProperty(`cannon_powder_${cannonKey}`) || 0;
    if (powderPool <= 0) {
        world.setDynamicProperty(`running_${cannonKey}`, false);
        playerSelections.delete(`task_${cannonKey}`);
        return;
    }

    world.setDynamicProperty(`running_${cannonKey}`, true);

    let maxRelX = 0, maxRelY = 0, maxRelZ = 0;
    for (const b of data.blocks) {
        if (b.relX > maxRelX) maxRelX = b.relX;
        if (b.relY > maxRelY) maxRelY = b.relY;
        if (b.relZ > maxRelZ) maxRelZ = b.relZ;
    }
    const midX = maxRelX / 2;
    const midZ = maxRelZ / 2;

    const structRotation = data.rotation ?? 0;
    const angleRad = (structRotation * Math.PI) / 180;
    const cos = Math.cos(angleRad);
    const sin = Math.sin(angleRad);
    const rotationSteps = (((Math.round(structRotation / 90)) % 4) + 4) % 4;

    let index = world.getDynamicProperty(`cannon_progress_${cannonKey}`) || 0;

    const runBuildStep = async () => {
        if (!world.getDynamicProperty(`running_${cannonKey}`)) {
            playerSelections.delete(`task_${cannonKey}`);
            return;
        }

        powderPool = world.getDynamicProperty(`cannon_powder_${cannonKey}`) || 0;
        if (powderPool <= 0) {
            world.setDynamicProperty(`running_${cannonKey}`, false);
            playerSelections.delete(`task_${cannonKey}`);
            return;
        }

        let bottleLevel = getTemporalBottleLevel(player.dimension, blockLocation);
        let blocksPerTick = 1;

        if (bottleLevel >= 256) {
            blocksPerTick = 256;
        } else if (bottleLevel >= 64) {
            blocksPerTick = 8;
        } else if (bottleLevel >= 16) {
            blocksPerTick = 4;
        } else if (bottleLevel >= 4) {
            blocksPerTick = 2;
        }

        for (let stepCount = 0; stepCount < blocksPerTick; stepCount++) {
            if (index >= data.blocks.length) break;

            let skipMissing = world.getDynamicProperty(`skip_missing_${cannonKey}`) || false;
            let replaceBlocks = world.getDynamicProperty(`replace_blocks_${cannonKey}`) || false;
            let replaceContainers = world.getDynamicProperty(`replace_containers_${cannonKey}`) || false;
            let dropOnReplace = world.getDynamicProperty(`drop_on_replace_${cannonKey}`) || false;
            let keepActive = world.getDynamicProperty(`keep_active_${cannonKey}`) || false;

            let foundValidTarget = false;
            let finalTargetPos = null;
            let currentTargetBlock = null;

            while (index < data.blocks.length) {
                const b = data.blocks[index];
                if (b.isEntityAnchor || CREATIVE_ONLY_BLOCKS.includes(b.type)) { 
                    index++; 
                    world.setDynamicProperty(`cannon_progress_${cannonKey}`, index);
                    continue; 
                }

                const centerX = b.relX - midX;
                const centerZ = b.relZ - midZ;
                
                const rotX = Math.floor(centerX * cos - centerZ * sin + 0.5);
                const rotZ = Math.floor(centerX * sin + centerZ * cos + 0.5);
                
                finalTargetPos = { 
                    x: Math.floor(basePos.x + rotX + midX), 
                    y: basePos.y + b.relY, 
                    z: Math.floor(basePos.z + rotZ + midZ) 
                };

                try {
                    await player.dimension.requestChunkLoading(finalTargetPos);
                } catch(e){}

                const blockAtWorld = player.dimension.getBlock(finalTargetPos);
                if (blockAtWorld && blockAtWorld.typeId === b.type) {
                    index++;
                    world.setDynamicProperty(`cannon_progress_${cannonKey}`, index);
                    continue;
                }

                if (blockAtWorld && !blockAtWorld.isAir) {
                    const hasInventory = blockAtWorld.getComponent("minecraft:inventory") !== undefined;
                    if (hasInventory && !replaceContainers) { index++; world.setDynamicProperty(`cannon_progress_${cannonKey}`, index); continue; }
                    if (!hasInventory && !replaceBlocks) { index++; world.setDynamicProperty(`cannon_progress_${cannonKey}`, index); continue; }
                }

                const adjacentContainers = getAdjacentInventories(player.dimension, blockLocation);
                let itemRemovido = false;

                for (const container of adjacentContainers) {
                    for (let i = 0; i < container.size; i++) {
                        const slotItem = container.getItem(i);
                        if (slotItem && slotItem.typeId === b.type) {
                            if (slotItem.amount > 1) { slotItem.amount -= 1; container.setItem(i, slotItem); }
                            else { container.setItem(i, null); }
                            itemRemovido = true; break;
                        }
                    }
                    if (itemRemovido) break;
                }

                if (itemRemovido) { currentTargetBlock = b; foundValidTarget = true; break; } 
                else {
                    if (skipMissing) { index++; world.setDynamicProperty(`cannon_progress_${cannonKey}`, index); } 
                    else {
                        const blockNameFormatted = b.type.replace("minecraft:", "").replace(/_/g, " ").toUpperCase();
                        const warningMsg = `§c[Cannon] Missing block: §e${blockNameFormatted}`;
                        
                        try {
                            const nearbyPlayersForMsg = player.dimension.getPlayers({ location: blockLocation, maxDistance: 4 });
                            for (const pNearby of nearbyPlayersForMsg) {
                                pNearby.onScreenDisplay.setActionBar(warningMsg);
                            }
                        } catch(e){}

                        if (keepActive) {
                            scheduleNextStep(10); 
                            return; 
                        } else {
                            world.setDynamicProperty(`running_${cannonKey}`, false);
                            playerSelections.delete(`task_${cannonKey}`);
                            return;
                        }
                    }
                }
            }

            if (index >= data.blocks.length && !foundValidTarget) {
                world.setDynamicProperty(`running_${cannonKey}`, false);
                world.setDynamicProperty(`cannon_progress_${cannonKey}`, 0);
                playerSelections.delete(`task_${cannonKey}`);
                player.sendMessage("§aConstruction completed successfully.");
                return;
            }

            if (!foundValidTarget || !finalTargetPos || !currentTargetBlock) continue;

            try {
                const existingEntities = player.dimension.getEntities({
                    type: "morecreate:cannon_entity",
                    location: { x: blockLocation.x + 0.5, y: blockLocation.y, z: blockLocation.z + 0.5 },
                    maxDistance: 0.6 
                });
                const canonEntity = existingEntities[0];
                if (canonEntity) {
                    const dx = finalTargetPos.x - blockLocation.x;
                    const dz = finalTargetPos.z - blockLocation.z;
                    let angle = Math.atan2(dz, dx) * (180 / Math.PI) - 180;
                    canonEntity.teleport({ x: blockLocation.x + 0.5, y: blockLocation.y, z: blockLocation.z + 0.5 }, { rotation: { x: 0, y: angle } });
                }
            } catch(e){}

            try {
                const currentBlockInWorld = player.dimension.getBlock(finalTargetPos);
                if (currentBlockInWorld) {
                    if (INDESTRUCTIBLE_BLOCKS.includes(currentBlockInWorld.typeId)) { index++; world.setDynamicProperty(`cannon_progress_${cannonKey}`, index); continue; }
                    if (!currentBlockInWorld.isAir && dropOnReplace) { player.dimension.runCommandAsync(`setblock ${finalTargetPos.x} ${finalTargetPos.y} ${finalTargetPos.z} air destroy`).catch(() => {}); }

                    const rotatedStates = rotateBlockStates(currentTargetBlock.type, currentTargetBlock.states, rotationSteps);
                    let perm;
                    try {
                        perm = BlockPermutation.resolve(currentTargetBlock.type, rotatedStates);
                    } catch (resolveError) {
                        perm = BlockPermutation.resolve(currentTargetBlock.type);
                    }

                    if (bottleLevel >= 256 || getGlobalBuildSpeed() <= 1) {
                        try {
                            currentBlockInWorld.setPermutation(perm);
                        } catch(exs){
                            player.dimension.runCommandAsync(`setblock ${finalTargetPos.x} ${finalTargetPos.y} ${finalTargetPos.z} ${currentTargetBlock.type}`).catch(()=>{});
                        }
                    } else {
                        const spawnLoc = { x: blockLocation.x + 0.5, y: blockLocation.y + 1.2, z: blockLocation.z + 0.5 };
                        
                        try {
                            player.dimension.spawnParticle("minecraft:basic_smoke_particle", spawnLoc);
                        } catch(e){}

                        const projectileMob = player.dimension.spawnEntity("morecreate:cannon_projectile", spawnLoc);
                        const itemEnt = player.dimension.spawnItem(new ItemStack(currentTargetBlock.type, 1), spawnLoc);
                        itemEnt.clearVelocity();

                        try {
                            itemEnt.addTag("cannon_flying_item");
                        } catch(e){}
                        
                        let t = 0;
                        const flyInterval = system.runInterval(() => {
                            t += 0.2;
                            if (t >= 1) {
                                system.clearRun(flyInterval);
                                try { projectileMob.remove(); } catch(e){}
                                try { itemEnt.remove(); } catch(e){}
                                
                                try {
                                    currentBlockInWorld.setPermutation(perm);
                                } catch(exs){
                                    player.dimension.runCommandAsync(`setblock ${finalTargetPos.x} ${finalTargetPos.y} ${finalTargetPos.z} ${currentTargetBlock.type}`).catch(()=>{});
                                }
                                return;
                            }
                            const curX = spawnLoc.x + (finalTargetPos.x + 0.5 - spawnLoc.x) * t;
                            const curZ = spawnLoc.z + (finalTargetPos.z + 0.5 - spawnLoc.z) * t;
                            const baseHeight = spawnLoc.y + (finalTargetPos.y + 0.5 - spawnLoc.y) * t;
                            const curY = baseHeight + (4.5 * 4 * t * (1 - t));
                            
                            try { projectileMob.teleport({ x: curX, y: curY - 0.5, z: curZ }); } catch(e){}
                            try { itemEnt.teleport({ x: curX, y: curY, z: curZ }); } catch(e){}
                        }, 1);

                        spawnBeamParticles(player.dimension, spawnLoc, { x: finalTargetPos.x + 0.5, y: finalTargetPos.y + 0.5, z: finalTargetPos.z + 0.5 });
                    }

                    powderPool--;
                    world.setDynamicProperty(`cannon_powder_${cannonKey}`, powderPool);
                }
            } catch (e) {}

            index++;
            world.setDynamicProperty(`cannon_progress_${cannonKey}`, index);
        }

        const currentSpeed = Math.max(1, getGlobalBuildSpeed());
        scheduleNextStep(currentSpeed);
    };

    function scheduleNextStep(ticks) {
        system.runTimeout(() => {
            runBuildStep();
        }, ticks);
    }

    runBuildStep();
}

function renderSelectionBoxFromData(dimension, blocks, offset, rotation) {
    if (!offset || !blocks || blocks.length === 0) return;

    let maxRelX = 0, maxRelZ = 0, maxRelY = 0;
    for (const b of blocks) {
        if (b.relX > maxRelX) maxRelX = b.relX;
        if (b.relY > maxRelY) maxRelY = b.relY;
        if (b.relZ > maxRelZ) maxRelZ = b.relZ;
    }
    const midX = maxRelX / 2;
    const midZ = maxRelZ / 2;
    const rad = (rotation * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);

    const calcPos = (rx, ry, rz) => {
        const cx = rx - midX;
        const cz = rz - midZ;
        return {
            x: Math.floor(offset.x + cx * cos - cz * sin + midX) + 0.5,
            y: offset.y + ry + 0.3,
            z: Math.floor(offset.z + cx * sin + cz * cos + midZ) + 0.5
        };
    };

    try {
        const p000 = calcPos(0, 0, 0);
        const p100 = calcPos(maxRelX, 0, 0);
        const p001 = calcPos(0, 0, maxRelZ);
        const p101 = calcPos(maxRelX, 0, maxRelZ);
        const p010 = calcPos(0, maxRelY, 0);
        const p110 = calcPos(maxRelX, maxRelY, 0);
        const p011 = calcPos(0, maxRelY, maxRelZ);
        const p111 = calcPos(maxRelX, maxRelY, maxRelZ);

        const spawnLine = (pA, pB) => {
            const steps = 4;
            for (let i = 0; i <= steps; i++) {
                const t = i / steps;
                dimension.spawnParticle("morecreate:schematic_cube", {
                    x: pA.x + (pB.x - pA.x) * t,
                    y: pA.y + (pB.y - pA.y) * t,
                    z: pA.z + (pB.z - pA.z) * t
                });
            }
        };

        spawnLine(p000, p100);
        spawnLine(p100, p101);
        spawnLine(p101, p001);
        spawnLine(p001, p000);

        spawnLine(p010, p110);
        spawnLine(p110, p111);
        spawnLine(p111, p011);
        spawnLine(p011, p010);

        spawnLine(p000, p010);
        spawnLine(p100, p110);
        spawnLine(p101, p111);
        spawnLine(p001, p011);

    } catch(e){}
}

function renderVisualizer(dimension, blocks, offset, rotation) {
    if (!offset || !blocks) return;
    let maxRelX = 0, maxRelZ = 0;
    for (const b of blocks) {
        if (b.relX > maxRelX) maxRelX = b.relX;
        if (b.relZ > maxRelZ) maxRelZ = b.relZ;
    }
    const midX = maxRelX / 2;
    const midZ = maxRelZ / 2;
    const rad = (rotation * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);

    try {
        for (const b of blocks) {
            const pX = b.isEntityAnchor 
                ? offset.x + 0.5 
                : Math.floor(offset.x + (b.relX - midX) * cos - (b.relZ - midZ) * sin + midX) + 0.5;
            const pY = offset.y + b.relY;
            const pZ = b.isEntityAnchor 
                ? offset.z + 0.5 
                : Math.floor(offset.z + (b.relX - midX) * sin + (b.relZ - midZ) * cos + midZ) + 0.5;
            
            dimension.spawnParticle("morecreate:schematic_cube", { x: pX, y: pY + 0.3, z: pZ });
        }
    } catch(e){}
}

function renderSelectionBoxParticles(dimension, start, end) {
    const minX = Math.min(start.x, end.x);
    const minY = Math.min(start.y, end.y);
    const minZ = Math.min(start.z, end.z);
    const maxX = Math.max(start.x, end.x) + 1;
    const maxY = Math.max(start.y, end.y) + 1;
    const maxZ = Math.max(start.z, end.z) + 1;

    try {
        for (let x = minX; x <= maxX; x += 0.5) {
            dimension.spawnParticle("morecreate:schematic_cube", { x: x, y: minY + 0.3, z: minZ });
            dimension.spawnParticle("morecreate:schematic_cube", { x: x, y: minY + 0.3, z: maxZ });
            dimension.spawnParticle("morecreate:schematic_cube", { x: x, y: maxY + 0.3, z: minZ });
            dimension.spawnParticle("morecreate:schematic_cube", { x: x, y: maxY + 0.3, z: maxZ });
        }
        for (let z = minZ; z <= maxZ; z += 0.5) {
            dimension.spawnParticle("morecreate:schematic_cube", { x: minX, y: minY + 0.3, z: z });
            dimension.spawnParticle("morecreate:schematic_cube", { x: maxX, y: minY + 0.3, z: z });
            dimension.spawnParticle("morecreate:schematic_cube", { x: minX, y: maxY + 0.3, z: z });
            dimension.spawnParticle("morecreate:schematic_cube", { x: maxX, y: maxY + 0.3, z: maxZ });
        }
        for (let y = minY; y <= maxY; y += 0.5) {
            dimension.spawnParticle("morecreate:schematic_cube", { x: minX, y: y + 0.3, z: minZ });
            dimension.spawnParticle("morecreate:schematic_cube", { x: maxX, y: y + 0.3, z: minZ });
            dimension.spawnParticle("morecreate:schematic_cube", { x: minX, y: y + 0.3, z: maxZ });
            dimension.spawnParticle("morecreate:schematic_cube", { x: maxX, y: maxY + 0.3, z: maxZ });
        }
    } catch(e){}
}
