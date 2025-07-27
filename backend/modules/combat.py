import random
from typing import Dict, Any, List
from core.module_manager import GameModule

class CombatModule(GameModule):
    """Handles combat actions and mechanics"""
    
    def can_handle(self, action_data: Dict[str, Any]) -> bool:
        return action_data.get('type') in ['attack', 'start_combat']
    
    def process_action(self, action_data: Dict[str, Any]) -> bool:
        action_type = action_data.get('type')
        
        if action_type == 'attack':
            return self._handle_attack(action_data)
        elif action_type == 'start_combat':
            return self._start_combat()
        
        return False
    
    def _handle_attack(self, action_data: Dict[str, Any]) -> bool:
        attacker_id = action_data.get('attacker_id', 'player')
        target_id = action_data.get('target_id')
        
        if not target_id:
            return False
        
        return self._execute_attack(attacker_id, target_id)
    
    def _execute_attack(self, attacker_id: str, target_id: str) -> bool:
        """Execute an attack between two characters"""
        attacker = self.gsm.get_character_by_id(attacker_id)
        target = self.gsm.get_character_by_id(target_id)
        
        if not attacker or not target:
            return False
        
        # Check if target is in range (simplified - assume melee range = 1 square)
        distance = abs(attacker.position[0] - target.position[0]) + abs(attacker.position[1] - target.position[1])
        if distance > 1:
            self.gsm.add_to_log(f"{attacker.name} is too far from {target.name} to attack!")
            return False
        
        # Roll to hit (d20 + attack modifier vs AC)
        attack_roll = random.randint(1, 20)
        attack_modifier = getattr(attacker, 'attack_bonus', 3)
        total_attack = attack_roll + attack_modifier
        
        self.gsm.add_to_log(f"{attacker.name} attacks {target.name}: rolls {attack_roll} + {attack_modifier} = {total_attack} vs AC {target.ac}")
        
        if total_attack >= target.ac:
            # Hit! Roll damage
            damage = random.randint(1, 8) + 2  # 1d8+2 damage
            self._apply_damage(target_id, damage)
            return True
        else:
            self.gsm.add_to_log(f"{attacker.name}'s attack misses {target.name}!")
            return True
    
    def _apply_damage(self, char_id: str, damage: int) -> bool:
        """Apply damage to character"""
        character = self.gsm.get_character_by_id(char_id)
        if not character:
            return False
        
        character.hp = max(0, character.hp - damage)
        self.gsm.add_to_log(f"{character.name} takes {damage} damage (HP: {character.hp}/{character.max_hp})")
        
        if character.hp <= 0:
            self.gsm.add_to_log(f"{character.name} is defeated!")
        
        return True
    
    def _start_combat(self) -> bool:
        """Initialize combat state"""
        self.gsm.combat_active = True
        self.gsm.add_to_log("Combat has started! Roll for initiative!")
        
        # Roll initiative for all characters
        for character in self.gsm.characters.values():
            initiative_roll = random.randint(1, 20)
            character.initiative = initiative_roll
            self.gsm.add_to_log(f"{character.name} rolls {initiative_roll} for initiative")
        
        # Create turn order sorted by initiative (highest first)
        self.gsm.turn_order = sorted(
            self.gsm.characters.keys(),
            key=lambda char_id: self.gsm.characters[char_id].initiative,
            reverse=True
        )
        
        self.gsm.current_turn_index = 0
        
        # Log the final turn order
        turn_order_names = [self.gsm.characters[char_id].name for char_id in self.gsm.turn_order]
        self.gsm.add_to_log(f"Turn order: {' -> '.join(turn_order_names)}")
        
        return True
    
    def advance_turn(self):
        """Move to the next character in the turn order"""
        self.gsm.current_turn_index += 1
        
        # Check if we've gone through all characters
        if self.gsm.current_turn_index >= len(self.gsm.turn_order):
            self.gsm.current_turn_index = 0
            self.gsm.add_to_log("--- New Round ---")
    
    def get_current_character(self):
        """Get the character whose turn it currently is"""
        if not self.gsm.turn_order:
            return None
        
        character_id = self.gsm.turn_order[self.gsm.current_turn_index]
        return self.gsm.characters.get(character_id)
    
    def is_combat_over(self) -> bool:
        """Check if combat should end"""
        monsters = [char for char in self.gsm.characters.values() if char.type == "monster" and char.hp > 0]
        players = [char for char in self.gsm.characters.values() if char.type == "player" and char.hp > 0]
        
        return len(monsters) == 0 or len(players) == 0
    
    def get_available_actions(self, character_id: str) -> List[Dict[str, Any]]:
        character = self.gsm.get_character_by_id(character_id)
        if not character:
            return []
        
        actions = [{
            "type": "attack",
            "name": "Attack",
            "description": "Attack a target within range",
            "requires_target": "character"
        }]
        
        return actions