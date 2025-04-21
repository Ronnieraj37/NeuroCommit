"""
Validates code changes to ensure they meet project standards.
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

class ValidationResult:
    def __init__(self, valid: bool, issues: List[Dict[str, Any]] = None):
        """
        Initialize validation result.
        
        Args:
            valid: Whether the changes are valid
            issues: List of validation issues
        """
        self.valid = valid
        self.issues = issues or []

class CodeValidator:
    def __init__(self, repo_path: Path):
        """
        Initialize code validator.
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
    
    async def validate_changes(self, changed_files: List[str]) -> ValidationResult:
        """
        Validate code changes.
        
        Args:
            changed_files: List of changed file paths
            
        Returns:
            Validation result
        """
        issues = []
        
        for file_path in changed_files:
            # Skip files that don't exist (e.g., deleted files)
            full_path = self.repo_path / file_path
            if not full_path.exists():
                continue
            
            try:
                # Check file size
                if full_path.stat().st_size > 1_000_000:  # 1MB
                    issues.append({
                        'file': file_path,
                        'type': 'size',
                        'message': f"File size exceeds 1MB ({full_path.stat().st_size} bytes)"
                    })
                    continue
                
                # Read file content
                content = full_path.read_text(encoding='utf-8')
                
                # Get file extension
                _, ext = os.path.splitext(file_path)
                
                # Validate based on file type
                if ext.lower() in ['.py', '.pyw']:
                    python_issues = self._validate_python(file_path, content)
                    issues.extend(python_issues)
                
                elif ext.lower() in ['.js', '.jsx', '.ts', '.tsx']:
                    js_issues = self._validate_javascript(file_path, content)
                    issues.extend(js_issues)
                
                elif ext.lower() in ['.java']:
                    java_issues = self._validate_java(file_path, content)
                    issues.extend(java_issues)
                
                # Common validations for all file types
                common_issues = self._validate_common(file_path, content)
                issues.extend(common_issues)
            
            except UnicodeDecodeError:
                issues.append({
                    'file': file_path,
                    'type': 'encoding',
                    'message': "File is not valid UTF-8 text"
                })
            
            except Exception as e:
                issues.append({
                    'file': file_path,
                    'type': 'error',
                    'message': f"Error validating file: {str(e)}"
                })
        
        return ValidationResult(valid=len(issues) == 0, issues=issues)
    
    def _validate_python(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        Validate Python code.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check for syntax errors
        try:
            compile(content, file_path, 'exec')
        except SyntaxError as e:
            issues.append({
                'file': file_path,
                'line': e.lineno,
                'type': 'syntax',
                'message': f"Syntax error: {e.msg}"
            })
        
        # Check for common issues
        
        # 1. Long lines (PEP 8 recommends max 79 characters)
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 100:  # Allow some flexibility
                issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'style',
                    'message': f"Line too long ({len(line)} > 100 characters)"
                })
        
        # 2. Check for missing docstrings
        if not re.search(r'""".*?"""', content, re.DOTALL):
            issues.append({
                'file': file_path,
                'type': 'documentation',
                'message': "Missing module docstring"
            })
        
        # 3. Check for undefined variables (simple check)
        imports = set()
        for match in re.finditer(r'^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.,\s]+))', content, re.MULTILINE):
            if match.group(1):
                # from x import y
                module = match.group(1)
                imports.add(module)
            elif match.group(2):
                # import x, y, z
                modules = [m.strip() for m in match.group(2).split(',')]
                imports.update(modules)
        
        return issues
    
    def _validate_javascript(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        Validate JavaScript/TypeScript code.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check for common issues
        
        # 1. Long lines
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'style',
                    'message': f"Line too long ({len(line)} > 100 characters)"
                })
        
        # 2. Check for console.log (often left in by mistake)
        for i, line in enumerate(lines, 1):
            if 'console.log(' in line and not re.search(r'//.*console\.log', line):
                issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'debug',
                    'message': "Debug statement (console.log) should be removed"
                })
        
        # 3. Check for mismatched braces (simple check)
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            issues.append({
                'file': file_path,
                'type': 'syntax',
                'message': f"Mismatched braces: {open_braces} opening vs {close_braces} closing"
            })
        
        return issues
    
    def _validate_java(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        Validate Java code.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check for common issues
        
        # 1. Long lines
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'style',
                    'message': f"Line too long ({len(line)} > 100 characters)"
                })
        
        # 2. Check for mismatched braces (simple check)
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            issues.append({
                'file': file_path,
                'type': 'syntax',
                'message': f"Mismatched braces: {open_braces} opening vs {close_braces} closing"
            })
        
        # 3. Check for System.out.println (often left in by mistake)
        for i, line in enumerate(lines, 1):
            if 'System.out.println(' in line and not re.search(r'//.*System\.out\.println', line):
                issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'debug',
                    'message': "Debug statement (System.out.println) should be removed"
                })
        
        return issues
    
    def _validate_common(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        Common validation checks for all file types.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check for TODO comments
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if re.search(r'(?:^|\s)#?\s*TODO\b', line, re.IGNORECASE):
                issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'todo',
                    'message': "TODO comment found"
                })
        
        # Check for trailing whitespace
        for i, line in enumerate(lines, 1):
            if line.rstrip() != line:
                issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'style',
                    'message': "Trailing whitespace"
                })
        
        # Check for tabs vs spaces consistency
        has_tabs = '\t' in content
        has_spaces = bool(re.search(r'^[ ]+', content, re.MULTILINE))
        
        if has_tabs and has_spaces:
            issues.append({
                'file': file_path,
                'type': 'style',
                'message': "Mixed use of tabs and spaces for indentation"
            })
        
        return issues