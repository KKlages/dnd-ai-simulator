#!/usr/bin/env python3
import os
import sys
import logging
from GameStateManager import GameStateManager
from GameEngine import GameEngine
from Gemini_DM import Gemini_DM
from DnDAPIClient import DnDAPIClient

# Set up logging
logging.basicConfig(level=logging.INFO)

def print_game_state(gsm: GameStateManager):
    """Print current game state to console with enhanced API-driven info"""
    print("\n" + "="*60)
    print("CURRENT GAME STATE")
    print("="*60)
    
    map_data = gsm.get_map_data()
    print(f"Location: {map_data.get('name', 'Unknown')}")
    print(f"Description: {map_data.get('description', '')}")
    print(f"Map Size: {map_data.get('width')}x{map_data.get('height')}")
    
    # Show combat status and current turn
    if gsm.combat_active:
        current_char = None
        if gsm.turn_order and gsm.current_turn_index < len(gsm.turn_order):
            current_char_id = gsm.turn_order[gsm.current_turn_index]
            current_char = gsm.characters.get(current_char_id)
        
        print(f"Combat Status: ACTIVE")
        if current_char:
            print(f"Current Turn: {current_char.name}")
    else:
        print(f"Combat Status: INACTIVE")
    
    print("\nCharacters:")
    for char_id, character in gsm.characters.items():
        status = "💀" if character.hp <= 0 else "💚"
        initiative_info = f" (Init: {character.initiative})" if gsm.combat_active else ""
        
        # NEW: Show enhanced character info with ability scores
        ability_info = ""
        if hasattr(character, 'strength'):
            ability_info = f" [STR:{character.strength} DEX:{character.dexterity} CON:{character.constitution}]"
        
        attack_bonus = getattr(character, 'attack_bonus', 'N/A')
        print(f"  {status} {character.name} ({character.type}): Position {character.position}, HP {character.hp}/{character.max_hp}, AC {character.ac}, ATK +{attack_bonus}{ability_info}{initiative_info}")
        
        # Show monster type info if available
        if hasattr(character, 'monster_stats'):
            print(f"      Type: {character.monster_stats.type}, Size: {character.monster_stats.size}, CR: {character.monster_stats.challenge_rating}")
    
    # Simple ASCII map
    print(f"\nMap ({map_data.get('width')}x{map_data.get('height')}):")
    width = map_data.get('width', 10)
    height = map_data.get('height', 10)
    
    for y in range(height):
        row = []
        for x in range(width):
            cell = "."
            for char in gsm.characters.values():
                if char.position == (x, y):
                    if char.type == "player":
                        cell = "P" if char.hp > 0 else "X"
                    elif char.type == "monster":
                        cell = "M" if char.hp > 0 else "x"
                    break
            row.append(cell)
        print("  " + " ".join(row))
    print("\n" + "="*60)

def main():
   print("🎲 D&D AI Simulator - Enhanced with API Integration")
   print("Initializing game...")
   
   # NEW: Initialize API client first
   print("🌐 Connecting to D&D 5e SRD API...")
   api_client = DnDAPIClient()
   
   # Test API connection
   try:
       monsters = api_client.get_all_monsters()
       print(f"✅ API connected successfully! Found {len(monsters)} monsters in database.")
   except Exception as e:
       print(f"⚠️  API connection failed: {e}")
       print("⚠️  Falling back to hardcoded values...")
       api_client = None
   
   # Initialize game components with API client
   gsm = GameStateManager(api_client=api_client)
   engine = GameEngine(gsm)
   dm = Gemini_DM()
   
   # Load test map
   map_path = os.path.join("../data/maps/test_map.json")
   if not os.path.exists(map_path):
       print(f"❌ Map file not found: {map_path}")
       print("Please ensure you are running this script from the 'backend' directory.")
       sys.exit(1)
   
   gsm.load_map(map_path)

   # Initialize the DM session ONCE with the starting state
   dm.initialize_session(gsm.serialize_state())
   
   gsm.add_to_log("Adventure begins!")
   
   print("✅ Game initialized successfully!")
   
   # Show available monsters if API is connected
   if api_client:
       print("\n🔍 Available monsters in API:")
       monsters = api_client.get_all_monsters()[:10]  # Show first 10
       for monster in monsters:
           print(f"  - {monster['name']} (index: {monster['index']})")
       if len(api_client.get_all_monsters()) > 10:
           print(f"  ... and {len(api_client.get_all_monsters()) - 10} more!")
   
   # Main game loop with turn-based combat
   while True:
       # Check if combat is over
       if engine.is_combat_over():
           print_game_state(gsm)
           monsters_alive = [c for c in gsm.characters.values() if c.type == "monster" and c.hp > 0]
           if len(monsters_alive) == 0:
               print("\n🎉 Victory! All monsters defeated!")
           else:
               print("\n💀 Defeat! The hero has fallen!")
           break
       
       # Handle non-combat state
       if not gsm.combat_active:
           print_game_state(gsm)
           
           # Get player input with enhanced options
           print("\nWhat would you like to do?")
           print("1. Move (format: move x y)")
           print("2. Attack (format: attack monster_id)")
           print("3. Wait")
           print("4. Show character details")
           print("5. Show available monsters (if API connected)")
           print("6. Quit")
           
           user_input = input("\nEnter your action: ").strip().lower()
           
           if user_input == "quit" or user_input == "6":
               print("Thanks for playing!")
               break
           
           # NEW: Enhanced command handling
           elif user_input == "4":
               print("\n📊 Character Details:")
               for char_id, char in gsm.characters.items():
                   print(f"\n{char.name} ({char.type}):")
                   if hasattr(char, 'class_stats') and hasattr(char, 'race_stats'):
                       print(f"  Class: {char.class_stats.name} (Level {char.level})")
                       print(f"  Race: {char.race_stats.name}")
                   elif hasattr(char, 'monster_stats'):
                       print(f"  Type: {char.monster_stats.type}")
                       print(f"  Challenge Rating: {char.monster_stats.challenge_rating}")
                   print(f"  Abilities: STR {char.strength}, DEX {char.dexterity}, CON {char.constitution}")
                   print(f"  INT {char.intelligence}, WIS {char.wisdom}, CHA {char.charisma}")
               continue
           
           elif user_input == "5" and api_client:
               print("\n🐉 Available Monsters:")
               monsters = api_client.get_all_monsters()
               for i, monster in enumerate(monsters[:20]):  # Show first 20
                   print(f"  {i+1:2d}. {monster['name']} (index: {monster['index']})")
               if len(monsters) > 20:
                   print(f"  ... and {len(monsters) - 20} more!")
               continue
           
           # Parse player action
           player_action_data = None
           if user_input.startswith("move"):
               parts = user_input.split()
               if len(parts) >= 3:
                   try:
                       x, y = int(parts[1]), int(parts[2])
                       player_action_data = {
                           "type": "move",
                           "character_id": "player",
                           "position": [x, y]
                       }
                   except ValueError:
                       print("❌ Invalid move format. Use: move x y")
                       continue
           
           elif user_input.startswith("attack"):
               parts = user_input.split()
               if len(parts) >= 2:
                   target_id = parts[1]
                   player_action_data = {
                       "type": "attack",
                       "attacker_id": "player",
                       "target_id": target_id
                   }
           
           elif user_input == "wait" or user_input == "3":
               player_action_data = {"type": "wait"}
           
           else:
               print("❌ Invalid action. Please try again.")
               continue
           
           # Process player action
           if player_action_data:
               print(f"\n⚡ Processing action: {user_input}")
               
               if engine.process_player_action(player_action_data):
                   print("✅ Player action completed")
                   
                   # Start combat if the action was an attack
                   if player_action_data.get('type') == 'attack':
                       engine.start_combat()
                       
               else:
                   print("❌ Player action failed")
                   continue
       
       # Handle combat state
       else:
           current_character = engine.get_current_character()
           
           # Skip dead characters
           if current_character and current_character.hp <= 0:
               gsm.add_to_log(f"{current_character.name} is unable to act (defeated)")
               engine.advance_turn()
               continue
           
           # Player's turn
           if current_character and current_character.type == 'player':
               print_game_state(gsm)
               print(f"\n⚔️ --- Turn: {current_character.name} ---")
               print("What would you like to do?")
               print("1. Move (format: move x y)")
               print("2. Attack (format: attack monster_id)")
               print("3. Wait")
               
               user_input = input("\nEnter your action: ").strip().lower()
               
               # Parse player action (same as non-combat)
               if player_action_data:
                   if engine.process_player_action(player_action_data):
                       engine.advance_turn()
                   else:
                       print("❌ Player action failed")
                       continue
           
           # AI's turn
           elif current_character and current_character.type == 'monster':
               print_game_state(gsm)
               print(f"\n🧌 --- Turn: {current_character.name} ---")
               
               # NEW: Show monster's capabilities if available
               if hasattr(current_character, 'monster_stats'):
                   actions = current_character.monster_stats.actions
                   if actions:
                       print(f"Available actions: {', '.join([action['name'] for action in actions[:3]])}")
               
               # Get AI response
               print("🤖 AI Dungeon Master is thinking...")
               game_state = gsm.serialize_state()
               ai_actions = dm.get_npc_actions(game_state, f"It's {current_character.name}'s turn")
               
               # Process AI actions
               if ai_actions:
                   print("🎭 DM Response:")
                   results = engine.process_ai_actions(ai_actions)
                   for result in results:
                       if result.startswith("DM: "):
                           print(f"  {result}")
               
               # Always advance turn after AI acts
               engine.advance_turn()

if __name__ == "__main__":
   main()