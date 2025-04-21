"""
Code editor for programmatic file modifications.
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)
class CodeEditor:
    def __init__(self, repo_path: Path):
        """
        Initialize code editor with repository path.
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
    
    async def create_file(self, file_path: str, content: str) -> None:
        """
        Create a new file with the given content.
        
        Args:
            file_path: Path to the file
            content: File content
        """
        full_path = self.repo_path / file_path
        
        # Create parent directories if they don't exist
        os.makedirs(full_path.parent, exist_ok=True)
        
        # Write content to file
        full_path.write_text(content, encoding="utf-8")
    
    async def read_file(self, file_path: str) -> str:
        """
        Read the content of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return full_path.read_text(encoding="utf-8")
    
    async def add_method_to_class(self, file_path: str, class_name: str, method_code: str) -> None:
        """
        Add a method to a class.
        
        Args:
            file_path: Path to the file
            class_name: Name of the class
            method_code: Method code to add
        """
        content = await self.read_file(file_path)
        
        # Get file extension
        ext = os.path.splitext(file_path)[1]
        
        if ext in [".py", ".pyw"]:
            # Python class
            pattern = rf'class\s+{class_name}(?:\([^)]*\))?\s*:'
            class_match = re.search(pattern, content)
            
            if not class_match:
                raise ValueError(f"Class '{class_name}' not found in {file_path}")
            
            class_start = class_match.end()
            
            # Find the indentation level of the class body
            next_line_match = re.search(r'(\n\s+)', content[class_start:])
            if not next_line_match:
                raise ValueError(f"Could not determine indentation level in {file_path}")
            
            indentation = next_line_match.group(1).replace('\n', '')
            
            # Find where to insert the method (end of class)
            next_class_match = re.search(r'\nclass\s+', content[class_start:])
            next_top_level_match = re.search(r'\n[a-zA-Z]', content[class_start:])
            
            if next_class_match and (not next_top_level_match or 
                                    next_class_match.start() < next_top_level_match.start()):
                class_end = class_start + next_class_match.start()
            elif next_top_level_match:
                class_end = class_start + next_top_level_match.start()
            else:
                class_end = len(content)
            
            # Format method code with proper indentation
            method_lines = method_code.strip().split('\n')
            indented_method = '\n'.join([f"{indentation}{line}" for line in method_lines])
            
            # Insert method at the end of the class
            new_content = (
                content[:class_end] + 
                f"\n\n{indentation}{method_lines[0]}\n" + 
                '\n'.join([f"{indentation}{line}" for line in method_lines[1:]]) + 
                content[class_end:]
            )
            
            # Write back to file
            full_path = self.repo_path / file_path
            full_path.write_text(new_content, encoding="utf-8")
        
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            # JavaScript/TypeScript class
            # Look for class declaration
            pattern = rf'class\s+{class_name}'
            class_match = re.search(pattern, content)
            
            if not class_match:
                # Try looking for React functional component
                pattern = rf'(?:export\s+)?(?:default\s+)?(?:const|function)\s+{class_name}\s*='
                class_match = re.search(pattern, content)
                
                if not class_match:
                    raise ValueError(f"Class or component '{class_name}' not found in {file_path}")
            
            # Find the opening brace
            brace_index = content.find('{', class_match.end())
            if brace_index == -1:
                raise ValueError(f"Could not find opening brace for class/component '{class_name}' in {file_path}")
            
            # Find the matching closing brace
            nest_level = 1
            for i in range(brace_index + 1, len(content)):
                if content[i] == '{':
                    nest_level += 1
                elif content[i] == '}':
                    nest_level -= 1
                    if nest_level == 0:
                        # Found the end of the class
                        class_end = i
                        break
            else:
                raise ValueError(f"Could not find closing brace for class/component '{class_name}' in {file_path}")
            
            # Insert method before the closing brace
            new_content = (
                content[:class_end] + 
                "\n\n  " + method_code.strip().replace('\n', '\n  ') + 
                "\n\n" + content[class_end:]
            )
            
            # Write back to file
            full_path = self.repo_path / file_path
            full_path.write_text(new_content, encoding="utf-8")
        
        elif ext == ".sol":
            # Solidity contract
            pattern = rf'(?:contract|library|interface)\s+{class_name}'
            contract_match = re.search(pattern, content)
            
            if not contract_match:
                raise ValueError(f"Contract '{class_name}' not found in {file_path}")
            
            # Find the opening brace
            brace_index = content.find('{', contract_match.end())
            if brace_index == -1:
                raise ValueError(f"Could not find opening brace for contract '{class_name}' in {file_path}")
            
            # Find the matching closing brace
            nest_level = 1
            for i in range(brace_index + 1, len(content)):
                if content[i] == '{':
                    nest_level += 1
                elif content[i] == '}':
                    nest_level -= 1
                    if nest_level == 0:
                        # Found the end of the contract
                        contract_end = i
                        break
            else:
                raise ValueError(f"Could not find closing brace for contract '{class_name}' in {file_path}")
            
            # Insert method before the closing brace
            new_content = (
                content[:contract_end] + 
                "\n    " + method_code.strip().replace('\n', '\n    ') + 
                "\n" + content[contract_end:]
            )
            
            # Write back to file
            full_path = self.repo_path / file_path
            full_path.write_text(new_content, encoding="utf-8")
        
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    # Update this method in src/editor/code_editor.py
    async def replace_code(self, file_path: str, pattern: str, replacement: str) -> None:
        """
        Replace code that matches a pattern.
        
        Args:
            file_path: Path to the file
            pattern: Code pattern to replace
            replacement: Replacement code
        """
        content = await self.read_file(file_path)
        
        # Escape special regex characters in the pattern
        escaped_pattern = re.escape(pattern)
        
        # Replace with the new code
        new_content = re.sub(escaped_pattern, replacement, content)
        
        if new_content == content:
            # Instead of raising an error, append the code if pattern not found
            logger.warning(f"Pattern not found in {file_path}, appending the new code instead")
            new_content = content + "\n\n" + replacement
        
        # Write back to file
        full_path = self.repo_path / file_path
        full_path.write_text(new_content, encoding="utf-8")
    
    async def insert_code(self, file_path: str, location: str, code: str) -> None:
        """
        Insert code at a specific location.
        
        Args:
            file_path: Path to the file
            location: Code location identifier
            code: Code to insert
        """
        content = await self.read_file(file_path)
        
        # Escape special regex characters in the location
        escaped_location = re.escape(location)
        
        # Find the location
        location_match = re.search(escaped_location, content)
        if not location_match:
            raise ValueError(f"Location not found in {file_path}")
        
        insertion_point = location_match.end()
        
        # Insert code at the location
        new_content = content[:insertion_point] + '\n' + code + content[insertion_point:]
        
        # Write back to file
        full_path = self.repo_path / file_path
        full_path.write_text(new_content, encoding="utf-8")
    
    async def add_import(self, file_path: str, import_statement: str) -> None:
        """
        Add an import statement to a file.
        
        Args:
            file_path: Path to the file
            import_statement: Import statement to add
        """
        content = await self.read_file(file_path)
        
        # Get file extension
        ext = os.path.splitext(file_path)[1]
        
        # Remove any leading/trailing whitespace and ensure newline at end
        import_statement = import_statement.strip()
        if not import_statement.endswith('\n'):
            import_statement += '\n'
        
        if ext in [".py", ".pyw"]:
            # Python file
            
            # Check if import already exists
            if import_statement in content:
                return
            
            # Find the last import statement
            import_matches = list(re.finditer(r'^(import|from)\s+', content, re.MULTILINE))
            
            if import_matches:
                # Insert after the last import
                last_match = import_matches[-1]
                end_of_line = content.find('\n', last_match.start())
                if end_of_line == -1:
                    end_of_line = len(content)
                
                new_content = content[:end_of_line + 1] + import_statement + content[end_of_line + 1:]
            else:
                # Insert at the beginning of the file
                new_content = import_statement + content
            
            # Write back to file
            full_path = self.repo_path / file_path
            full_path.write_text(new_content, encoding="utf-8")
        
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            # JavaScript/TypeScript file
            
            # Check if import already exists
            if import_statement in content:
                return
            
            # Find the last import statement
            import_matches = list(re.finditer(r'^(import|const|require)\s+', content, re.MULTILINE))
            
            if import_matches:
                # Insert after the last import
                last_match = import_matches[-1]
                end_of_line = content.find('\n', last_match.start())
                if end_of_line == -1:
                    end_of_line = len(content)
                
                new_content = content[:end_of_line + 1] + import_statement + content[end_of_line + 1:]
            else:
                # Insert at the beginning of the file
                new_content = import_statement + content
            
            # Write back to file
            full_path = self.repo_path / file_path
            full_path.write_text(new_content, encoding="utf-8")
        
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    async def modify_function(
        self, 
        file_path: str, 
        function_name: str, 
        new_implementation: str
    ) -> None:
        """
        Modify a function implementation.
        
        Args:
            file_path: Path to the file
            function_name: Name of the function
            new_implementation: New function implementation
        """
        content = await self.read_file(file_path)
        
        # Get file extension
        ext = os.path.splitext(file_path)[1]
        
        if ext in [".py", ".pyw"]:
            # Python function
            pattern = rf'def\s+{function_name}\s*\([^)]*\)\s*(?:->.*?)?:'
            func_match = re.search(pattern, content)
            
            if not func_match:
                raise ValueError(f"Function '{function_name}' not found in {file_path}")
            
            func_start = func_match.start()
            
            # Find the end of the function
            # This is complex in Python, we'll use indentation to find it
            func_def_line = content.count('\n', 0, func_start)
            lines = content.split('\n')
            
            # Get the indentation of the function definition
            func_def_indent = len(lines[func_def_line]) - len(lines[func_def_line].lstrip())
            
            # Find the first line with same or less indentation after the function definition
            func_end_line = func_def_line
            for i in range(func_def_line + 1, len(lines)):
                line = lines[i]
                if line.strip() and (len(line) - len(line.lstrip())) <= func_def_indent:
                    func_end_line = i - 1
                    break
            else:
                func_end_line = len(lines) - 1
            
            # Reconstruct the content with the new function implementation
            func_end = sum(len(lines[j]) + 1 for j in range(func_def_line + 1, func_end_line + 1)) + func_match.end()
            
            # Format indentation for new implementation
            indentation = ' ' * (func_def_indent + 4)  # 4 spaces for standard Python indentation
            indented_impl = '\n'.join(indentation + line for line in new_implementation.strip().split('\n'))
            
            new_content = content[:func_match.end()] + '\n' + indented_impl + content[func_end:]
            
            # Write back to file
            full_path = self.repo_path / file_path
            full_path.write_text(new_content, encoding="utf-8")
            
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            # JavaScript/TypeScript function
            patterns = [
                rf'function\s+{function_name}\s*\([^)]*\)\s*{{',  # function declaration
                rf'const\s+{function_name}\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*{{',  # arrow function
                rf'const\s+{function_name}\s*=\s*function\s*\([^)]*\)\s*{{'  # function expression
            ]
            
            for pattern in patterns:
                func_match = re.search(pattern, content)
                if func_match:
                    break
            else:
                raise ValueError(f"Function '{function_name}' not found in {file_path}")
            
            # Find the opening brace
            brace_index = content.find('{', func_match.start())
            
            # Find the matching closing brace
            nest_level = 1
            for i in range(brace_index + 1, len(content)):
                if content[i] == '{':
                    nest_level += 1
                elif content[i] == '}':
                    nest_level -= 1
                    if nest_level == 0:
                        # Found the end of the function
                        func_end = i + 1
                        break
            else:
                raise ValueError(f"Could not find closing brace for function '{function_name}' in {file_path}")
            
            # Replace the function body
            new_content = content[:brace_index + 1] + '\n  ' + new_implementation.strip().replace('\n', '\n  ') + '\n' + content[func_end - 1:]
            
            # Write back to file
            full_path = self.repo_path / file_path
            full_path.write_text(new_content, encoding="utf-8")
        
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    async def find_function_by_name(self, file_path: str, function_name: str) -> Tuple[int, int]:
        """
        Find the start and end position of a function in a file.
        
        Args:
            file_path: Path to the file
            function_name: Name of the function
            
        Returns:
            Tuple of (start_position, end_position)
        """
        content = await self.read_file(file_path)
        
        # Get file extension
        ext = os.path.splitext(file_path)[1]
        
        if ext in [".py", ".pyw"]:
            # Python function
            pattern = rf'def\s+{function_name}\s*\([^)]*\)\s*(?:->.*?)?:'
            func_match = re.search(pattern, content)
            
            if not func_match:
                raise ValueError(f"Function '{function_name}' not found in {file_path}")
            
            func_start = func_match.start()
            
            # Find the end of the function using indentation
            func_def_line = content.count('\n', 0, func_start)
            lines = content.split('\n')
            
            # Get the indentation of the function definition
            func_def_indent = len(lines[func_def_line]) - len(lines[func_def_line].lstrip())
            
            # Find the first line with same or less indentation after the function definition
            func_end_line = func_def_line
            for i in range(func_def_line + 1, len(lines)):
                line = lines[i]
                if line.strip() and len(line) - len(line.lstrip()) <= func_def_indent:
                    func_end_line = i - 1
                    break
            else:
                func_end_line = len(lines) - 1
            
            func_end = sum(len(lines[j]) + 1 for j in range(0, func_end_line + 1))
            
            return func_start, func_end
        
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            # JavaScript/TypeScript function
            patterns = [
                rf'function\s+{function_name}\s*\([^)]*\)\s*{{',  # function declaration
                rf'const\s+{function_name}\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*{{',  # arrow function
                rf'const\s+{function_name}\s*=\s*function\s*\([^)]*\)\s*{{'  # function expression
            ]
            
            for pattern in patterns:
                func_match = re.search(pattern, content)
                if func_match:
                    break
            else:
                raise ValueError(f"Function '{function_name}' not found in {file_path}")
            
            func_start = func_match.start()
            
            # Find the opening brace
            brace_index = content.find('{', func_start)
            
            # Find the matching closing brace
            nest_level = 1
            for i in range(brace_index + 1, len(content)):
                if content[i] == '{':
                    nest_level += 1
                elif content[i] == '}':
                    nest_level -= 1
                    if nest_level == 0:
                        # Found the end of the function
                        func_end = i + 1
                        break
            else:
                raise ValueError(f"Could not find closing brace for function '{function_name}' in {file_path}")
            
            return func_start, func_end
        
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    async def find_class_by_name(self, file_path: str, class_name: str) -> Tuple[int, int]:
        """
        Find the start and end position of a class in a file.
        
        Args:
            file_path: Path to the file
            class_name: Name of the class
            
        Returns:
            Tuple of (start_position, end_position)
        """
        content = await self.read_file(file_path)
        
        # Get file extension
        ext = os.path.splitext(file_path)[1]
        
        if ext in [".py", ".pyw"]:
            # Python class
            pattern = rf'class\s+{class_name}(?:\([^)]*\))?\s*:'
            class_match = re.search(pattern, content)
            
            if not class_match:
                raise ValueError(f"Class '{class_name}' not found in {file_path}")
            
            class_start = class_match.start()
            
            # Find the end of the class using indentation
            class_def_line = content.count('\n', 0, class_start)
            lines = content.split('\n')
            
            # Get the indentation of the class definition
            class_def_indent = len(lines[class_def_line]) - len(lines[class_def_line].lstrip())
            
            # Find the first line with same or less indentation after the class definition
            class_end_line = class_def_line
            for i in range(class_def_line + 1, len(lines)):
                line = lines[i]
                if line.strip() and len(line) - len(line.lstrip()) <= class_def_indent:
                    class_end_line = i - 1
                    break
            else:
                class_end_line = len(lines) - 1
            
            class_end = sum(len(lines[j]) + 1 for j in range(0, class_end_line + 1))
            
            return class_start, class_end
        
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            # JavaScript/TypeScript class
            pattern = rf'class\s+{class_name}'
            class_match = re.search(pattern, content)
            
            if not class_match:
                # Try looking for React functional component
                pattern = rf'(?:export\s+)?(?:default\s+)?(?:const|function)\s+{class_name}\s*='
                class_match = re.search(pattern, content)
                
                if not class_match:
                    raise ValueError(f"Class or component '{class_name}' not found in {file_path}")
            
            class_start = class_match.start()
            
            # Find the opening brace
            brace_index = content.find('{', class_start)
            
            # Find the matching closing brace
            nest_level = 1
            for i in range(brace_index + 1, len(content)):
                if content[i] == '{':
                    nest_level += 1
                elif content[i] == '}':
                    nest_level -= 1
                    if nest_level == 0:
                        # Found the end of the class
                        class_end = i + 1
                        break
            else:
                raise ValueError(f"Could not find closing brace for class '{class_name}' in {file_path}")
            
            return class_start, class_end
        
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    async def delete_file(self, file_path: str) -> None:
        """
        Delete a file.
        
        Args:
            file_path: Path to the file
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        os.remove(full_path)
    
    async def rename_file(self, old_path: str, new_path: str) -> None:
        """
        Rename a file.
        
        Args:
            old_path: Original file path
            new_path: New file path
        """
        old_full_path = self.repo_path / old_path
        new_full_path = self.repo_path / new_path
        
        if not old_full_path.exists():
            raise FileNotFoundError(f"File not found: {old_path}")
        
        # Create parent directories for new path if they don't exist
        os.makedirs(new_full_path.parent, exist_ok=True)
        
        # Rename the file
        os.rename(old_full_path, new_full_path)
    
    async def append_to_file(self, file_path: str, content: str) -> None:
        """
        Append content to the end of a file.
        
        Args:
            file_path: Path to the file
            content: Content to append
        """
        full_path = self.repo_path / file_path
        
        # Create file if it doesn't exist
        if not full_path.exists():
            await self.create_file(file_path, content)
            return
        
        # Read existing content
        existing_content = await self.read_file(file_path)
        
        # Append new content with a newline if needed
        if existing_content and not existing_content.endswith('\n'):
            new_content = existing_content + '\n' + content
        else:
            new_content = existing_content + content
        
        # Write back to file
        full_path.write_text(new_content, encoding="utf-8")
    
    async def insert_at_line(self, file_path: str, line_number: int, content: str) -> None:
        """
        Insert content at a specific line number.
        
        Args:
            file_path: Path to the file
            line_number: Line number (1-based)
            content: Content to insert
        """
        if line_number < 1:
            raise ValueError("Line number must be at least 1")
        
        # Read file content
        file_content = await self.read_file(file_path)
        lines = file_content.split('\n')
        
        # Check if line number is valid
        if line_number > len(lines) + 1:
            raise ValueError(f"Line number {line_number} is out of range (max: {len(lines) + 1})")
        
        # Insert content at the specified line
        lines.insert(line_number - 1, content)
        
        # Write back to file
        new_content = '\n'.join(lines)
        full_path = self.repo_path / file_path
        full_path.write_text(new_content, encoding="utf-8")
    
    async def format_code(self, file_path: str) -> None:
        """
        Format code according to language-specific conventions.
        
        Args:
            file_path: Path to the file
        """
        # Get file extension
        ext = os.path.splitext(file_path)[1]
        
        try:
            # Try to use external formatters if available
            
            if ext in [".py", ".pyw"]:
                # Use black for Python formatting
                import subprocess
                
                proc = subprocess.run(
                    ["black", str(self.repo_path / file_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                
                if proc.returncode != 0:
                    # Fall back to basic indentation fixing
                    await self._basic_format(file_path)
            
            elif ext in [".js", ".jsx", ".ts", ".tsx"]:
                # Use prettier for JavaScript/TypeScript formatting
                import subprocess
                
                proc = subprocess.run(
                    ["npx", "prettier", "--write", str(self.repo_path / file_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                
                if proc.returncode != 0:
                    # Fall back to basic indentation fixing
                    await self._basic_format(file_path)
            
            else:
                # For other languages, just do basic formatting
                await self._basic_format(file_path)
                
        except (ImportError, FileNotFoundError):
            # If external tools are not available, fall back to basic formatting
            await self._basic_format(file_path)
    
    async def _basic_format(self, file_path: str) -> None:
        """
        Basic code formatting (fix indentation, trailing whitespace).
        
        Args:
            file_path: Path to the file
        """
        content = await self.read_file(file_path)
        lines = content.split('\n')
        
        # Remove trailing whitespace
        clean_lines = [line.rstrip() for line in lines]
        
        # Write back to file
        new_content = '\n'.join(clean_lines)
        full_path = self.repo_path / file_path
        full_path.write_text(new_content, encoding="utf-8")

    async def append_to_file(self, file_path: str, content: str) -> None:
        """
        Append content to the end of a file.
        
        Args:
            file_path: Path to the file
            content: Content to append
        """
        full_path = self.repo_path / file_path
        
        # Create file if it doesn't exist
        if not full_path.exists():
            await self.create_file(file_path, content)
            return
        
        # Read existing content
        existing_content = await self.read_file(file_path)
        
        # Append new content with a newline if needed
        if existing_content and not existing_content.endswith('\n'):
            new_content = existing_content + '\n' + content
        else:
            new_content = existing_content + content
        
        # Write back to file
        full_path.write_text(new_content, encoding="utf-8")