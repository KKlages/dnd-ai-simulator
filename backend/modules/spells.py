from typing import Dict, Any, List, Optional
from core.module_manager import GameModule
import random

class Spell:
    def __init__(self, name: str, level: int, school: str, properties: Dict[str, Any]):
        self.name = name
        self.level = level
        self.school = school
        self.properties = properties
        self.casting_time = properties.get('casting_time', 'action')
        self.range = properties.get('range', 'touch')
        self.duration = properties.get('duration', 'instantaneous')
        self.components = properties.get('components', [])
        self.description = properties.get('description', '')
    
    def to_dict(self):
        return {
            "name": self.name,
            "level": self.level,
            "school": self.school,
            "casting_time": self.casting_time,
            "range": self.range,
            "duration": self.duration,
            "components": self.components,
            "description": self.description,
            "properties": self.properties
        }

class SpellsModule(GameModule):
    """Handles spell casting and spell management"""
    
    def __init__(self, game_state_manager):
        super().__init__(game_state_manager)
        self.spell_database = self._create_spell_database()
        self._initialize_character_spells()
    
    def _create_spell_database(self) -> Dict[str, Spell]:
        """Create a database of available spells"""
        spells = {
            "cure_wounds": Spell("Cure Wounds", 1, "evocation", {
                "casting_time": "action",
                "range": "touch",
                "duration": "instantaneous",
                "components": ["V", "S"],
                "healing": "1d8+SPELL_MOD",
                "description": "Touch a creature to heal 1d8 + spell modifier HP"
            }),
            "magic_missile": Spell("Magic Missile", 1, "evocation", {
                "casting_time": "action", 
                "range": "120 feet",
                "duration": "instantaneous",
                "components": ["V", "S"],
                "damage": "1d4+1",
                "missiles": 3,
                "description": "Create 3 darts of magical force, each dealing 1d4+1 damage"
            }),
            "shield": Spell("Shield", 1, "abjuration", {
                "casting_time": "reaction",
                "range": "self",
                "duration": "1 round",
                "components": ["V", "S"],
                "ac_bonus": 5,
                "description": "+5 AC until start of your next turn"
            }),
            "fireball": Spell("Fireball", 3, "evocation", {
                "casting_time": "action",
                "range": "150 feet", 
                "duration": "instantaneous",
                "components": ["V", "S", "M"],
                "damage": "8d6",
                "area": "20-foot radius",
                "save": "dexterity",
                "description": "Deal 8d6 fire damage in 20-foot radius (Dex save for half)"
            })
        }
        return spells
    
    def _initialize_character_spells(self):
        """Initialize spell lists for spellcasting characters"""
        for character in self.gsm.characters.values():
            if not hasattr(character, 'spells_known'):
                character.spells_known = []
                character.spell_slots = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
                character.spell_slots_used = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
                
                # Give spells based on character class
                if character.type == "player" and hasattr(character, 'class_stats'):
                    if character.class_stats.name.lower() in ['wizard', 'sorcerer', 'cleric']:
                        self._give_starting_spells(character)
    
    def _give_starting_spells(self, character):
        """Give starting spells to a spellcaster"""
        # Level 1 caster gets 2 spell slots and 2 spells known
        character.spell_slots[1] = 2
        character.spells_known = ["cure_wounds", "magic_missile"]
    
    def can_handle(self, action_data: Dict[str, Any]) -> bool:
        return action_data.get('type') in ['cast_spell', 'prepare_spell']
    
    def process_action(self, action_data: Dict[str, Any]) -> bool:
        action_type = action_data.get('type')
        character_id = action_data.get('character_id', 'player')
        spell_name = action_data.get('spell_name')
        
        character = self.gsm.get_character_by_id(character_id)
        if not character:
            return False
        
        if action_type == 'cast_spell':
            target_id = action_data.get('target_id')
            return self._cast_spell(character, spell_name, target_id)
        elif action_type == 'prepare_spell':
            return self._prepare_spell(character, spell_name)
        
        return False
    
    def _cast_spell(self, caster, spell_name: str, target_id: str = None) -> bool:
        """Cast a spell"""
        if not hasattr(caster, 'spells_known') or spell_name not in caster.spells_known:
            self.gsm.add_to_log(f"{caster.name} doesn't know {spell_name}")
            return False
        
        spell = self.spell_database.get(spell_name)
        if not spell:
            return False
        
        # Check spell slots
        if caster.spell_slots_used[spell.level] >= caster.spell_slots[spell.level]:
            self.gsm.add_to_log(f"{caster.name} has no {spell.level}-level spell slots left")
            return False
        
        # Use spell slot
        caster.spell_slots_used[spell.level] += 1
        
        # Get target
        target = None
        if target_id:
            target = self.gsm.get_character_by_id(target_id)
        else:
            target = caster  # Self-targeting spells
        
        # Execute spell effect
        success = self._execute_spell_effect(spell, caster, target)
        
        if success:
            self.gsm.add_to_log(f"{caster.name} casts {spell.name}")
        
        return success
    
    def _execute_spell_effect(self, spell: Spell, caster, target) -> bool:
        """Execute the magical effect of a spell"""
        spell_name = spell.name.lower().replace(" ", "_")
        
        if spell_name == "cure_wounds":
            if not target:
                return False
            healing = self._roll_dice("1d8") + 3  # Assuming +3 spell modifier
            old_hp = target.hp
            target.hp = min(target.max_hp, target.hp + healing)
            self.gsm.add_to_log(f"{target.name} heals {target.hp - old_hp} HP")
            return True
        
        elif spell_name == "magic_missile":
            if not target:
                return False
            total_damage = 0
            for i in range(3):  # 3 missiles
                damage = self._roll_dice("1d4") + 1
                total_damage += damage
            
            target.hp = max(0, target.hp - total_damage)
            self.gsm.add_to_log(f"Magic missiles hit {target.name} for {total_damage} damage")
            
            if target.hp <= 0:
                self.gsm.add_to_log(f"{target.name} is defeated!")
            return True
        
        elif spell_name == "shield":
            # Add temporary AC bonus (would need duration tracking)
            if not hasattr(caster, 'temp_ac_bonus'):
                caster.temp_ac_bonus = 0
            caster.temp_ac_bonus += 5
            caster.ac += 5
            self.gsm.add_to_log(f"{caster.name} gains +5 AC from Shield spell")
            return True
        
        elif spell_name == "fireball":
            # Area effect spell - damage all enemies in range
            damage = self._roll_dice("8d6")
            targets_hit = []
            
            # For simplicity, hit all monsters if cast by player
            for char in self.gsm.characters.values():
                if char.type == "monster" and char.hp > 0:
                    # Assume failed save for simplicity
                    char.hp = max(0, char.hp - damage)
                    targets_hit.append(char.name)
                    if char.hp <= 0:
                        self.gsm.add_to_log(f"{char.name} is defeated by the fireball!")
            
            if targets_hit:
                self.gsm.add_to_log(f"Fireball deals {damage} damage to: {', '.join(targets_hit)}")
            return True
        
        return False
    
    def _roll_dice(self, dice_string: str) -> int:
        """Roll dice for spell effects"""
        import re
        
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
        if not character or not hasattr(character, 'spells_known'):
            return []
        
        actions = []
        for spell_name in character.spells_known:
            spell = self.spell_database.get(spell_name)
            if spell and character.spell_slots_used[spell.level] < character.spell_slots[spell.level]:
                actions.append({
                    "type": "cast_spell",
                    "name": f"Cast {spell.name}",
                    "description": spell.description,
                    "spell_name": spell_name,
                    "requires_target": "character" if spell.range != "self" else None
                })
        
        return actions
    
    def get_character_spells(self, character_id: str) -> Dict[str, Any]:
        """Get character's spell information"""
        character = self.gsm.get_character_by_id(character_id)
        if not character or not hasattr(character, 'spells_known'):
            return {}
        
        return {
            "spells_known": [self.spell_database[name].to_dict() for name in character.spells_known if name in self.spell_database],
            "spell_slots": character.spell_slots,
            "spell_slots_used": character.spell_slots_used
        }