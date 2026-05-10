"""Base Agent class with tool management capabilities."""
from typing import Dict, Any, List, Optional, Callable
from src.api.model_client import ModelClient


class Tool:
    """Base class for agent tools."""
    
    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """Convert tool to OpenAI tool definition format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    def execute(self, **kwargs) -> Any:
        """Execute the tool with given arguments."""
        return self.func(**kwargs)


class Agent:
    """Base agent class with tool management and model interaction."""
    
    def __init__(
        self,
        name: str,
        system_prompt: str,
        model_client: ModelClient,
        workspace_path: Optional[str] = None
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.model_client = model_client
        self.workspace_path = workspace_path
        self.tools: Dict[str, Tool] = {}
        self.message_history: List[Dict[str, str]] = []
        
        # Initialize with system message
        self.message_history.append({
            "role": "system",
            "content": system_prompt
        })
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the agent."""
        self.tools[tool.name] = tool
    
    def unregister_tool(self, tool_name: str) -> None:
        """Unregister a tool from the agent."""
        if tool_name in self.tools:
            del self.tools[tool_name]
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all registered tool definitions."""
        return [tool.to_tool_definition() for tool in self.tools.values()]
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.message_history.append({
            "role": role,
            "content": content
        })
    
    def step(self) -> Optional[Dict[str, Any]]:
        """
        Execute one step of agent reasoning.
        
        Returns:
            Tool calls if any, otherwise None
        """
        tool_definitions = self.get_tool_definitions()
        
        response = self.model_client.chat(
            messages=self.message_history,
            tools=tool_definitions if tool_definitions else None
        )
        
        message = self.model_client.get_message(response)
        self.add_message("assistant", message.get("content", ""))
        
        # Check for tool calls
        tool_calls = self.model_client.get_tool_calls(response)
        return tool_calls if tool_calls else None
    
    def execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """
        Execute a tool call and return the result.
        
        Args:
            tool_call: Tool call dictionary from model
            
        Returns:
            Tool execution result as string
        """
        function = tool_call["function"]
        tool_name = function["name"]
        arguments = function.get("arguments", "{}")
        
        # Parse arguments if string
        if isinstance(arguments, str):
            import json
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        
        if tool_name not in self.tools:
            return f"Error: Tool '{tool_name}' not found"
        
        try:
            result = self.tools[tool_name].execute(**arguments)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"
    
    def run(self, user_message: str, max_steps: int = 10) -> str:
        """
        Run the agent with a user message until completion.
        
        Args:
            user_message: Initial user message
            max_steps: Maximum number of reasoning steps
            
        Returns:
            Final response from the agent
        """
        self.add_message("user", user_message)
        
        for _ in range(max_steps):
            tool_calls = self.step()
            
            if not tool_calls:
                # No tool calls, agent is done
                break
            
            # Execute each tool call
            for tool_call in tool_calls:
                tool_result = self.execute_tool(tool_call)
                self.add_message("tool", tool_result)
        
        # Get final response
        response = self.model_client.chat(messages=self.message_history)
        return self.model_client.get_content(response) or ""
