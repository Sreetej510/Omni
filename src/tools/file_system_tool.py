"""File system tools for directory listing and file operations."""
import os
from typing import Dict, Any, Optional
from datetime import datetime


class FileSystemTool:
    """
    Tool for file system operations.
    Provides ls functionality for listing directory contents.
    """
    
    def __init__(self, base_directory: str):
        """
        Initialize file system tool.
        
        Args:
            base_directory: Base directory that restricts file operations
        """
        self.base_directory = base_directory
    
    def ls(self, directory: Optional[str] = None) -> str:
        """
        List files in specified directory.
        
        Args:
            directory: Directory to list (defaults to base_directory)
            
        Returns:
            Formatted string with file information
        """
        if directory is None:
            directory = self.base_directory
        
        # Ensure directory is within base directory (security)
        if not directory.startswith(self.base_directory):
            directory = self.base_directory
        
        # Check if directory exists
        if not os.path.exists(directory):
            return f"Error: Directory does not exist: {directory}"
        
        if not os.path.isdir(directory):
            return f"Error: Not a directory: {directory}"
        
        try:
            entries = os.listdir(directory)
            
            if not entries:
                return f"Directory is empty: {directory}"
            
            # Build output
            output_lines = []
            output_lines.append(f"Contents of: {directory}")
            output_lines.append("=" * 60)
            
            # Separate files and directories
            dirs = []
            files = []
            
            for entry in entries:
                full_path = os.path.join(directory, entry)
                if os.path.isdir(full_path):
                    dirs.append(entry)
                else:
                    files.append(entry)
            
            # List directories first
            if dirs:
                output_lines.append("\nDirectories:")
                for dir_name in sorted(dirs):
                    full_path = os.path.join(directory, dir_name)
                    try:
                        mod_time = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M")
                        output_lines.append(f"  📁 {dir_name}/ (Modified: {mod_time})")
                    except Exception:
                        output_lines.append(f"  📁 {dir_name}/")
            
            # Then list files with details
            if files:
                output_lines.append("\nFiles:")
                for file_name in sorted(files):
                    full_path = os.path.join(directory, file_name)
                    try:
                        size = os.path.getsize(full_path)
                        size_str = self._format_size(size)
                        mod_time = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M")
                        output_lines.append(f"  📄 {file_name} ({size_str}, Modified: {mod_time})")
                    except Exception:
                        output_lines.append(f"  📄 {file_name}")
            
            # Summary
            output_lines.append("\n" + "=" * 60)
            output_lines.append(f"Total: {len(dirs)} directories, {len(files)} files")
            
            return "\n".join(output_lines)
            
        except PermissionError:
            return f"Error: Permission denied: {directory}"
        except Exception as e:
            return f"Error listing directory: {str(e)}"
    
    def _format_size(self, size: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
    
    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """
        Get detailed information about a file.
        
        Args:
            filepath: Path to file
            
        Returns:
            Dictionary with file information
        """
        # Ensure filepath is within base directory
        if not filepath.startswith(self.base_directory):
            filepath = os.path.join(self.base_directory, filepath)
        
        if not os.path.exists(filepath):
            return {"error": f"File does not exist: {filepath}"}
        
        try:
            stat = os.stat(filepath)
            return {
                "name": os.path.basename(filepath),
                "path": filepath,
                "size": stat.st_size,
                "size_formatted": self._format_size(stat.st_size),
                "is_directory": os.path.isdir(filepath),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            return {"error": f"Error getting file info: {str(e)}"}
