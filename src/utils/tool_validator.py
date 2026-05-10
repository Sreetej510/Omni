"""Tool validator for dynamic tool access control."""
from typing import Tuple


class ToolValidator:
    """
    Validates tool calls and enforces dynamic tool access limits.
    
    Features:
    - Tracks web_search usage
    - Dynamically disables tools after limits reached
    - Provides clear error messages for disallowed tools
    """
    
    def __init__(self, web_search_limit: int):
        """
        Initialize tool validator.
        
        Args:
            web_search_limit: Maximum number of web_search calls allowed
        """
        self.web_search_limit = web_search_limit
        self.web_search_count = 0
        self.web_search_allowed = True
    
    def increment_web_search(self) -> None:
        """Increment web_search counter and check if limit reached."""
        self.web_search_count += 1
        if self.web_search_count >= self.web_search_limit:
            self.web_search_allowed = False
    
    def validate_tool_call(self, tool_name: str) -> Tuple[bool, str]:
        """
        Validate if a tool call is allowed.
        
        Args:
            tool_name: Name of the tool being called
            
        Returns:
            Tuple of (is_allowed, error_message)
            - is_allowed: True if tool can be executed
            - error_message: Empty if allowed, error description if not
        """
        # Check web_search limit
        if tool_name == "web_search" and not self.web_search_allowed:
            return (False, 
                   f"web_search is NOT ALLOWED. Limit ({self.web_search_limit}) reached. "
                   f"Use fetch_url to read URLs you discovered.")
        
        # All other tools are allowed by default
        return (True, "")
    
    def get_status(self) -> dict:
        """
        Get current validator status.
        
        Returns:
            Dictionary with validator state information
        """
        return {
            "web_search_limit": self.web_search_limit,
            "web_search_count": self.web_search_count,
            "web_search_allowed": self.web_search_allowed,
            "remaining_web_searches": max(0, self.web_search_limit - self.web_search_count)
        }
