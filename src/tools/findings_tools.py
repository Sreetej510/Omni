"""Findings management tools for agents."""
from typing import Dict
from src.tools.findings_manager import FindingsManager


class FindingsTools:
    """Tool set for findings management."""
    
    def __init__(self, findings_manager: FindingsManager):
        self.findings_manager = findings_manager
    
    def add_findings(self, findings, agent_id: str = "agent") -> str:
        """
        Write multiple research findings at once. Can write up to 1000 words per finding. 
        Use this for ALL important information, quotes, statistics, and detailed analysis. 
        Each fact should be a separate finding.
        
        Args:
            findings: Single {title, content} object OR array of {title, content} objects
            agent_id: ID of the agent writing these findings
            
        Returns:
            Formatted results of all findings
        """
        # Handle both single finding and batch mode
        if isinstance(findings, dict):
            # Single finding - convert to batch
            findings = [findings]
        
        if not isinstance(findings, list):
            return "Error: findings must be an object or array of objects"
        
        # Process batch
        results = self.findings_manager.add_findings_batch(findings, agent_id)
        
        # Format results
        output = []
        success_count = 0
        error_count = 0
        
        for result in results:
            if result["status"] == "success":
                success_count += 1
                output.append(f"✓ Finding written: {result['title']} (ID: {result['id']})")
            else:
                error_count += 1
                error_msg = result.get("message", "Unknown error")
                output.append(f"✗ Failed: {result['title']} - {error_msg}")
        
        summary = f"\nBatch complete: {success_count} successful, {error_count} failed"
        return "\n".join(output) + summary
    
    def findings_list(self) -> str:
        """
        List all findings (ID and title only).
        
        Returns:
            Formatted list
        """
        findings = self.findings_manager.list_findings()
        if not findings:
            return "No findings yet."
        
        output = "Available Findings:\n"
        for f in findings:
            output += f"- {f['id']}: {f['title']}\n"
        return output
    
    def findings_read(self, finding_ids) -> str:
        """
        Read one or more findings by ID. Can read up to 5 findings at once for context.
        
        Args:
            finding_ids: Single finding ID (str) OR list of finding IDs (List[str])
            
        Returns:
            Formatted text of finding(s) content
        """
        # Handle both single ID and list of IDs
        if isinstance(finding_ids, str):
            ids_to_read = [finding_ids]
        else:
            ids_to_read = finding_ids
        
        # Read all findings
        results = []
        for fid in ids_to_read:
            finding = self.findings_manager.read_finding(fid)
            if finding:
                results.append(f"Finding: {finding['title']}\n\nContent:\n{finding['content']}")
            else:
                results.append(f"Finding not found: {fid}")
        
        return "\n\n---\n\n".join(results)
