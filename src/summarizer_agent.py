"""Summarization agent for compressing message history."""
from typing import List, Dict, Any, Optional
from src.api.model_client import ModelClient


class SummarizerAgent:
    """
    Summarize agent message history to free up context space.
    Compresses conversation while preserving key information.
    """
    
    def __init__(self, model_client: ModelClient):
        """
        Initialize summarizer agent.
        
        Args:
            model_client: Model client for generating summaries
        """
        self.model_client = model_client
    
    def summarize_history(self, message_history: List[Dict[str, str]]) -> str:
        """
        Summarize message history into compact form.
        
        Args:
            message_history: Full message history to summarize
            
        Returns:
            Summarized content as string
        """
        if not message_history:
            return ""
        
        # Group messages by role for better summarization
        system_messages = [m["content"] for m in message_history if m.get("role") == "system"]
        user_messages = [m["content"] for m in message_history if m.get("role") == "user"]
        assistant_messages = [m["content"] for m in message_history if m.get("role") == "assistant"]
        tool_messages = [m["content"] for m in message_history if m.get("role") == "tool"]
        
        # Build summary prompt
        summary_prompt = self._create_summary_prompt(
            system_messages,
            user_messages,
            assistant_messages,
            tool_messages
        )
        
        # Generate summary
        response = self.model_client.chat(
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=45000
        )
        
        summary = self.model_client.get_content(response) or ""
        return summary
    
    def _create_summary_prompt(
        self,
        system_messages: List[str],
        user_messages: List[str],
        assistant_messages: List[str],
        tool_messages: List[str]
    ) -> str:
        """
        Create a prompt for summarizing the conversation.
        
        Args:
            system_messages: System instructions
            user_messages: User inputs
            assistant_messages: Assistant responses
            tool_messages: Tool results
            
        Returns:
            Summary prompt string
        """
        prompt = """You are an expert at summarizing AI agent conversations. 
Create a concise summary that preserves all essential information while reducing token count.

IMPORTANT: Preserve these elements:
- Research topic and goals
- Key findings and discoveries
- Important search queries and their results
- Critical data, facts, and figures
- Decisions made and reasoning
- Open questions or areas needing more research

Format the summary as structured text with clear sections.

CONVERSATION TO SUMMARIZE:

"""
        
        if system_messages:
            prompt += f"SYSTEM INSTRUCTIONS:\n{' | '.join(system_messages[:3])}\n\n"
        
        if user_messages:
            prompt += f"USER QUESTIONS/TASKS ({len(user_messages)} total):\n"
            for i, msg in enumerate(user_messages[:5], 1):
                # Truncate long messages
                content = msg[:300] + "..." if len(msg) > 300 else msg
                prompt += f"{i}. {content}\n"
            if len(user_messages) > 5:
                prompt += f"... and {len(user_messages) - 5} more\n"
            prompt += "\n"
        
        if assistant_messages:
            prompt += f"ASSISTANT RESPONSES ({len(assistant_messages)} total):\n"
            for i, msg in enumerate(assistant_messages[:5], 1):
                content = msg[:300] + "..." if len(msg) > 300 else msg
                prompt += f"{i}. {content}\n"
            if len(assistant_messages) > 5:
                prompt += f"... and {len(assistant_messages) - 5} more\n"
            prompt += "\n"
        
        if tool_messages:
            # Summarize tool results briefly
            prompt += f"TOOL RESULTS: {len(tool_messages)} tool calls executed\n"
        
        prompt += """
Now create a comprehensive but compact summary that captures all essential information.
Use concise language and structured formatting.
"""
        
        return prompt
    
    def create_summarized_history(self, original_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Create new minimal history with summarized content.
        
        Args:
            original_history: Full message history
            
        Returns:
            New history with summarized system message
        """
        # Generate summary
        summary = self.summarize_history(original_history)
        
        # Create new minimal history
        new_history = [
            {
                "role": "system",
                "content": f"""You are a research agent continuing an ongoing research task.

PREVIOUS CONVERSATION SUMMARY:
{summary}

IMPORTANT: This summary contains all essential information from our previous conversation. 
Use this context to continue the research task seamlessly.
The research may be incomplete - check the summary for open questions or areas needing more research.

Continue the research based on this summarized context."""
            }
        ]
        
        # Optionally add the most recent user message if it exists
        recent_user_messages = [m for m in original_history if m.get("role") == "user"]
        if recent_user_messages:
            new_history.append({
                "role": "user",
                "content": recent_user_messages[-1]["content"]
            })
        
        return new_history
    
    def estimate_compression_ratio(
        self,
        original_history: List[Dict[str, str]],
        summarized_history: List[Dict[str, str]]
    ) -> float:
        """
        Estimate the compression ratio achieved by summarization.
        
        Args:
            original_history: Original message history
            summarized_history: Summarized message history
            
        Returns:
            Compression ratio (original_size / summarized_size)
        """
        original_size = sum(len(m.get("content", "")) for m in original_history)
        summarized_size = sum(len(m.get("content", "")) for m in summarized_history)
        
        if summarized_size == 0:
            return float('inf')
        
        return original_size / summarized_size
