"""Enhanced OpenAI-compatible model client with token usage tracking."""
import requests
import json
from typing import List, Dict, Any, Optional
from config.settings import MODEL_BASE_URL, MODEL_NAME


class ModelClient:
    """Client for interacting with OpenAI-compatible local model server with token tracking."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        max_completion_tokens: Optional[int] = None,
        max_context_window: Optional[int] = None
    ):
        self.base_url = base_url or MODEL_BASE_URL
        self.model_name = model_name or MODEL_NAME
        self.max_completion_tokens = max_completion_tokens
        self.max_context_window = max_context_window
        self.chat_url = f"{self.base_url}/chat/completions"
        self.current_prompt_tokens = 0  # Current context size (from last response)
        self.current_completion_tokens = 0  # Last completion tokens
        self.total_tokens_used = 0  # Last total tokens
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.7,
        max_completion_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to the model and track token usage.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            tools: Optional list of tool definitions
            tool_choice: Optional tool choice specification
            temperature: Sampling temperature
            max_completion_tokens: Maximum tokens to generate in response
            
        Returns:
            Model response dictionary with token usage information
            
        Raises:
            ValueError: If context window would be exceeded
        """
        # Check context window before sending request
        self.check_context_window(messages)
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "reasoning_effort": "high"
        }
        
        # Use instance max_completion_tokens if not provided
        effective_max_tokens = max_completion_tokens or self.max_completion_tokens
        if effective_max_tokens:
            payload["max_tokens"] = effective_max_tokens
        
        if tools:
            payload["tools"] = tools
        
        if tool_choice:
            payload["tool_choice"] = tool_choice
        
        # Retry logic for API calls
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    self.chat_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=600  # 5 minutes for complex research
                )
                response.raise_for_status()
                response_data = response.json()
                
                # Extract token usage from response (no accumulation needed)
                if "usage" in response_data:
                    usage = response_data["usage"]
                    prompt_tokens = usage.get("prompt_tokens", 0)  # This is the CURRENT context size
                    completion_tokens = usage.get("completion_tokens", 0)
                    tokens_used = usage.get("total_tokens", 0)
                    
                    # Store current token counts (no accumulation - just latest values)
                    self.current_prompt_tokens = prompt_tokens
                    self.current_completion_tokens = completion_tokens
                    self.total_tokens_used = tokens_used
                    
                    # Store usage info in response for easy access
                    response_data["_prompt_tokens"] = prompt_tokens
                    response_data["_completion_tokens"] = completion_tokens
                    response_data["_tokens_used"] = tokens_used
                
                return response_data
                
            except requests.exceptions.HTTPError as e:
                last_error = e
                # Only retry on 5xx errors (server errors), not 4xx (client errors)
                if e.response.status_code >= 500 and attempt < max_retries:
                    print(f"HTTP Error {e.response.status_code}. Retrying immediately... (attempt {attempt + 2}/{max_retries + 1})")
                    continue  # Retry immediately without waiting
                else:
                    # Get error details from response
                    error_details = ""
                    try:
                        error_data = e.response.json()
                        error_details = str(error_data)
                    except:
                        error_details = str(e)
                    raise RuntimeError(f"Model API request failed ({e.response.status_code}): {error_details}")
                    
            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < max_retries:
                    print(f"Timeout. Retrying immediately... (attempt {attempt + 2}/{max_retries + 1})")
                    continue  # Retry immediately without waiting
                else:
                    raise RuntimeError(f"Model API request failed: Read timeout after {max_retries} retries")
                    
            except requests.exceptions.RequestException as e:
                last_error = e
                raise RuntimeError(f"Model API request failed: {e}")
        
        # Should not reach here, but just in case
        raise RuntimeError(f"Model API request failed after {max_retries} retries: {last_error}")
    
    def check_context_window(self, messages: List[Dict[str, str]]) -> bool:
        """
        Check if sending these messages would exceed the context window.
        
        Args:
            messages: Messages to be sent
            
        Returns:
            True if context window is within limits
            
        Raises:
            ValueError: If context window would be exceeded
        """
        if not self.max_context_window:
            return True  # No limit set
        
        # Use actual tracked prompt tokens from API responses
        # Estimate the new messages being sent
        estimated_new_prompt = self.estimate_tokens(messages)
        total_context = self.current_prompt_tokens + estimated_new_prompt
        
        if total_context > self.max_context_window:
            raise ValueError(
                f"Context window exceeded: {total_context} > {self.max_context_window}. "
                f"Current prompt tokens: {self.current_prompt_tokens}, "
                f"Estimated new prompt tokens: {estimated_new_prompt}"
            )
        
        return True
    
    def get_current_prompt_tokens(self) -> int:
        """
        Get the current context size (prompt tokens from last response).
        
        Returns:
            Current prompt tokens (context size)
        """
        return self.current_prompt_tokens
    
    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate the number of tokens in messages.
        
        Args:
            messages: List of messages
            
        Returns:
            Estimated token count (approximate)
        """
        total_chars = 0
        for msg in messages:
            content = msg.get("content") or ""
            # Handle non-string content (e.g. multimodal content lists)
            if isinstance(content, list):
                content = str(content)
            total_chars += len(content)
            
            # Also count tool_calls if present (assistant messages with tool calls)
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                total_chars += len(str(tool_calls))
        
        # Rough estimate: 1 token ≈ 4 characters
        return total_chars // 4
    
    def get_choice(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the choice from model response."""
        if "choices" not in response or not response["choices"]:
            raise ValueError("Invalid model response: no choices")
        return response["choices"][0]
    
    def get_message(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the message from model response."""
        choice = self.get_choice(response)
        return choice.get("message", {})
    
    def get_content(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract content from model response."""
        message = self.get_message(response)
        return message.get("content")
    
    def get_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool calls from model response."""
        message = self.get_message(response)
        return message.get("tool_calls", [])
    
    def get_reasoning(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Extract reasoning from model response.
        Checks both 'reasoning_content' and 'reasoning' fields.
        
        Args:
            response: Model response dictionary
            
        Returns:
            Reasoning content if available, None otherwise
        """
        message = self.get_message(response)
        # Check both keys, return whichever has content
        reasoning = message.get("reasoning_content") or message.get("reasoning")
        return reasoning
    
    def get_usage(self, response: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract token usage from model response.
        
        Args:
            response: Model response dictionary
            
        Returns:
            Dictionary with prompt_tokens, completion_tokens, total_tokens
        """
        return response.get("usage", {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        })
    
    def get_tokens_used(self, response: Dict[str, Any]) -> int:
        """
        Get tokens used in this specific response.
        
        Args:
            response: Model response dictionary
            
        Returns:
            Number of tokens used in this response
        """
        return response.get("_tokens_used", 0)
    
    def get_cumulative_tokens(self) -> int:
        """
        Get total cumulative tokens used across all requests.
        
        Returns:
            Total tokens used
        """
        return self.total_tokens_used
    
    def reset_token_counter(self):
        """Reset the cumulative token counter."""
        self.total_tokens_used = 0
