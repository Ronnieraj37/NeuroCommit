"""
Manages code context for AI prompts.
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

class ContextManager:
    def __init__(self, repo_path: Path, max_files: int = 5, max_file_size: int = 10000):
        """
        Initialize context manager.
        
        Args:
            repo_path: Path to the repository
            max_files: Maximum number of files to include in context
            max_file_size: Maximum size of a file to include in context (in characters)
        """
        self.repo_path = repo_path
        self.max_files = max_files
        self.max_file_size = max_file_size
    
    def get_file_dependencies(self, file_path: str) -> List[str]:
        """
        Get a list of files that the given file depends on.
        This is a simplistic implementation that looks for import statements.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of file paths that the file depends on
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            return []
        
        content = full_path.read_text(encoding="utf-8")
        dependencies = []
        
        # Get file extension
        ext = os.path.splitext(file_path)[1]
        
        if ext in [".py", ".pyw"]:
            # Look for Python imports
            import re
            
            # Simple regex for import statements (not perfect but good enough for most cases)
            import_patterns = [
                r'from\s+([\w.]+)\s+import',  # from x import y
                r'import\s+([\w.]+)'          # import x
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    module_path = match.group(1).replace(".", "/")
                    
                    # Check if it's a local module
                    potential_paths = [
                        f"{module_path}.py",
                        f"{module_path}/__init__.py"
                    ]
                    
                    for potential_path in potential_paths:
                        if (self.repo_path / potential_path).exists():
                            dependencies.append(potential_path)
        
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            # Look for JavaScript/TypeScript imports
            import re
            
            # Simple regex for import statements
            import_patterns = [
                r'import.*?from\s+[\'"]([^\'"]+)[\'"]',  # import x from 'y'
                r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'  # require('y')
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    module_path = match.group(1)
                    
                    # Ignore node_modules and external packages
                    if module_path.startswith("."):
                        # Resolve relative path
                        dirname = os.path.dirname(file_path)
                        module_path = os.path.normpath(os.path.join(dirname, module_path))
                        
                        # Check for extensions
                        potential_extensions = ["", ".js", ".ts", ".jsx", ".tsx"]
                        for ext in potential_extensions:
                            potential_path = f"{module_path}{ext}"
                            if (self.repo_path / potential_path).exists():
                                dependencies.append(potential_path)
                                break
        
        # Limit to existing files
        return [dep for dep in dependencies if (self.repo_path / dep).exists()]
    
    def get_context_for_file(self, file_path: str) -> Dict[str, str]:
        """
        Get relevant context for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary of {file_path: content} for relevant context
        """
        context = {}
        visited: Set[str] = set()
        
        def collect_context(path: str, depth: int = 0):
            if path in visited or len(context) >= self.max_files or depth > 2:
                return
            
            visited.add(path)
            full_path = self.repo_path / path
            
            if not full_path.exists() or not full_path.is_file():
                return
            
            # Skip files that are too large
            if full_path.stat().st_size > self.max_file_size:
                return
            
            # Skip binary files
            if self._is_binary_file(full_path):
                return
            
            # Add file to context
            try:
                content = full_path.read_text(encoding="utf-8")
                context[path] = content
            except UnicodeDecodeError:
                # Skip files that can't be decoded as UTF-8
                return
            
            # Add dependencies
            dependencies = self.get_file_dependencies(path)
            for dep in dependencies:
                collect_context(dep, depth + 1)
        
        # Start with the target file
        collect_context(file_path)
        
        # If we haven't reached the maximum, add files in the same directory
        if len(context) < self.max_files:
            directory = os.path.dirname(file_path)
            for sibling in (self.repo_path / directory).glob("*"):
                if sibling.is_file() and str(sibling.relative_to(self.repo_path)) not in visited:
                    collect_context(str(sibling.relative_to(self.repo_path)))
        
        return context
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """
        Check if a file is binary.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file is binary, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                file.read(1024)
                return False
        except UnicodeDecodeError:
            return True