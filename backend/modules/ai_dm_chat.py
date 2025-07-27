from typing import Dict, Any, List
from core.module_manager import GameModule
from modules.Gemini_DM import Gemini_DM
from datetime import datetime

class AIDMChatModule(GameModule):
    """Enhanced AI DM with better chat and narrative capabilities"""
    
    def __init__(self, game_state_manager):
        super().__init__(game_state_manager)
        self.dm = Gemini_DM()
        self.conversation_history = []
        self.dm_initialized = False
    
    def can_handle(self, action_data: Dict[str, Any]) -> bool:
        return action_data.get('type') in ['chat_with_dm', 'dm_narrate', 'dm_response']
    
    def process_action(self, action_data: Dict[str, Any]) -> bool:
        action_type = action_data.get('type')
        
        if action_type == 'chat_with_dm':
            message = action_data.get('message', '')
            return self._handle_player_chat(message)
        elif action_type == 'dm_narrate':
            return self._handle_dm_narration(action_data)
        elif action_type == 'dm_response':
            return self._handle_dm_response(action_data)
        
        return False
    
    def _handle_player_chat(self, message: str) -> bool:
        """Handle player message to DM"""
        if not self.dm_initialized:
            self.dm.initialize_session(self.gsm.serialize_state())
            self.dm_initialized = True
        
        # Add to conversation history
        self.conversation_history.append({
            "speaker": "player",
            "message": message,
            "timestamp": self._get_timestamp()
        })
        
        # Get AI response
        try:
            ai_actions = self.dm.get_npc_actions(
                self.gsm.serialize_state(), 
                f"Player says: '{message}'"
            )
            
            # Process AI response
            for action in ai_actions:
                if action.get('function') == 'narrate':
                    dm_response = action.get('args', {}).get('text', '')
                    self.conversation_history.append({
                        "speaker": "dm",
                        "message": dm_response,
                        "timestamp": self._get_timestamp()
                    })
                    self.gsm.add_to_log(f"[DM] {dm_response}")
            
            return True
            
        except Exception as e:
            # self.logger.error(f"Error getting DM response: {e}")
            print(f"Error getting DM response: {e}") # Assuming no logger is configured
            fallback_response = "The DM pauses thoughtfully, considering the situation..."
            self.conversation_history.append({
                "speaker": "dm",
                "message": fallback_response,
                "timestamp": self._get_timestamp()
            })
            self.gsm.add_to_log(f"[DM] {fallback_response}")
            return True

    def _handle_dm_narration(self, action_data: Dict[str, Any]) -> bool:
        """Handle DM-initiated narration"""
        context = action_data.get('context', 'general')
        
        if not self.dm_initialized:
            self.dm.initialize_session(self.gsm.serialize_state())
            self.dm_initialized = True
        
        try:
            # Create context-specific prompts
            if context == 'combat_start':
                prompt = "Combat is about to begin. Describe the tense atmosphere and what the characters see as they prepare for battle."
            elif context == 'combat_end':
                prompt = "Combat has ended. Describe the aftermath and current state of the area."
            elif context == 'character_death':
                character_name = action_data.get('character_name', 'someone')
                prompt = f"{character_name} has fallen in combat. Provide dramatic narration of this moment."
            elif context == 'exploration':
                prompt = "The characters are exploring. Describe what they might notice in their environment."
            else:
                prompt = "Provide general narrative description of the current situation."
            
            ai_actions = self.dm.get_npc_actions(self.gsm.serialize_state(), prompt)
            
            for action in ai_actions:
                if action.get('function') == 'narrate':
                    narration = action.get('args', {}).get('text', '')
                    self.conversation_history.append({
                        "speaker": "dm",
                        "message": narration,
                        "timestamp": self._get_timestamp(),
                        "type": "narration"
                    })
                    self.gsm.add_to_log(f"[DM] {narration}")
            
            return True
            
        except Exception as e:
            # self.logger.error(f"Error getting DM narration: {e}")
            print(f"Error getting DM narration: {e}") # Assuming no logger
            return False
    
    def _handle_dm_response(self, action_data: Dict[str, Any]) -> bool:
        """Handle DM response to game events"""
        event_type = action_data.get('event_type')
        event_data = action_data.get('event_data', {})
        
        if not self.dm_initialized:
            self.dm.initialize_session(self.gsm.serialize_state())  
            self.dm_initialized = True
        
        # Create event-specific prompts
        prompt = self._create_event_prompt(event_type, event_data)
        
        try:
            ai_actions = self.dm.get_npc_actions(self.gsm.serialize_state(), prompt)
            
            for action in ai_actions:
                if action.get('function') == 'narrate':
                    response = action.get('args', {}).get('text', '')
                    self.conversation_history.append({
                        "speaker": "dm",
                        "message": response,
                        "timestamp": self._get_timestamp(),
                        "event_type": event_type
                    })
                    self.gsm.add_to_log(f"[DM] {response}")
            
            return True
            
        except Exception as e:
            # self.logger.error(f"Error getting DM event response: {e}")
            print(f"Error getting DM event response: {e}") # Assuming no logger
            return False
    
    def _create_event_prompt(self, event_type: str, event_data: Dict[str, Any]) -> str:
        """Create appropriate prompts for different game events"""
        prompts = {
            'attack_hit': f"{event_data.get('attacker', 'Someone')} successfully hits {event_data.get('target', 'their target')} for {event_data.get('damage', 0)} damage. Describe this attack dramatically.",
            'attack_miss': f"{event_data.get('attacker', 'Someone')} misses their attack against {event_data.get('target', 'their target')}. Describe how the attack fails.",
            'spell_cast': f"{event_data.get('caster', 'Someone')} casts {event_data.get('spell', 'a spell')}. Describe the magical effects and atmosphere.",
            'character_defeated': f"{event_data.get('character', 'A character')} has been defeated. Provide dramatic description of their fall.",
            'critical_hit': f"{event_data.get('attacker', 'Someone')} scores a critical hit against {event_data.get('target', 'their target')}! Describe this devastating blow.",
            'healing': f"{event_data.get('target', 'Someone')} is healed for {event_data.get('amount', 0)} HP. Describe the restorative effects.",
            'item_used': f"{event_data.get('character', 'Someone')} uses {event_data.get('item', 'an item')}. Describe what happens.",
            'environmental': f"Something happens in the environment: {event_data.get('description', 'unknown event')}. Provide atmospheric description."
        }
        
        return prompts.get(event_type, f"Something interesting happens: {event_data}. Please provide narrative description.")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for conversation history"""
        return datetime.now().strftime("%H:%M:%S")
    
    def get_available_actions(self, character_id: str) -> List[Dict[str, Any]]:
        return [{
            "type": "chat_with_dm",
            "name": "Talk to DM",
            "description": "Ask the Dungeon Master a question or make a comment",
            "requires_input": "text"
        }]
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history for display"""
        return self.conversation_history.copy()
    
    def trigger_dm_narration(self, context: str, **kwargs):
        """Trigger DM narration from other modules"""
        action_data = {
            "type": "dm_narrate",
            "context": context,
            **kwargs
        }
        self.process_action(action_data)
    
    def trigger_dm_event_response(self, event_type: str, event_data: Dict[str, Any]):
        """Trigger DM response to game events"""
        action_data = {
            "type": "dm_response", 
            "event_type": event_type,
            "event_data": event_data
        }
        self.process_action(action_data)