"""File read and write tools for agent workspaces."""
from typing import Optional, List
from src.workspace.manager import WorkspaceManager


class WriteTool:
    """Tool for writing files to agent workspaces."""
    
    def __init__(self, workspace_manager: WorkspaceManager):
        self.workspace = workspace_manager
    
    def write(
        self,
        agent_name: str,
        filename: str,
        content: str,
        description: str = ""
    ) -> str:
        """
        Write content to a file in the agent's workspace.
        
        Args:
            agent_name: Name of the agent
            filename: Name of the file to write
            content: Content to write to the file
            description: Optional description of what this file contains
            
        Returns:
            Status message
        """
        try:
            file_path = self.workspace.write_file(agent_name, filename, content)
            msg = f"Successfully wrote to {filename}"
            if description:
                msg += f" (Description: {description})"
            return msg
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    def append(
        self,
        agent_name: str,
        filename: str,
        content: str
    ) -> str:
        """
        Append content to an existing file.
        
        Args:
            agent_name: Name of the agent
            filename: Name of the file
            content: Content to append
            
        Returns:
            Status message
        """
        try:
            workspace = self.workspace.create_agent_workspace(agent_name)
            file_path = os.path.join(workspace, filename)
            
            # Create directory if needed
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else workspace, exist_ok=True)
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write("\n" + content)
            
            return f"Successfully appended to {filename}"
        except Exception as e:
            return f"Error appending file: {str(e)}"


class ReadTool:
    """Tool for reading files from agent workspaces."""
    
    def __init__(self, workspace_manager: WorkspaceManager):
        self.workspace = workspace_manager
    
    def read(self, agent_name: str, filename: str) -> str:
        """
        Read content from a file in the agent's workspace.
        
        Args:
            agent_name: Name of the agent
            filename: Name of the file to read
            
        Returns:
            File content or error message
        """
        content = self.workspace.read_file(agent_name, filename)
        if content is None:
            return f"Error: File '{filename}' not found for agent '{agent_name}'"
        return content
    
    def read_multiple(self, agent_name: str, filenames: List[str]) -> str:
        """
        Read multiple files and return combined content.
        
        Args:
            agent_name: Name of the agent
            filenames: List of file names to read
            
        Returns:
            Combined content of all files
        """
        contents = []
        for filename in filenames:
            content = self.read(agent_name, filename)
            contents.append(f"=== {filename} ===\n{content}")
        return "\n\n".join(contents)
    
    def list_files(self, agent_name: str) -> str:
        """
        List all files in the agent's workspace.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Formatted list of files
        """
        files = self.workspace.list_files(agent_name)
        if not files:
            return f"No files found in workspace for agent '{agent_name}'"
        return "Files in workspace:\n" + "\n".join(f"  - {f}" for f in files)
    
    def get_context(self, agent_name: str) -> str:
        """
        Get full workspace context for the agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Formatted context from all files
        """
        return self.workspace.get_workspace_context(agent_name)


# Import os at module level for WriteTool.append
import os
