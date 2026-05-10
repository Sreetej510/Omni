"""Centralized findings management using JSON storage."""
import os
import json
import uuid
import threading
from typing import Dict, List, Optional
from datetime import datetime


class FindingsManager:
    """
    Centralized findings management using JSON storage.
    Shared by all agents and subagents for a topic.
    Thread-safe with locking for concurrent access.
    """
    
    def __init__(self, workspace: str):
        self.findings_file = os.path.join(workspace, "findings_db.json")
        self.lock = threading.Lock()
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Initialize findings database if it doesn't exist."""
        if not os.path.exists(self.findings_file):
            self._save_findings_db({"findings": []})
    
    def _load_findings_db(self) -> Dict:
        """Load findings database from JSON file."""
        with self.lock:
            try:
                with open(self.findings_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return {"findings": []}
                    return json.loads(content)
            except json.JSONDecodeError:
                # File is corrupted, return empty db
                return {"findings": []}
    
    def _save_findings_db(self, db: Dict):
        """Save findings database to JSON file."""
        with self.lock:
            # Write to temp file first, then rename for atomicity
            temp_file = self.findings_file + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, self.findings_file)
    
    def add_finding(self, title: str, content: str, agent_id: str) -> str:
        """
        Add a new finding to the database.
        
        Args:
            title: Finding title/heading
            content: Finding content
            agent_id: ID of the agent creating this finding
            
        Returns:
            Unique finding ID
        """
        db = self._load_findings_db()
        finding_id = str(uuid.uuid4())[:8]
        
        finding = {
            "id": finding_id,
            "title": title,
            "content": content,
            "agent_id": agent_id,
            "created_at": datetime.now().isoformat()
        }
        
        db["findings"].append(finding)
        self._save_findings_db(db)
        
        return finding_id
    
    def list_findings(self) -> List[Dict]:
        """
        List all findings (ID and title only, no content).
        
        Returns:
            List of finding metadata
        """
        db = self._load_findings_db()
        return [
            {"id": f["id"], "title": f["title"], "agent_id": f["agent_id"]}
            for f in db["findings"]
        ]
    
    def read_finding(self, finding_id: str) -> Optional[Dict]:
        """
        Read a specific finding by ID.
        
        Args:
            finding_id: ID of finding to read
            
        Returns:
            Full finding (id, title, content) or None
        """
        db = self._load_findings_db()
        for finding in db["findings"]:
            if finding["id"] == finding_id:
                return finding
        return None
