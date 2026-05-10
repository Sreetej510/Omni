"""Enhanced workspace management with hierarchical structure support."""
import os
import shutil
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from config.settings import WORKSPACE_ROOT


class WorkspaceManager:
    """
    Manages hierarchical workspaces for agents and subagents.
    
    Structure:
    research/
    └── main_agent_<uuid>/
        ├── subagent_1/
        │   ├── research.md
        │   └── summary.md
        ├── subagent_2/
        └── final_report.md
    """
    
    def __init__(self, root_path: Optional[str] = None):
        self.root_path = root_path or WORKSPACE_ROOT
        os.makedirs(self.root_path, exist_ok=True)
    
    def create_main_agent_workspace(self, topic: Optional[str] = None) -> str:
        """
        Create a new main agent workspace with unique UUID.
        
        Args:
            topic: Optional topic name to include in workspace
            
        Returns:
            Main agent workspace identifier (uuid)
        """
        # Generate unique UUID
        agent_uuid = str(uuid.uuid4())[:8]  # Short UUID
        
        # Create workspace directory
        workspace_name = f"main_agent_{agent_uuid}"
        workspace_path = os.path.join(self.root_path, workspace_name)
        os.makedirs(workspace_path, exist_ok=True)
        
        # Create subdirectories
        os.makedirs(os.path.join(workspace_path, "subagent_1"), exist_ok=True)
        os.makedirs(os.path.join(workspace_path, "subagent_2"), exist_ok=True)
        os.makedirs(os.path.join(workspace_path, "subagent_3"), exist_ok=True)
        os.makedirs(os.path.join(workspace_path, "drafts"), exist_ok=True)
        
        return workspace_name
    
    def create_subagent_workspace(
        self,
        main_agent_uuid: str,
        subagent_number: int
    ) -> str:
        """
        Create a subagent workspace within main agent workspace.
        
        Args:
            main_agent_uuid: Main agent workspace identifier
            subagent_number: Subagent number (1, 2, 3, etc.)
            
        Returns:
            Full subagent workspace identifier
        """
        subagent_name = f"{main_agent_uuid}/subagent_{subagent_number}"
        workspace_path = os.path.join(self.root_path, subagent_name)
        os.makedirs(workspace_path, exist_ok=True)
        
        return subagent_name
    
    def create_agent_workspace(self, agent_name: str) -> str:
        """
        Create an isolated workspace folder for an agent.
        Supports both standalone and hierarchical workspaces.
        
        Args:
            agent_name: Name of the agent (can include path like "main/subagent_1")
            
        Returns:
            Path to the created workspace
        """
        # Sanitize agent name for filesystem
        safe_name = self._sanitize_name(agent_name)
        workspace_path = os.path.join(self.root_path, safe_name)
        os.makedirs(workspace_path, exist_ok=True)
        return workspace_path
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for filesystem, preserving path separators."""
        # Replace forward slashes with OS separator
        name = name.replace("/", os.sep)
        # Sanitize each path component
        parts = name.split(os.sep)
        safe_parts = []
        for part in parts:
            safe_part = "".join(c if c.isalnum() or c in "-_" else "_" for c in part)
            safe_parts.append(safe_part)
        return os.sep.join(safe_parts)
    
    def delete_agent_workspace(self, agent_name: str) -> bool:
        """
        Delete an agent's workspace.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            True if successful, False otherwise
        """
        safe_name = self._sanitize_name(agent_name)
        workspace_path = os.path.join(self.root_path, safe_name)
        try:
            if os.path.exists(workspace_path):
                shutil.rmtree(workspace_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting workspace: {e}")
            return False
    
    def get_agent_workspace(self, agent_name: str) -> Optional[str]:
        """
        Get the path to an agent's workspace if it exists.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Path to workspace or None
        """
        safe_name = self._sanitize_name(agent_name)
        workspace_path = os.path.join(self.root_path, safe_name)
        if os.path.exists(workspace_path):
            return workspace_path
        return None
    
    def list_workspaces(self) -> List[str]:
        """List all existing workspaces."""
        if not os.path.exists(self.root_path):
            return []
        return [
            d for d in os.listdir(self.root_path)
            if os.path.isdir(os.path.join(self.root_path, d))
        ]
    
    def list_main_agent_workspaces(self) -> List[str]:
        """List all main agent workspaces."""
        if not os.path.exists(self.root_path):
            return []
        return [
            d for d in os.listdir(self.root_path)
            if os.path.isdir(os.path.join(self.root_path, d)) and d.startswith("main_agent_")
        ]
    
    def write_file(self, agent_name: str, filename: str, content: str) -> str:
        """
        Write a file to an agent's workspace.
        Supports hierarchical paths like "main_agent_xxx/subagent_1".
        
        Args:
            agent_name: Name of the agent
            filename: Name of the file (can include subdirectories)
            content: File content
            
        Returns:
            Path to the written file
        """
        workspace = self.create_agent_workspace(agent_name)
        file_path = os.path.join(workspace, filename)
        
        # Create subdirectories if needed
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else workspace, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def read_file(self, agent_name: str, filename: str) -> Optional[str]:
        """
        Read a file from an agent's workspace.
        
        Args:
            agent_name: Name of the agent
            filename: Name of the file
            
        Returns:
            File content or None if not found
        """
        workspace = self.get_agent_workspace(agent_name)
        if not workspace:
            return None
        
        file_path = os.path.join(workspace, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def list_files(self, agent_name: str) -> List[str]:
        """
        List all files in an agent's workspace.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of file paths relative to workspace
        """
        workspace = self.get_agent_workspace(agent_name)
        if not workspace:
            return []
        
        files = []
        for root, _, filenames in os.walk(workspace):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, workspace)
                files.append(rel_path)
        return files
    
    def get_workspace_context(self, agent_name: str) -> str:
        """
        Get a summary of all files in an agent's workspace for context.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Formatted context string
        """
        files = self.list_files(agent_name)
        if not files:
            return "No files in workspace."
        
        context_parts = []
        for file_path in files:
            content = self.read_file(agent_name, file_path)
            if content:
                context_parts.append(f"=== {file_path} ===\n{content}\n")
        
        return "\n".join(context_parts)
    
    def copy_file(
        self,
        source_agent: str,
        source_file: str,
        dest_agent: str,
        dest_file: str
    ) -> bool:
        """
        Copy a file from one agent workspace to another.
        
        Args:
            source_agent: Source agent name
            source_file: Source file path
            dest_agent: Destination agent name
            dest_file: Destination file path
            
        Returns:
            True if successful
        """
        content = self.read_file(source_agent, source_file)
        if content is None:
            return False
        
        self.write_file(dest_agent, dest_file, content)
        return True
    
    def copy_workspace(
        self,
        source_agent: str,
        dest_agent: str,
        preserve_structure: bool = True
    ) -> bool:
        """
        Copy all files from one workspace to another.
        
        Args:
            source_agent: Source agent name
            dest_agent: Destination agent name
            preserve_structure: Whether to preserve subdirectory structure
            
        Returns:
            True if successful
        """
        source_workspace = self.get_agent_workspace(source_agent)
        if not source_workspace:
            return False
        
        dest_workspace = self.create_agent_workspace(dest_agent)
        
        try:
            for root, _, filenames in os.walk(source_workspace):
                for filename in filenames:
                    src_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(src_path, source_workspace)
                    
                    if preserve_structure:
                        dest_path = rel_path
                    else:
                        dest_path = filename
                    
                    with open(src_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self.write_file(dest_agent, dest_path, content)
            
            return True
        except Exception as e:
            print(f"Error copying workspace: {e}")
            return False
