from typing import Dict, List, Tuple, Optional, Any
from utils.DnDAPIClient import DnDAPIClient

class Character:
    def __init__(self, char_id: str, name: str, char_type: str, position: Tuple[int, int], 
                 api_client: Optional[DnDAPIClient] = None, **kwargs):
        self.id = char_id
        self.name = name
        self.type = char_type  # "player", "npc", "monster"
        self.position = position
        self.initiative = 0
        self.conditions = []
        
        # API-driven character stats
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