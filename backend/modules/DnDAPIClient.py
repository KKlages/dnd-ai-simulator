import requests
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

@dataclass
class MonsterStats:
    """Data class for monster statistics from D&D API"""
    name: str
    armor_class: int
    hit_points: int
    hit_dice: str
    speed: Dict[str, str]
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int
    challenge_rating: float
    proficiency_bonus: int
    actions: List[Dict[str, Any]]
    size: str
    type: str
    alignment: str

@dataclass
class ClassStats:
    """Data class for character class statistics from D&D API"""
    name: str
    hit_die: int
    primary_ability: List[str]
    saving_throw_proficiencies: List[str]
    proficiencies: List[Dict[str, Any]]

@dataclass
class RaceStats:
    """Data class for character race statistics from D&D API"""
    name: str
    ability_bonuses: List[Dict[str, Any]]
    size: str
    speed: int
    languages: List[Dict[str, Any]]
    traits: List[Dict[str, Any]]

class DnDAPIClient:
    """Client for interacting with the D&D 5e SRD API"""
    
    def __init__(self, base_url: str = "https://www.dnd5eapi.co/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DnD-Simulator/1.0'
        })
        
        # Cache for API responses to avoid repeated requests
        self._cache: Dict[str, Any] = {}
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make a request to the API with caching"""
        if endpoint in self._cache:
            return self._cache[endpoint]
        
        try:
            url = f"{self.base_url}{endpoint}"
            self.logger.info(f"Making API request to: {url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self._cache[endpoint] = data
            return data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed for {endpoint}: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON response for {endpoint}: {e}")
            return None
    
    def get_monster(self, monster_index: str) -> Optional[MonsterStats]:
        """Get monster data from the API"""
        data = self._make_request(f"/monsters/{monster_index}")
        if not data:
            return None
        
        try:
            return MonsterStats(
                name=data.get('name', ''),
                armor_class=data.get('armor_class', [{}])[0].get('value', 12),
                hit_points=data.get('hit_points', 10),
                hit_dice=data.get('hit_dice', '2d8'),
                speed=data.get('speed', {}),
                strength=data.get('strength', 10),
                dexterity=data.get('dexterity', 10),
                constitution=data.get('constitution', 10),
                intelligence=data.get('intelligence', 10),
                wisdom=data.get('wisdom', 10),
                charisma=data.get('charisma', 10),
                challenge_rating=data.get('challenge_rating', 0.125),
                proficiency_bonus=data.get('proficiency_bonus', 2),
                actions=data.get('actions', []),
                size=data.get('size', 'Medium'),
                type=data.get('type', 'humanoid'),
                alignment=data.get('alignment', 'neutral')
            )
        except (KeyError, TypeError) as e:
            self.logger.error(f"Failed to parse monster data for {monster_index}: {e}")
            return None
    
    def get_class(self, class_index: str) -> Optional[ClassStats]:
        """Get character class data from the API"""
        data = self._make_request(f"/classes/{class_index}")
        if not data:
            return None
        
        try:
            return ClassStats(
                name=data.get('name', ''),
                hit_die=data.get('hit_die', 8),
                primary_ability=[ability['name'] for ability in data.get('primary_ability', [])],
                saving_throw_proficiencies=[prof['name'] for prof in data.get('saving_throws', [])],
                proficiencies=data.get('proficiencies', [])
            )
        except (KeyError, TypeError) as e:
            self.logger.error(f"Failed to parse class data for {class_index}: {e}")
            return None
    
    def get_race(self, race_index: str) -> Optional[RaceStats]:
        """Get character race data from the API"""
        data = self._make_request(f"/races/{race_index}")
        if not data:
            return None
        
        try:
            return RaceStats(
                name=data.get('name', ''),
                ability_bonuses=data.get('ability_bonuses', []),
                size=data.get('size', 'Medium'),
                speed=data.get('speed', 30),
                languages=data.get('languages', []),
                traits=data.get('traits', [])
            )
        except (KeyError, TypeError) as e:
            self.logger.error(f"Failed to parse race data for {race_index}: {e}")
            return None
    
    def get_all_monsters(self) -> List[Dict[str, str]]:
        """Get list of all available monsters"""
        data = self._make_request("/monsters")
        if not data:
            return []
        
        return data.get('results', [])
    
    def get_all_classes(self) -> List[Dict[str, str]]:
        """Get list of all available classes"""
        data = self._make_request("/classes")
        if not data:
            return []
        
        return data.get('results', [])
    
    def get_all_races(self) -> List[Dict[str, str]]:
        """Get list of all available races"""
        data = self._make_request("/races")
        if not data:
            return []
        
        return data.get('results', [])
    
    def search_monsters(self, **filters) -> List[Dict[str, Any]]:
        """Search monsters with filters (challenge_rating, type, etc.)"""
        params = []
        for key, value in filters.items():
            params.append(f"{key}={value}")
        
        query_string = "&".join(params)
        endpoint = f"/monsters?{query_string}" if query_string else "/monsters"
        
        data = self._make_request(endpoint)
        if not data:
            return []
        
        return data.get('results', [])

    def calculate_ability_modifier(self, ability_score: int) -> int:
        """Calculate ability modifier from ability score"""
        return (ability_score - 10) // 2
    
    def calculate_proficiency_bonus(self, level: int) -> int:
        """Calculate proficiency bonus from character level"""
        return 2 + ((level - 1) // 4)