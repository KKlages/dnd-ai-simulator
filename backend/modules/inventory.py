from typing import Dict, Any, List, Optional
from core.module_manager import GameModule

class Item:
    def __init__(self, name: str, item_type: str, properties: Dict[str, Any] = None):
        self.name = name
        self.type = item_type  # "weapon", "armor", "consumable", "misc"
        self.properties = properties or {}
        self.quantity = properties.get('quantity', 1)
        self.weight = properties.get('weight', 0)
        self.value = properties.get('value', 0)
    
    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "quantity": self.quantity,
            "weight": self.weight,
            "value": self.value,
            "properties": self.properties
        }

class InventoryModule(GameModule):
    """Handles character inventory and equipment"""
    
    def __init__(self, game_state_manager):
        super().__init__(game_state_manager)
        self._initialize_character_inventories()
    
    def _initialize_character_inventories(self):
        """Initialize inventory for all characters"""
        for character in self.gsm.characters.values():
            if not hasattr(character, 'inventory'):
                character.inventory = []
                character.equipped = {
                    "weapon": None,
                    "armor": None,
                    "shield": None
                }
                
                # Give starting equipment based on character type
                if character.type == "player":
                    self._give_starting_equipment(character)
    
    def _give_starting_equipment(self, character):
        """Give starting equipment to player character"""
        # Basic starting gear for a fighter
        starting_items = [
            Item("Longsword", "weapon", {
                "damage": "1d8",
                "damage_type": "slashing", 
                "attack_bonus": 0,
                "weight": 3
            }),
            Item("Chain Mail", "armor", {
                "ac_bonus": 6,
                "weight": 55,
                "stealth_disadvantage": True
            }),
            Item("Shield", "shield", {
                "ac_bonus": 2,
                "weight": 6
            }),
            Item("Healing Potion", "consumable", {
                "healing": "2d4+2",
                "quantity": 2
            }),
            Item("Rations", "misc", {
                "quantity": 10,
                "weight": 0.5
            })
        ]
        
        for item in starting_items:
            character.inventory.append(item)
        
        # Auto-equip basic gear
        self._equip_item(character, "Longsword")
        self._equip_item(character, "Chain Mail")
        self._equip_item(character, "Shield")
    
    def can_handle(self, action_data: Dict[str, Any]) -> bool:
        return action_data.get('type') in ['equip', 'unequip', 'use_item', 'drop_item']
    
    def process_action(self, action_data: Dict[str, Any]) -> bool:
        action_type = action_data.get('type')
        character_id = action_data.get('character_id', 'player')
        item_name = action_data.get('item_name')
        
        character = self.gsm.get_character_by_id(character_id)
        if not character:
            return False
        
        if action_type == 'equip':
            return self._equip_item(character, item_name)
        elif action_type == 'unequip':
            return self._unequip_item(character, item_name)
        elif action_type == 'use_item':
            return self._use_item(character, item_name)
        elif action_type == 'drop_item':
            return self._drop_item(character, item_name)
        
        return False
    
    def _equip_item(self, character, item_name: str) -> bool:
        """Equip an item from inventory"""
        item = self._find_item_in_inventory(character, item_name)
        if not item:
            self.gsm.add_to_log(f"{character.name} doesn't have {item_name}")
            return False
        
        # Unequip current item in that slot
        if item.type in character.equipped and character.equipped[item.type]:
            self._unequip_item(character, character.equipped[item.type].name)
        
        # Equip new item
        character.equipped[item.type] = item
        
        # Apply bonuses
        self._apply_item_bonuses(character, item, equip=True)
        
        self.gsm.add_to_log(f"{character.name} equips {item_name}")
        return True
    
    def _unequip_item(self, character, item_name: str) -> bool:
        """Unequip an equipped item"""
        for slot, item in character.equipped.items():
            if item and item.name == item_name:
                character.equipped[slot] = None
                self._apply_item_bonuses(character, item, equip=False)
                self.gsm.add_to_log(f"{character.name} unequips {item_name}")
                return True
        return False
    
    def _use_item(self, character, item_name: str) -> bool:
        """Use a consumable item"""
        item = self._find_item_in_inventory(character, item_name)
        if not item or item.type != "consumable":
            return False
        
        # Handle different consumable types
        if "healing" in item.properties:
            healing = self._roll_dice(item.properties["healing"])
            old_hp = character.hp
            character.hp = min(character.max_hp, character.hp + healing)
            self.gsm.add_to_log(f"{character.name} uses {item_name} and heals {character.hp - old_hp} HP")
        
        # Remove one from inventory
        item.quantity -= 1
        if item.quantity <= 0:
            character.inventory.remove(item)
        
        return True
    
    def _drop_item(self, character, item_name: str) -> bool:
        """Drop an item from inventory"""
        item = self._find_item_in_inventory(character, item_name)
        if not item:
            return False
        
        character.inventory.remove(item)
        self.gsm.add_to_log(f"{character.name} drops {item_name}")
        return True
    
    def _find_item_in_inventory(self, character, item_name: str) -> Optional[Item]:
        """Find an item in character's inventory"""
        for item in character.inventory:
            if item.name.lower() == item_name.lower():
                return item
        return None
    
    def _apply_item_bonuses(self, character, item: Item, equip: bool = True):
        """Apply or remove item bonuses to character"""
        modifier = 1 if equip else -1
        
        if item.type == "weapon" and "attack_bonus" in item.properties:
            if not hasattr(character, 'equipment_attack_bonus'):
                character.equipment_attack_bonus = 0
            character.equipment_attack_bonus += item.properties["attack_bonus"] * modifier
        
        if item.type in ["armor", "shield"] and "ac_bonus" in item.properties:
            if not hasattr(character, 'equipment_ac_bonus'):
                character.equipment_ac_bonus = 0
            character.equipment_ac_bonus += item.properties["ac_bonus"] * modifier
            # Recalculate AC
            base_ac = 10 + (character.get_ability_modifier("dexterity") if item.type != "armor" else 0)
            character.ac = base_ac + character.equipment_ac_bonus
    
    def _roll_dice(self, dice_string: str) -> int:
        """Simple dice rolling for item effects"""
        import random
        import re
        
        # Parse dice string like "2d4+2"
        match = re.match(r'(\d+)d(\d+)(?:\+(\d+))?', dice_string)
        if not match:
            return 0
        
        num_dice = int(match.group(1))
        die_size = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0
        
        total = sum(random.randint(1, die_size) for _ in range(num_dice)) + modifier
        return total
    
    def get_available_actions(self, character_id: str) -> List[Dict[str, Any]]:
        character = self.gsm.get_character_by_id(character_id)
        if not character or not hasattr(character, 'inventory'):
            return []
        
        actions = []
        
        # Equipment actions
        for item in character.inventory:
            if item.type in ["weapon", "armor", "shield"]:
                actions.append({
                    "type": "equip",
                    "name": f"Equip {item.name}",
                    "description": f"Equip {item.name}",
                    "item_name": item.name
                })
            elif item.type == "consumable":
                actions.append({
                    "type": "use_item",
                    "name": f"Use {item.name}",
                    "description": f"Use {item.name}",
                    "item_name": item.name
                })
        
        return actions
    
    def get_character_inventory(self, character_id: str) -> Dict[str, Any]:
        """Get formatted inventory for display"""
        character = self.gsm.get_character_by_id(character_id)
        if not character or not hasattr(character, 'inventory'):
            return {}
        
        return {
            "inventory": [item.to_dict() for item in character.inventory],
            "equipped": {slot: item.to_dict() if item else None 
                        for slot, item in character.equipped.items()}
        }