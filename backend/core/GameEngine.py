import random
from typing import Dict, List, Any, Optional
from GameStateManager import GameStateManager, Character

class GameEngine:
    def __init__(self, game_state_manager: GameStateManager):
        self.gsm = game_state_manager

    # NEW: Initialize turn order when combat begins
    def start_combat(self):
        """Initialize the turn order when combat begins"""
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

    # NEW: Move to the next character in turn order
    def advance_turn(self):
        """Move to the next character in the turn order"""
        self.gsm.current_turn_index += 1
        
        # Check if we've gone through all characters
        if self.gsm.current_turn_index >= len(self.gsm.turn_order):
            self.gsm.current_turn_index = 0
            self.gsm.add_to_log("--- New Round ---")

    # NEW: Get the character whose turn it currently is
    def get_current_character(self) -> Optional[Character]:
        """Get the character object whose turn it currently is"""
        if not self.gsm.turn_order:
            return None
        
        character_id = self.gsm.turn_order[self.gsm.current_turn_index]
        return self.gsm.characters.get(character_id)

    def process_player_action(self, action_data: Dict[str, Any]) -> bool:
        """Process a player action and update game state"""
        action_type = action_data.get('type')
        
        if action_type == 'move':
            return self._handle_move_action(action_data)
        elif action_type == 'attack':
            return self._handle_attack_action(action_data)
        elif action_type == 'wait':
            self.gsm.add_to_log("Hero waits and observes the situation.")
            return True
        
        return False

    def _handle_move_action(self, action_data: Dict[str, Any]) -> bool:
        """Handle player movement"""
        character_id = action_data.get('character_id', 'player')
        new_position = tuple(action_data.get('position', [0, 0]))
        
        return self.gsm.move_character(character_id, new_position)

    def _handle_attack_action(self, action_data: Dict[str, Any]) -> bool:
        """Handle player attack"""
        attacker_id = action_data.get('attacker_id', 'player')
        target_id = action_data.get('target_id')
        
        if not target_id:
            return False
        
        return self.execute_attack(attacker_id, target_id)

    def execute_attack(self, attacker_id: str, target_id: str) -> bool:
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
        attack_modifier = 3  # Simple attack modifier
        total_attack = attack_roll + attack_modifier
        
        self.gsm.add_to_log(f"{attacker.name} attacks {target.name}: rolls {attack_roll} + {attack_modifier} = {total_attack} vs AC {target.ac}")
        
        if total_attack >= target.ac:
            # Hit! Roll damage
            damage = random.randint(1, 8) + 2  # 1d8+2 damage
            self.gsm.apply_damage(target_id, damage)
            return True
        else:
            self.gsm.add_to_log(f"{attacker.name}'s attack misses {target.name}!")
            return True

    def process_ai_actions(self, ai_actions: List[Dict[str, Any]]) -> List[str]:
        """Process a list of AI actions and return results"""
        results = []
        
        for action in ai_actions:
            function_name = action.get('function')
            args = action.get('args', {})
            
            if function_name == 'narrate':
                text = args.get('text', '')
                self.gsm.add_to_log(f"[DM] {text}")
                results.append(f"DM: {text}")
            
            elif function_name == 'move_character':
                character_id = args.get('character_id')
                new_position = tuple(args.get('new_position', [0, 0]))
                
                if self.gsm.move_character(character_id, new_position):
                    results.append(f"Moved {character_id} to {new_position}")
                else:
                    results.append(f"Failed to move {character_id}")
            
            elif function_name == 'attack_character':
                attacker_id = args.get('attacker_id')
                target_id = args.get('target_id')
                
                if self.execute_attack(attacker_id, target_id):
                    results.append(f"{attacker_id} attacks {target_id}")
                else:
                    results.append(f"Attack failed: {attacker_id} -> {target_id}")
        
        return results

    def is_combat_over(self) -> bool:
        """Check if combat should end"""
        monsters = [char for char in self.gsm.characters.values() if char.type == "monster" and char.hp > 0]
        players = [char for char in self.gsm.characters.values() if char.type == "player" and char.hp > 0]
        
        return len(monsters) == 0 or len(players) == 0