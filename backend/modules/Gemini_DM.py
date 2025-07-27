import google.generativeai as genai
import json
import os
from typing import Dict, List, Any

# No need to load dotenv here if it's done in main.py, but it's safe to keep.
from dotenv import load_dotenv
load_dotenv()

class Gemini_DM:
    def __init__(self):
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

        # Define the tools with the CORRECT, FULLY UPPERCASE schema
        self.tools = [
            {
                'function_declarations': [
                    {
                        'name': 'narrate',
                        'description': 'Provide narrative description of events, dialogue, or scene setting.',
                        'parameters': {
                            'type': 'OBJECT',
                            'properties': {
                                'text': {
                                    'type': 'STRING', # <-- FIX
                                    'description': 'The narrative text to present to the player.'
                                }
                            },
                            'required': ['text']
                        }
                    },
                    {
                        'name': 'move_character',
                        'description': 'Move an AI-controlled character to a new position on the map.',
                        'parameters': {
                            'type': 'OBJECT',
                            'properties': {
                                'character_id': {
                                    'type': 'STRING', # <-- FIX
                                    'description': 'The ID of the character to move (e.g., "goblin_1").'
                                },
                                'new_position': {
                                    'type': 'ARRAY',  # <-- FIX
                                    'items': {'type': 'INTEGER'}, # <-- FIX
                                    'description': 'New [x, y] coordinates for the character.'
                                }
                            },
                            'required': ['character_id', 'new_position']
                        }
                    },
                    {
                        'name': 'attack_character',
                        'description': 'Have one AI-controlled character attack another character (usually the player).',
                        'parameters': {
                            'type': 'OBJECT',
                            'properties': {
                                'attacker_id': {
                                    'type': 'STRING', # <-- FIX
                                    'description': 'ID of the attacking character (e.g., "goblin_1").'
                                },
                                'target_id': {
                                    'type': 'STRING', # <-- FIX
                                    'description': 'ID of the target character (usually "player").'
                                }
                            },
                            'required': ['attacker_id', 'target_id']
                        }
                    }
                ]
            }
        ]
        
        # Use a stable model name
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest', tools=self.tools)
        self.chat = None # Initialize chat as None

    def initialize_session(self, game_state: Dict[str, Any]):
        """Starts a new chat session with a detailed system prompt."""
        system_prompt = self._build_initial_prompt(game_state)
        self.chat = self.model.start_chat()
        # Send the initial system prompt to set the context for the entire session
        self.chat.send_message(system_prompt)
        print("?? Gemini DM session initialized.")


    def _build_initial_prompt(self, game_state: Dict[str, Any]) -> str:
        """Build the one-time, comprehensive system prompt for the AI DM."""
        map_data = game_state.get('map_data', {})
        characters = game_state.get('characters', {})
        
        prompt = f"""You are an expert D&D 5e Dungeon Master. Your goal is to create an engaging and fair experience.

Here is the initial state of the world:

SCENE:
Map: {map_data.get('name', 'Unknown')} - {map_data.get('description', '')}
Dimensions: {map_data.get('width')}x{map_data.get('height')} grid (each square = 5 feet)

CHARACTERS IN SCENE:"""
        
        for char_id, char_data in characters.items():
            prompt += f"""
- ID: {char_id}, Name: {char_data['name']} ({char_data['type']}), Position: {char_data['position']}, HP: {char_data['hp']}/{char_data['max_hp']}, AC: {char_data['ac']}"""
        
        prompt += """

YOUR TASK:
- You control all characters where 'type' is NOT 'player'.
- After the player acts, I will tell you what they did. You will then decide the actions for all the characters you control.
- Use your tools to execute actions: `narrate()` for descriptions, `move_character()` to move, and `attack_character()` to attack.
- Make intelligent, tactical decisions appropriate for the characters you control. Goblins are cunning but cowardly.
- You must always respond by using your available tools. Do not just output text.
- Let's begin. Awaiting the player's first action."""
        
        return prompt

    def get_npc_actions(self, game_state: Dict[str, Any], player_action_description: str) -> List[Dict[str, Any]]:
        """Gets the AI's response to the player's latest action."""
        if not self.chat:
            self.initialize_session(game_state)

        current_turn_prompt = f"""The player's action was: '{player_action_description}'.

The current character states are:
"""
        for char_id, char_data in game_state.get('characters', {}).items():
             current_turn_prompt += f"- ID: {char_id}, Pos: {char_data['position']}, HP: {char_data['hp']}\n"
        
        current_turn_prompt += "\nNow, determine and execute the actions for all non-player characters."

        try:
            response = self.chat.send_message(current_turn_prompt)
            return self._parse_response(response.candidates[0])
        except Exception as e:
            print(f"Error getting AI response: {e}")
            return [{"function": "narrate", "args": {"text": "The dungeon master pauses, momentarily confused by the cosmos..."}}]

    def _parse_response(self, candidate) -> List[Dict[str, Any]]:
        """Parse a Gemini response candidate and extract function calls."""
        actions = []
        if not hasattr(candidate, 'content') or not candidate.content.parts:
            return [{"function": "narrate", "args": {"text": "The DM considers the situation..."}}]
            
        for part in candidate.content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                actions.append({
                    "function": part.function_call.name,
                    "args": dict(part.function_call.args)
                })
        
        if not actions and hasattr(candidate.content.parts[0], 'text') and candidate.content.parts[0].text:
             actions.append({
                "function": "narrate",
                "args": {"text": candidate.content.parts[0].text}
            })

        return actions if actions else [{"function": "narrate", "args": {"text": "The DM quietly observes..."}}]