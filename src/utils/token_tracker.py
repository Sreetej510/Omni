"""Token tracker using real API token counts with dual tracking."""
from typing import Dict, Any


class TokenTracker:
    """
    Track token usage using real counts from API responses.
    Monitors both completion tokens and context window usage.
    """
    
    def __init__(self, max_completion_tokens: int, max_context_window: int, summarization_threshold: float = 0.80):
        """
        Initialize token tracker with dual limits.
        
        Args:
            max_completion_tokens: Maximum tokens to generate per response
            max_context_window: Maximum total context (prompt + completion)
            summarization_threshold: Percentage at which to trigger summarization (default 80%)
        """
        self.max_completion_tokens = max_completion_tokens
        self.max_context_window = max_context_window
        self.summarization_threshold = summarization_threshold
        
        # Track completion tokens
        self.completion_tokens = 0
        
        # Track context window (total tokens in conversation)
        self.context_tokens = 0
        
        self.peak_context_tokens = 0  # Track peak usage before summarization
    
    def update_usage(self, response: Dict[str, Any]):
        """
        Update token counts from API response.
        
        Args:
            response: Model response with usage information
        """
        # Try to get tokens from response
        prompt_tokens = response.get("_prompt_tokens", 0)
        completion_tokens = response.get("_completion_tokens", 0)
        total_tokens = response.get("_tokens_used", 0)
        
        # Fallback to usage object if custom keys not present
        if total_tokens == 0:
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
        
        # Update completion tokens
        self.completion_tokens += completion_tokens
        
        # Update context tokens
        self.context_tokens += total_tokens
        
        # Track peak usage
        if self.context_tokens > self.peak_context_tokens:
            self.peak_context_tokens = self.context_tokens
    
    def get_usage_percentage(self) -> float:
        """
        Get current context usage as percentage of max context window.
        
        Returns:
            Usage percentage (0-100)
        """
        if self.max_context_window == 0:
            return 0.0
        return (self.context_tokens / self.max_context_window) * 100
    
    def is_near_limit(self) -> bool:
        """
        Check if context usage exceeds summarization threshold.
        
        Returns:
            True if usage is at or above threshold
        """
        return self.get_usage_percentage() >= (self.summarization_threshold * 100)
    
    def get_remaining_context(self) -> int:
        """
        Get remaining tokens in context window.
        
        Returns:
            Number of remaining context tokens
        """
        return max(0, self.max_context_window - self.context_tokens)
    
    def get_completion_limit(self) -> int:
        """
        Get the max completion tokens limit.
        
        Returns:
            Max completion tokens per response
        """
        return self.max_completion_tokens
    
    def get_usage_info(self) -> Dict[str, Any]:
        """
        Get comprehensive usage information.
        
        Returns:
            Dictionary with usage details
        """
        return {
            "completion_tokens": self.completion_tokens,
            "context_tokens": self.context_tokens,
            "max_completion_tokens": self.max_completion_tokens,
            "max_context_window": self.max_context_window,
            "usage_percentage": self.get_usage_percentage(),
            "remaining_context": self.get_remaining_context(),
            "peak_context_tokens": self.peak_context_tokens,
            "is_near_limit": self.is_near_limit(),
            "threshold_percentage": self.summarization_threshold * 100
        }
    
    def reset(self):
        """Reset token counters (typically after summarization)."""
        self.completion_tokens = 0
        self.context_tokens = 0
    
    def log_usage(self, prefix: str = ""):
        """
        Log current usage to console.
        
        Args:
            prefix: Optional prefix for log message
        """
        info = self.get_usage_info()
        print(f"{prefix}Completion Tokens: {info['completion_tokens']} (max: {info['max_completion_tokens']})")
        print(f"{prefix}Context Tokens: {info['context_tokens']}/{info['max_context_window']} "
              f"({info['usage_percentage']:.1f}%) - "
              f"Remaining: {info['remaining_context']}")
    
    def get_usage_percentage(self) -> float:
        """
        Get current context window usage as percentage.
        
        Returns:
            Percentage of context window used (0.0 to 1.0+)
        """
        if self.max_context_window == 0:
            return 0.0
        return self.context_tokens / self.max_context_window
