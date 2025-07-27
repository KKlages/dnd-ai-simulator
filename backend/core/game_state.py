import json
import os
from typing import Dict, List, Tuple, Optional, Any
from utils.DnDAPIClient import DnDAPIClient
from core.character import Character

class GameStateManager:
    def __init__(self, api_client: Optional[DnDAPIClient] = None):
        self.characters: Dict[str, Character] = {}
        self.map_data: Dict[str, Any] = {}
        self.combat_active = False
        self.game_log: List[str] = []
        # Turn-based combat attributes
        self.turn_order: List[str] = []
        self.current_turn_index: int = 0
        
        # API client for character data
        self.api_client = api_client or DnDAPIClient()

    def load_state_from_file(self, filepath: str = "gamestate.json"):
        """Load game state from file"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                self._deserialize_state(data)

    def save_state_to_file(self, filepath: str = "gamestate.json"):
        """Save current game state to file"""
        state_data = self.serialize_state()
        with open(filepath, 'w') as f:
            json.dump(state_data, f, indent=2)

    def load_map(self, map_path: str):
        """Load map data from JSON file"""
        with open(map_path, 'r') as f:
            self.map_data = json.load(f)
        
        # Initialize characters from map starting positions
        if "starting_positions" in self.map_data:
            for char_id, position in self.map_data["starting_positions"].items():
                if char_id == "player":
                    self.add_character(
                        char_id, "Hero", "player", tuple(position),
                        class_index="fighter", race_index="human", level=1
                    )
                else:
                    # Initialize monsters with API data
                    monster_type = char_id.split('_')[0] if '_' in char_id else char_id
                    char_name = char_id.replace("_", " ").title()
                    self.add_character(
                        char_id, char_name, "monster", tuple(position),
                        monster_index=monster_type
                    )

    def add_character(self, char_id: str, name: str, char_type: str, position: Tuple[int, int], **kwargs):
        """Add a character to the game state with API-driven stats"""
        self.characters[char_id] = Character(
            char_id, name, char_type, position, 
            api_client=self.api_client, **kwargs
        )

    def get_character_by_id(self, char_id: str) -> Optional[Character]:
        """Get character by ID"""
        return self.characters.get(char_id)

    def get_map_data(self) -> Dict[str, Any]:
        """Get current map data"""
        return self.map_data

    def add_to_log(self, message: str):
        """Add message to game log"""
        self.game_log.append(message)
        print(f"[GAME LOG] {message}")

    def serialize_state(self) -> Dict[str, Any]:
        """Serialize current game state for saving/transmission"""
        return {
            "characters": {char_id: char.to_dict() for char_id, char in self.characters.items()},
            "map_data": self.map_data,
            "turn_order": self.turn_order,
            "current_turn_index": self.current_turn_index,
            "combat_active": self.combat_active,
            "game_log": self.game_log[-50:]  # Keep last 50 log entries
        }

    def get_characters_in_range(self, position: Tuple[int, int], range_feet: int = 5) -> List[Character]:
        """Get all characters within range of a position"""
        characters_in_range = []
        for character in self.characters.values():
            # Simple distance calculation (assuming 5ft per grid square)
            distance = abs(character.position[0] - position[0]) + abs(character.position[1] - position[1])
            if distance <= range_feet // 5:  # Convert feet to grid squares
                characters_in_range.append(character)
        return characters_in_range