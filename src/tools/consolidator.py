"""Workspace consolidation for merging subagent research."""
import os
import shutil
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.workspace.manager import WorkspaceManager


class Consolidator:
    """Consolidate subagent research into main workspace."""
    
    def __init__(self, workspace_manager: WorkspaceManager):
        self.workspace = workspace_manager
    
    def consolidate(
        self,
        main_agent_uuid: str,
        subagent_names: List[str],
        topic: str,
        subtopics: List[str]
    ) -> str:
        """
        Consolidate all subagent research into main workspace.
        
        Args:
            main_agent_uuid: Main agent workspace identifier
            subagent_names: List of subagent names
            topic: Original research topic
            subtopics: List of subtopics researched
            
        Returns:
            Path to consolidated workspace
        """
        # Create subdirectories in main workspace
        drafts_dir = self.workspace.write_file(
            main_agent_uuid,
            "drafts/.gitkeep",
            ""
        )
        drafts_dir = os.path.dirname(drafts_dir)
        os.makedirs(drafts_dir, exist_ok=True)
        
        # Consolidate subagent files
        all_sources = []
        all_findings = []
        
        for subagent_name in subagent_names:
            # Copy subagent files to main workspace
            self._copy_subagent_files(main_agent_uuid, subagent_name)
            
            # Collect findings
            summary = self.workspace.read_file(subagent_name, "summary.md")
            if summary:
                all_findings.append(f"### {subagent_name}\n\n{summary}")
            
            # Collect sources
            sources = self.workspace.read_file(subagent_name, "sources.md")
            if sources:
                all_sources.append(f"#### {subagent_name}\n\n{sources}")
        
        # Create consolidated files
        self._create_subtopics_file(main_agent_uuid, topic, subtopics)
        self._create_research_notes(main_agent_uuid, all_findings)
        self._create_sources_file(main_agent_uuid, all_sources)
        
        return self.workspace.get_agent_workspace(main_agent_uuid)
    
    def _copy_subagent_files(
        self,
        main_agent_uuid: str,
        subagent_name: str
    ):
        """Copy subagent files to main workspace."""
        # Get subagent workspace
        subagent_workspace = self.workspace.get_agent_workspace(subagent_name)
        if not subagent_workspace:
            return
        
        # List all files in subagent workspace
        files = self.workspace.list_files(subagent_name)
        
        for file_path in files:
            # Read content
            content = self.workspace.read_file(subagent_name, file_path)
            if content:
                # Write to main workspace with subagent prefix
                main_file_path = f"{subagent_name}/{file_path}"
                self.workspace.write_file(main_agent_uuid, main_file_path, content)
    
    def _create_subtopics_file(
        self,
        main_agent_uuid: str,
        topic: str,
        subtopics: List[str]
    ):
        """Create subtopics.md file."""
        content = f"# Research Topic\n\n{topic}\n\n## Subtopics\n\n"
        
        for i, subtopic in enumerate(subtopics, 1):
            content += f"{i}. {subtopic}\n"
        
        content += f"\n---\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        self.workspace.write_file(main_agent_uuid, "subtopics.md", content)
    
    def _create_research_notes(
        self,
        main_agent_uuid: str,
        findings: List[str]
    ):
        """Create consolidated research_notes.md file."""
        content = "# Consolidated Research Notes\n\n"
        content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "---\n\n"
        
        for finding in findings:
            content += finding + "\n\n---\n\n"
        
        content += "\n## Summary\n\n"
        content += "This document contains consolidated research findings from all subagents.\n"
        content += "Each subagent's work is organized in their respective subdirectories.\n"
        
        self.workspace.write_file(main_agent_uuid, "research_notes.md", content)
    
    def _create_sources_file(
        self,
        main_agent_uuid: str,
        sources_sections: List[str]
    ):
        """Create consolidated sources.md file."""
        content = "# Research Sources\n\n"
        content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "All sources discovered during research:\n\n"
        
        for section in sources_sections:
            content += section + "\n\n"
        
        content += "\n---\n"
        content += "*Total sources collected across all subagents*\n"
        
        self.workspace.write_file(main_agent_uuid, "sources.md", content)
    
    def create_draft_report(
        self,
        main_agent_uuid: str,
        topic: str,
        subagent_results: Dict[str, str]
    ) -> str:
        """
        Create a draft report in the drafts folder.
        
        Args:
            main_agent_uuid: Main agent workspace
            topic: Research topic
            subagent_results: Subagent findings
            
        Returns:
            Path to draft report
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_draft_v1_{timestamp}.md"
        
        content = f"# Draft Research Report\n\n"
        content += f"**Topic:** {topic}\n\n"
        content += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "---\n\n"
        content += "## Preliminary Findings\n\n"
        
        for agent_name, findings in subagent_results.items():
            content += f"### {agent_name}\n\n"
            # Include first 500 chars as preview
            preview = findings[:500] + "..." if len(findings) > 500 else findings
            content += preview + "\n\n"
        
        content += "---\n\n"
        content += "*This is a draft report. Final report will be generated after quality validation.*\n"
        
        file_path = self.workspace.write_file(main_agent_uuid, f"drafts/{filename}", content)
        return file_path
    
    def get_workspace_summary(self, main_agent_uuid: str) -> str:
        """
        Get a summary of all files in the consolidated workspace.
        
        Args:
            main_agent_uuid: Main agent workspace
            
        Returns:
            Summary of workspace contents
        """
        files = self.workspace.list_files(main_agent_uuid)
        
        if not files:
            return "Workspace is empty"
        
        summary = "# Workspace Summary\n\n"
        summary += f"Total files: {len(files)}\n\n"
        summary += "## Files\n\n"
        
        # Group by directory
        directories = {}
        for file_path in files:
            dir_name = os.path.dirname(file_path) or "root"
            if dir_name not in directories:
                directories[dir_name] = []
            directories[dir_name].append(os.path.basename(file_path))
        
        for dir_name, dir_files in directories.items():
            summary += f"### {dir_name}/\n\n"
            for file in dir_files:
                summary += f"- {file}\n"
            summary += "\n"
        
        return summary
