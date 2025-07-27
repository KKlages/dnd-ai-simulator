import json
import os
from typing import Dict, List, Tuple, Optional, Any
from DnDAPIClient import DnDAPIClient, MonsterStats, ClassStats, RaceStats

class Character:
    def __init__(self, char_id: str, name: str, char_type: str, position: Tuple[int, int], 
                 api_client: Optional[DnDAPIClient] = None, **kwargs):
        self.id = char_id
        self.name = name
        self.type = char_type  # "player", "npc", "monster"
        self.position = position
        self.initiative = 0
        self.conditions = []
        
        # NEW: API-driven character stats
        self.api_client = api_client
        self._stats_cache = {}
        
        # Initialize with API data or defaults
        if char_type == "monster" and api_client:
            self._initialize_from_monster_api(kwargs.get('monster_index', 'goblin'))
        elif char_type == "player" and api_client:
            self._initialize_from_player_api(
                kwargs.get('class_index', 'fighter'),
                kwargs.get('race_index', 'human'),
                kwargs.get('level', 1)
            )
        else:
            # Fallback to hardcoded values
            self._initialize_defaults()
    
    def _initialize_from_monster_api(self, monster_index: str):
        """Initialize monster stats from D&D API"""
        monster_stats = self.api_client.get_monster(monster_index)
        if monster_stats:
            self.hp = monster_stats.hit_points
            self.max_hp = monster_stats.hit_points
            self.ac = monster_stats.armor_class
            self.monster_stats = monster_stats
            
            # Store ability scores
            self.strength = monster_stats.strength
            self.dexterity = monster_stats.dexterity
            self.constitution = monster_stats.constitution
            self.intelligence = monster_stats.intelligence
            self.wisdom = monster_stats.wisdom
            self.charisma = monster_stats.charisma
            
            # Calculate attack bonus from stats
            self.attack_bonus = self.api_client.calculate_ability_modifier(self.strength) + monster_stats.proficiency_bonus
        else:
            self._initialize_defaults()
    
    def _initialize_from_player_api(self, class_index: str, race_index: str, level: int):
        """Initialize player stats from D&D API"""
        class_stats = self.api_client.get_class(class_index)
        race_stats = self.api_client.get_race(race_index)
        
        if class_stats and race_stats:
            # Base ability scores (could be made configurable)
            base_stats = {
                'strength': 15, 'dexterity': 14, 'constitution': 13,
                'intelligence': 12, 'wisdom': 10, 'charisma': 8
            }
            
            # Apply racial bonuses
            for bonus in race_stats.ability_bonuses:
                ability_name = bonus['ability_score']['name'].lower()
                if ability_name in base_stats:
                    base_stats[ability_name] += bonus['bonus']
            
            # Set ability scores
            self.strength = base_stats['strength']
            self.dexterity = base_stats['dexterity']
            self.constitution = base_stats['constitution']
            self.intelligence = base_stats['intelligence']
            self.wisdom = base_stats['wisdom']
            self.charisma = base_stats['charisma']
            
            # Calculate HP from class hit die + con modifier
            con_modifier = self.api_client.calculate_ability_modifier(self.constitution)
            self.max_hp = class_stats.hit_die + con_modifier + ((level - 1) * (class_stats.hit_die // 2 + 1 + con_modifier))
            self.hp = self.max_hp
            
            # Base AC (could be enhanced with armor)
            dex_modifier = self.api_client.calculate_ability_modifier(self.dexterity)
            self.ac = 10 + dex_modifier  # Unarmored AC
            
            # Store class and race info
            self.class_stats = class_stats
            self.race_stats = race_stats
            self.level = level
            
            # Calculate attack bonus
            proficiency_bonus = self.api_client.calculate_proficiency_bonus(level)
            self.attack_bonus = self.api_client.calculate_ability_modifier(self.strength) + proficiency_bonus
        else:
            self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Fallback initialization with hardcoded values"""
        if self.type == "player":
            self.hp = 20
            self.max_hp = 20
            self.ac = 15
            self.attack_bonus = 5
        else:  # monster
            self.hp = 10
            self.max_hp = 10
            self.ac = 12
            self.attack_bonus = 3
        
        # Default ability scores
        self.strength = 13
        self.dexterity = 12
        self.constitution = 14
        self.intelligence = 10
        self.wisdom = 12
        self.charisma = 10

    def get_ability_modifier(self, ability_name: str) -> int:
        """Get ability modifier for a given ability"""
        ability_score = getattr(self, ability_name.lower(), 10)
        if self.api_client:
            return self.api_client.calculate_ability_modifier(ability_score)
        else:
            return (ability_score - 10) // 2

    def to_dict(self) -> Dict[str, Any]:
        base_dict = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "position": self.position,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "ac": self.ac,
            "conditions": self.conditions,
            "initiative": self.initiative,
            "attack_bonus": getattr(self, 'attack_bonus', 3)
        }
        
        # Add ability scores if available
        abilities = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
        for ability in abilities:
            if hasattr(self, ability):
                base_dict[ability] = getattr(self, ability)
        
        return base_dict

class GameStateManager:
    def __init__(self, api_client: Optional[DnDAPIClient] = None):
        self.characters: Dict[str, Character] = {}
        self.map_data: Dict[str, Any] = {}
        self.combat_active = False
        self.game_log: List[str] = []
        # Turn-based combat attributes
        self.turn_order: List[str] = []
        self.current_turn_index: int = 0
        
        # NEW: API client for character data
        self.api_client = api_client or DnDAPIClient()

    def load_state_from_file(self, filepath: str = "gamestate.json"):
        """Load game state from file"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                # Reconstruct state from saved data
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
                    # NEW: Initialize player with API data
                    self.add_character(
                        char_id, "Hero", "player", tuple(position),
                        class_index="fighter", race_index="human", level=1
                    )
                else:
                    # NEW: Initialize monsters with API data
                    # Extract monster type from character ID (e.g., "goblin_1" -> "goblin")
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

    def move_character(self, char_id: str, new_position: Tuple[int, int]) -> bool:
        """Move character to new position with validation"""
        character = self.get_character_by_id(char_id)
        if not character:
            return False
        
        # Basic bounds checking
        if (0 <= new_position[0] < self.map_data.get("width", 10) and 
            0 <= new_position[1] < self.map_data.get("height", 10)):
            
            # Check if position is occupied
            for other_char in self.characters.values():
                if other_char.id != char_id and other_char.position == new_position:
                    return False
            
            old_pos = character.position
            character.position = new_position
            self.add_to_log(f"{character.name} moves from {old_pos} to {new_position}")
            return True
        
        return False

    def apply_damage(self, char_id: str, damage: int) -> bool:
        """Apply damage to character"""
        character = self.get_character_by_id(char_id)
        if not character:
            return False
        
        character.hp = max(0, character.hp - damage)
        self.add_to_log(f"{character.name} takes {damage} damage (HP: {character.hp}/{character.max_hp})")
        
        if character.hp <= 0:
            self.add_to_log(f"{character.name} is defeated!")
        
        return True

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