"""
File system operations for repository files.
"""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

class FileSystem:
    def __init__(self, repo_path: Path):
        """
        Initialize file system operations with a repository path.
        
        Args:
            repo_path: Path to the repository directory
        """
        self.repo_path = repo_path
    
    def read_file(self, file_path: str) -> str:
        """
        Read the content of a file.
        
        Args:
            file_path: Path to the file, relative to repository root
            
        Returns:
            File content as string
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return full_path.read_text(encoding="utf-8")
    
    def write_file(self, file_path: str, content: str) -> None:
        """
        Write content to a file.
        
        Args:
            file_path: Path to the file, relative to repository root
            content: File content
        """
        full_path = self.repo_path / file_path
        
        # Create parent directories if they don't exist
        os.makedirs(full_path.parent, exist_ok=True)
        
        full_path.write_text(content, encoding="utf-8")
    
    def delete_file(self, file_path: str) -> None:
        """
        Delete a file.
        
        Args:
            file_path: Path to the file, relative to repository root
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        os.remove(full_path)
    
    def list_files(self, directory: str = "", pattern: str = "*") -> List[str]:
        """
        List files in a directory.
        
        Args:
            directory: Directory path, relative to repository root
            pattern: Glob pattern for file filtering
            
        Returns:
            List of file paths, relative to the specified directory
        """
        search_dir = self.repo_path / directory
        
        if not search_dir.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        files = []
        for path in search_dir.glob(pattern):
            if path.is_file():
                # Make paths relative to the specified directory
                rel_path = path.relative_to(search_dir)
                files.append(str(rel_path))
        
        return files
    
    def list_directories(self, directory: str = "") -> List[str]:
        """
        List subdirectories in a directory.
        
        Args:
            directory: Directory path, relative to repository root
            
        Returns:
            List of directory names
        """
        search_dir = self.repo_path / directory
        
        if not search_dir.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        directories = []
        for path in search_dir.iterdir():
            if path.is_dir() and not path.name.startswith("."):
                directories.append(path.name)
        
        return directories
    
    def get_file_stats(self, file_path: str) -> Dict[str, Any]:
        """
        Get file statistics.
        
        Args:
            file_path: Path to the file, relative to repository root
            
        Returns:
            Dictionary with file statistics
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = full_path.stat()
        
        return {
            "size": stat.st_size,
            "modified_time": stat.st_mtime,
            "created_time": stat.st_ctime
        }
    
    def copy_file(self, source: str, destination: str) -> None:
        """
        Copy a file.
        
        Args:
            source: Source file path, relative to repository root
            destination: Destination file path, relative to repository root
        """
        source_path = self.repo_path / source
        dest_path = self.repo_path / destination
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        # Create parent directories if they don't exist
        os.makedirs(dest_path.parent, exist_ok=True)
        
        shutil.copy2(source_path, dest_path)
    
    def move_file(self, source: str, destination: str) -> None:
        """
        Move a file.
        
        Args:
            source: Source file path, relative to repository root
            destination: Destination file path, relative to repository root
        """
        source_path = self.repo_path / source
        dest_path = self.repo_path / destination
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        # Create parent directories if they don't exist
        os.makedirs(dest_path.parent, exist_ok=True)
        
        shutil.move(source_path, dest_path)