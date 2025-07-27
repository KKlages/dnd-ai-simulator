#!/usr/bin/env python3
import os
import sys
import json
import logging
from typing import List, Dict, Any
from core.game_state import GameStateManager
from core.module_manager import ModuleManager
from modules.movement import MovementModule
from modules.combat import CombatModule
from modules.inventory import InventoryModule
from modules.spells import SpellsModule
from modules.ai_dm_chat import AIDMChatModule
from modules.Gemini_DM import Gemini_DM
from utils.DnDAPIClient import DnDAPIClient

logging.basicConfig(level=logging.INFO)

class GameEngine:
    """Enhanced game engine with all modules"""
    
    def __init__(self, game_state_manager: GameStateManager):
        self.gsm = game_state_manager
        self.module_manager = ModuleManager(game_state_manager)
        
        # Store references to specific modules
        self.combat_module = None
        self.movement_module = None
        self.ai_dm_chat = None
        
        # Register all modules
        self._register_modules()
    
    def _register_modules(self):
        """Register all game modules"""
        # Core modules
        self.movement_module = MovementModule(self.gsm)
        self.module_manager.register_module(self.movement_module)
        
        self.combat_module = CombatModule(self.gsm)
        self.module_manager.register_module(self.combat_module)
        
        # Feature modules
        self.module_manager.register_module(InventoryModule(self.gsm))
        self.module_manager.register_module(SpellsModule(self.gsm))
        
        # AI DM
        self.ai_dm_chat = AIDMChatModule(self.gsm)
        self.module_manager.register_module(self.ai_dm_chat)
    
    def process_player_action(self, action_data):
        """Process player action through module system"""
        return self.module_manager.process_action(action_data)
    
    def start_combat(self):
        """Start combat and trigger DM narration"""
        success = self.combat_module._start_combat()
        if success and self.ai_dm_chat:
            self.ai_dm_chat.trigger_dm_narration("combat_start")
        return success
    
    def advance_turn(self):
        """Advance turn and reset movement"""
        if self.combat_module:
            current_char = self.combat_module.get_current_character()
            if current_char and self.movement_module:
                self.movement_module.reset_turn_movement(current_char.id)
            
            self.combat_module.advance_turn()
    
    def get_current_character(self):
        """Get current character"""
        return self.combat_module.get_current_character() if self.combat_module else None
    
    def is_combat_over(self):
        """Check if combat is over"""
        return self.combat_module.is_combat_over() if self.combat_module else False
    
    def get_all_available_actions(self, character_id: str) -> List[Dict[str, Any]]:
        """Get all available actions for a character"""
        return self.module_manager.get_available_actions(character_id)

def initialize_game():
    """Initialize the enhanced game with all modules"""
    print("🎲 D&D AI Simulator - Enhanced Modular Architecture")
    print("🆕 New Features: Inventory, Spells, Enhanced Movement, AI DM Chat")
    print("Initializing game...")
    
    # Initialize API client
    print("🌐 Connecting to D&D 5e SRD API...")
    api_client = DnDAPIClient()
    
    try:
        monsters = api_client.get_all_monsters()
        print(f"✅ API connected successfully! Found {len(monsters)} monsters in database.")
    except Exception as e:
        print(f"⚠️  API connection failed: {e}")
        print("⚠️  Falling back to hardcoded values...")
        api_client = None
    
    # Initialize game components
    gsm = GameStateManager(api_client=api_client)
    engine = GameEngine(gsm)
    
    # Load test map - try multiple paths
    map_paths = [
        "data/maps/test_map.json",
        "../data/maps/test_map.json",
        "test_map.json",
        "../test_map.json"
    ]
    
    map_loaded = False
    for map_path in map_paths:
        if os.path.exists(map_path):
            gsm.load_map(map_path)
            print(f"✅ Map loaded from: {map_path}")
            map_loaded = True
            break
    
    if not map_loaded:
        # Create default map
        print("🔧 Creating default test map...")
        default_map = {
            "name": "Enhanced Test Chamber",
            "description": "A test chamber with inventory, spells, and enhanced movement",
            "width": 6,
            "height": 6,
            "starting_positions": {
                "player": [1, 1],
                "goblin_1": [4, 4],
                "orc_1": [5, 2]
            },
            "terrain": {
                "trees": [[2, 2], [3, 1]],
                "rocks": [[1, 4]]
            }
        }
        
        os.makedirs("data/maps", exist_ok=True)
        with open("data/maps/test_map.json", 'w') as f:
            json.dump(default_map, f, indent=2)
        
        gsm.load_map("data/maps/test_map.json")
        print("✅ Default map created and loaded!")
    
    gsm.add_to_log("Enhanced adventure begins!")
    print("✅ Game initialized successfully!")
    
    return gsm, engine

def test_new_features(gsm, engine):
    """Test all the new features"""
    print("\n🧪 Testing Enhanced Features...")
    
    player = gsm.get_character_by_id("player")
    if not player:
        print("❌ No player found")
        return
    
    # Test inventory
    print("\n📦 Testing Inventory System...")
    inventory_actions = [action for action in engine.get_all_available_actions("player") if "equip" in action.get("name", "").lower()]
    print(f"Available equipment actions: {len(inventory_actions)}")
    
    # Test spells
    print("\n✨ Testing Spell System...")
    spell_actions = [action for action in engine.get_all_available_actions("player") if "cast" in action.get("name", "").lower()]
    print(f"Available spells: {len(spell_actions)}")
    
    # Test enhanced movement
    print("\n🏃 Testing Enhanced Movement...")
    movement_info = engine.movement_module.get_movement_info("player")
    print(f"Player movement: {movement_info}")
    
    # Test movement
    move_action = {"type": "move", "character_id": "player", "position": [2, 1]}
    success = engine.process_player_action(move_action)
    print(f"Movement test: {'✅' if success else '❌'}")
    
    # Test movement limit
    move_action2 = {"type": "move", "character_id": "player", "position": [5, 5]}  # Too far
    success2 = engine.process_player_action(move_action2)
    print(f"Movement limit test: {'✅' if not success2 else '❌'}")  # Should fail
    
    # Test AI DM Chat
    print("\n💬 Testing AI DM Chat...")
    chat_action = {"type": "chat_with_dm", "message": "What do I see around me?"}
    success = engine.process_player_action(chat_action)
    print(f"DM Chat test: {'✅' if success else '❌'}")
    
    print("\n✅ All enhanced features tested!")

if __name__ == "__main__":
    # Initialize enhanced game
    gsm, engine = initialize_game()
    
    # Test new features
    test_new_features(gsm, engine)
    
    # Show available actions
    print(f"\n🎮 All available actions for player:")
    actions = engine.get_all_available_actions("player")
    for i, action in enumerate(actions, 1):
        print(f"  {i:2d}. {action.get('name', 'Unknown')} - {action.get('description', '')}")
    
    print(f"\n✅ Enhanced modular system complete!")
    print(f"🚀 Ready for GUI development with {len(actions)} available actions!")