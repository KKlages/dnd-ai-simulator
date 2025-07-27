from typing import Dict, Any, List, Tuple
from core.module_manager import GameModule

class MovementModule(GameModule):
    """Handles character movement with turn-based restrictions"""
    
    def __init__(self, game_state_manager):
        super().__init__(game_state_manager)
        # Track movement used this turn for each character
        self.movement_used = {}
    
    def can_handle(self, action_data: Dict[str, Any]) -> bool:
        return action_data.get('type') in ['move', 'dash']
    
    def process_action(self, action_data: Dict[str, Any]) -> bool:
        action_type = action_data.get('type')
        character_id = action_data.get('character_id', 'player')
        
        if action_type == 'move':
            new_position = tuple(action_data.get('position', [0, 0]))
            return self._handle_movement(character_id, new_position)
        elif action_type == 'dash':
            return self._handle_dash(character_id)
        
        return False
    
    def _handle_movement(self, character_id: str, new_position: Tuple[int, int]) -> bool:
        """Handle character movement with speed restrictions"""
        character = self.gsm.get_character_by_id(character_id)
        if not character:
            return False
        
        # Calculate movement distance
        current_pos = character.position
        distance = abs(new_position[0] - current_pos[0]) + abs(new_position[1] - current_pos[1])
        distance_feet = distance * 5  # Each grid square = 5 feet
        
        # Get character speed (default 30 feet)
        speed = self._get_character_speed(character)
        
        # Check how much movement has been used this turn
        used_movement = self.movement_used.get(character_id, 0)
        remaining_movement = speed - used_movement
        
        if distance_feet > remaining_movement:
            self.gsm.add_to_log(f"{character.name} doesn't have enough movement! Needs {distance_feet} feet, has {remaining_movement} feet remaining.")
            return False
        
        # Validate movement path
        if not self._is_valid_move(character, new_position):
            return False
        
        # Execute movement
        character.position = new_position
        self.movement_used[character_id] = used_movement + distance_feet
        
        remaining = speed - self.movement_used[character_id]
        self.gsm.add_to_log(f"{character.name} moves from {current_pos} to {new_position} ({distance_feet} feet, {remaining} feet remaining)")
        
        return True
    
    def _handle_dash(self, character_id: str) -> bool:
        """Handle dash action (doubles movement for the turn)"""
        character = self.gsm.get_character_by_id(character_id)
        if not character:
            return False
        
        # Check if already dashed this turn
        if hasattr(character, 'dashed_this_turn'):
            self.gsm.add_to_log(f"{character.name} has already dashed this turn!")
            return False
        
        speed = self._get_character_speed(character)
        character.dashed_this_turn = True
        
        # Reset movement used to allow full movement again
        used_before_dash = self.movement_used.get(character_id, 0)
        self.movement_used[character_id] = max(0, used_before_dash - speed)
        
        self.gsm.add_to_log(f"{character.name} dashes! Movement doubled for this turn.")
        return True
    
    def _get_character_speed(self, character) -> int:
        """Get character's movement speed in feet"""
        # Check for race-based speed
        if hasattr(character, 'race_stats') and hasattr(character.race_stats, 'speed'):
            return character.race_stats.speed
        
        # Default human speed
        return 30
    
    def _is_valid_move(self, character, new_position: Tuple[int, int]) -> bool:
        """Validate movement destination"""
        # Basic bounds checking
        map_data = self.gsm.get_map_data()
        if not (0 <= new_position[0] < map_data.get("width", 10) and 
                0 <= new_position[1] < map_data.get("height", 10)):
            self.gsm.add_to_log(f"{character.name} cannot move outside the map bounds!")
            return False
        
        # Check if position is occupied
        for other_char in self.gsm.characters.values():
            if other_char.id != character.id and other_char.position == new_position:
                self.gsm.add_to_log(f"{character.name} cannot move to occupied position!")
                return False
        
        # Check terrain restrictions
        if self._is_position_blocked(new_position):
            self.gsm.add_to_log(f"{character.name} cannot move through that terrain!")
            return False
        
        return True
    
    def _is_position_blocked(self, position: Tuple[int, int]) -> bool:
        """Check if position is blocked by terrain"""
        map_data = self.gsm.get_map_data()
        terrain = map_data.get('terrain', {})
        
        # Check for blocking terrain
        for terrain_type, positions in terrain.items():
            if list(position) in positions:  # Convert tuple to list for comparison
                # Trees block movement
                if terrain_type == 'trees':
                    return True
        
        return False
    
    def reset_turn_movement(self, character_id: str):
        """Reset movement for a new turn"""
        self.movement_used[character_id] = 0
        character = self.gsm.get_character_by_id(character_id)
        if character and hasattr(character, 'dashed_this_turn'):
            delattr(character, 'dashed_this_turn')
    
    def get_available_actions(self, character_id: str) -> List[Dict[str, Any]]:
        character = self.gsm.get_character_by_id(character_id)
        if not character:
            return []
        
        actions = []
        
        # Always allow movement (the module will check if it's valid)
        speed = self._get_character_speed(character)
        used_movement = self.movement_used.get(character_id, 0)
        remaining = speed - used_movement
        
        actions.append({
            "type": "move",
            "name": f"Move ({remaining} feet remaining)",
            "description": f"Move to a new position. {remaining}/{speed} feet remaining.",
            "requires_target": "position"
        })
        
        # Dash action if not already used
        if not hasattr(character, 'dashed_this_turn') and remaining < speed:
            actions.append({
                "type": "dash",
                "name": "Dash",
                "description": "Double your movement speed for this turn"
            })
        
        return actions
    
    def get_movement_info(self, character_id: str) -> Dict[str, Any]:
        """Get movement information for display"""
        character = self.gsm.get_character_by_id(character_id)
        if not character:
            return {}
        
        speed = self._get_character_speed(character)
        used = self.movement_used.get(character_id, 0)
        
        return {
            "speed": speed,
            "used": used,
            "remaining": speed - used,
            "can_dash": not hasattr(character, 'dashed_this_turn')
        }