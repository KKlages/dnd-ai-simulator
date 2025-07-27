from typing import Dict, List, Any, Optional
import logging

class GameModule:
    """Base class for all game modules"""
    
    def __init__(self, game_state_manager):
        self.gsm = game_state_manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def can_handle(self, action_data: Dict[str, Any]) -> bool:
        """Check if this module can handle the given action"""
        raise NotImplementedError
    
    def process_action(self, action_data: Dict[str, Any]) -> bool:
        """Process the action and return success status"""
        raise NotImplementedError
    
    def get_available_actions(self, character_id: str) -> List[Dict[str, Any]]:
        """Get list of actions this module can provide for a character"""
        return []

class ModuleManager:
    """Manages all game modules and routes actions to appropriate handlers"""
    
    def __init__(self, game_state_manager):
        self.gsm = game_state_manager
        self.modules: List[GameModule] = []
        self.logger = logging.getLogger(__name__)
    
    def register_module(self, module: GameModule):
        """Register a new game module"""
        self.modules.append(module)
        self.logger.info(f"Registered module: {module.__class__.__name__}")
    
    def process_action(self, action_data: Dict[str, Any]) -> bool:
        """Route action to appropriate module"""
        for module in self.modules:
            if module.can_handle(action_data):
                try:
                    success = module.process_action(action_data)
                    if success:
                        self.logger.info(f"Action processed by {module.__class__.__name__}")
                        return True
                except Exception as e:
                    self.logger.error(f"Error in {module.__class__.__name__}: {e}")
                    continue
        
        self.logger.warning(f"No module could handle action: {action_data}")
        return False
    
    def get_available_actions(self, character_id: str) -> List[Dict[str, Any]]:
        """Get all available actions for a character across all modules"""
        actions = []
        for module in self.modules:
            actions.extend(module.get_available_actions(character_id))
        return actions