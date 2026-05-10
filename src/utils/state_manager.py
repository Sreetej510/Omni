"""State manager for JSON-based agent state persistence."""
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime


class StateManager:
    """
    Save and load agent state to/from JSON files.
    Persists message history, research data, and session metadata.
    """
    
    def __init__(self, storage_path: str = "research/sessions"):
        """
        Initialize state manager.
        
        Args:
            storage_path: Directory path for storing session files
        """
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def _get_filepath(self, session_id: str) -> str:
        """Get file path for a session."""
        return os.path.join(self.storage_path, f"research_session_{session_id}.json")
    
    def save_state(
        self,
        session_id: str,
        message_history: List[Dict[str, str]],
        research_data: Dict[str, Any],
        status: str = "active",
        is_summarized: bool = False,
        total_tokens_used: int = 0,
        **kwargs
    ):
        """
        Save complete agent state to JSON file.
        
        Args:
            session_id: Unique session identifier
            message_history: Agent's message history
            research_data: Research findings and metadata
            status: Session status (active, completed, summarized)
            is_summarized: Whether history has been summarized
            total_tokens_used: Total tokens consumed
            **kwargs: Additional data to save
        """
        state = {
            "session_id": session_id,
            "topic": research_data.get("topic", ""),
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "agent_state": {
                "name": "main_agent",
                "message_history": message_history,
                "is_summarized": is_summarized,
                "total_tokens_used": total_tokens_used
            },
            "research_data": research_data,
            "status": status
        }
        
        # Add any additional kwargs
        if kwargs:
            state["additional_data"] = kwargs
        
        filepath = self._get_filepath(session_id)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load agent state from JSON file.
        
        Args:
            session_id: Session identifier to load
            
        Returns:
            State dictionary or None if not found
        """
        filepath = self._get_filepath(session_id)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def delete_state(self, session_id: str) -> bool:
        """
        Delete a session state file.
        
        Args:
            session_id: Session identifier to delete
            
        Returns:
            True if successful
        """
        filepath = self._get_filepath(session_id)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        """
        List all saved session IDs.
        
        Returns:
            List of session identifiers
        """
        sessions = []
        if os.path.exists(self.storage_path):
            for file in os.listdir(self.storage_path):
                if file.startswith("research_session_") and file.endswith(".json"):
                    session_id = file.replace("research_session_", "").replace(".json", "")
                    sessions.append(session_id)
        return sessions
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get basic information about a session without loading full state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session info dictionary or None
        """
        state = self.load_state(session_id)
        if state:
            return {
                "session_id": state.get("session_id"),
                "topic": state.get("topic"),
                "status": state.get("status"),
                "created_at": state.get("created_at"),
                "last_updated": state.get("last_updated"),
                "is_summarized": state.get("agent_state", {}).get("is_summarized", False)
            }
        return None
    
    def list_all_sessions(self) -> List[Dict[str, Any]]:
        """
        List information about all sessions.
        
        Returns:
            List of session info dictionaries
        """
        sessions = []
        for session_id in self.list_sessions():
            info = self.get_session_info(session_id)
            if info:
                sessions.append(info)
        return sessions
    
    def update_status(self, session_id: str, status: str) -> bool:
        """
        Update session status.
        
        Args:
            session_id: Session identifier
            status: New status
            
        Returns:
            True if successful
        """
        state = self.load_state(session_id)
        if state:
            state["status"] = status
            state["last_updated"] = datetime.now().isoformat()
            
            filepath = self._get_filepath(session_id)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            return True
        return False
    
    def update_research_data(self, session_id: str, research_data: Dict[str, Any]) -> bool:
        """
        Update research data for a session.
        
        Args:
            session_id: Session identifier
            research_data: New research data
            
        Returns:
            True if successful
        """
        state = self.load_state(session_id)
        if state:
            state["research_data"].update(research_data)
            state["last_updated"] = datetime.now().isoformat()
            
            filepath = self._get_filepath(session_id)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            return True
        return False
