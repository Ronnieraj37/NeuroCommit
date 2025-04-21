"""
Language-agnostic code parsing for various programming languages.
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

class CodeParser:
    def __init__(self, repo_path: Path):
        """
        Initialize code parser.
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
        self.language_extensions = {
            'python': ['.py', '.pyw'],
            'javascript': ['.js', '.jsx'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java'],
            'go': ['.go'],
            'ruby': ['.rb'],
            'php': ['.php'],
            'c': ['.c', '.h'],
            'cpp': ['.cpp', '.hpp', '.cc', '.hh'],
            'csharp': ['.cs'],
            'rust': ['.rs'],
            'swift': ['.swift'],
            'kotlin': ['.kt'],
            'scala': ['.scala'],
            'solidity': ['.sol'] 
        }
        
        # Invert the mapping for quick lookups
        self.extension_to_language = {}
        for language, extensions in self.language_extensions.items():
            for ext in extensions:
                self.extension_to_language[ext] = language
    
    def get_language_from_file(self, file_path: str) -> Optional[str]:
        """
        Determine the programming language of a file based on its extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language name or None if unknown
        """
        _, ext = os.path.splitext(file_path.lower())
        return self.extension_to_language.get(ext)
    
    async def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a file and extract its structure.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File structure information
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Skip large files
        if full_path.stat().st_size > 1_000_000:  # 1MB
            return {'error': 'File too large to parse'}
        
        try:
            content = full_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return {'error': 'Unable to decode file as text'}
        
        language = self.get_language_from_file(file_path)
        if not language:
            return {'error': 'Unsupported file type'}
        
        result = {
            'language': language,
            'imports': await self.extract_imports(content, language),
            'classes': await self.extract_classes(content, language),
            'functions': await self.extract_functions(content, language),
            'variables': await self.extract_variables(content, language)
        }
        
        return result
    
    async def extract_imports(self, content: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract import statements from code.
        
        Args:
            content: Source code
            language: Programming language
            
        Returns:
            List of import information
        """
        imports = []
        
        if language == 'python':
            # Python imports
            import_patterns = [
                (r'^\s*import\s+([\w.]+)(?:\s+as\s+(\w+))?', lambda m: {'module': m.group(1), 'alias': m.group(2) or None}),
                (r'^\s*from\s+([\w.]+)\s+import\s+([\w.*,\s]+)', lambda m: {'module': m.group(1), 'symbols': [s.strip() for s in m.group(2).split(',')]})
            ]
            
            for pattern, parser in import_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    imports.append(parser(match))
        
        elif language in ['javascript', 'typescript']:
            # JavaScript/TypeScript imports
            import_patterns = [
                (r'import\s+{([^}]+)}\s+from\s+[\'"]([^\'"]+)[\'"]', 
                 lambda m: {'module': m.group(2), 'symbols': [s.strip() for s in m.group(1).split(',')]}),
                (r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]', 
                 lambda m: {'module': m.group(2), 'default': m.group(1)}),
                (r'import\s+\*\s+as\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]', 
                 lambda m: {'module': m.group(2), 'namespace': m.group(1)}),
                (r'(?:const|let|var)\s+{([^}]+)}\s+=\s+require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', 
                 lambda m: {'module': m.group(2), 'symbols': [s.strip() for s in m.group(1).split(',')]}),
                (r'(?:const|let|var)\s+(\w+)\s+=\s+require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', 
                 lambda m: {'module': m.group(2), 'default': m.group(1)})
            ]
            
            for pattern, parser in import_patterns:
                for match in re.finditer(pattern, content):
                    imports.append(parser(match))
        
        elif language == 'java':
            # Java imports
            import_pattern = r'^\s*import\s+(static\s+)?([\w.]+)(?:\.\*)?;'
            
            for match in re.finditer(import_pattern, content, re.MULTILINE):
                imports.append({
                    'static': bool(match.group(1)),
                    'package': match.group(2)
                })
        
        elif language == 'solidity':
            # Solidity imports
            import_pattern = r'import\s+[\'"]([^\'"]+)[\'"]\s*;'
            
            for match in re.finditer(import_pattern, content):
                imports.append({
                    'path': match.group(1)
                })
            
            # Also detect inheritance imports
            inherit_pattern = r'is\s+([\w,\s]+){'
            for match in re.finditer(inherit_pattern, content):
                contracts = [c.strip() for c in match.group(1).split(',')]
                for contract in contracts:
                    imports.append({
                        'contract': contract
                    })
        
        return imports
    
    async def extract_classes(self, content: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract class definitions from code.
        
        Args:
            content: Source code
            language: Programming language
            
        Returns:
            List of class information
        """
        classes = []
        
        if language == 'python':
            # Python classes
            class_pattern = r'^\s*class\s+(\w+)(?:\(([^)]*)\))?:'
            
            for match in re.finditer(class_pattern, content, re.MULTILINE):
                class_name = match.group(1)
                parent_classes = []
                
                if match.group(2):
                    parent_classes = [p.strip() for p in match.group(2).split(',')]
                
                # Find class methods
                class_start = match.end()
                class_indent = None
                methods = []
                
                # Get the line where the class is defined
                class_line_end = content.find('\n', match.start())
                if class_line_end == -1:
                    class_line_end = len(content)
                
                # Find the next line's indentation to determine class body
                next_line_match = re.search(r'^\s+', content[class_line_end+1:], re.MULTILINE)
                if next_line_match:
                    class_indent = next_line_match.group(0)
                    
                    # Extract methods using this indentation as a guide
                    method_pattern = re.compile(r'^' + class_indent + r'def\s+(\w+)\s*\(([^)]*)\):', re.MULTILINE)
                    
                    for method_match in method_pattern.finditer(content[class_line_end:]):
                        method_name = method_match.group(1)
                        params = method_match.group(2).strip()
                        
                        # Remove 'self' from params
                        if params.startswith('self'):
                            params = params[4:].strip()
                            if params.startswith(','):
                                params = params[1:].strip()
                        
                        methods.append({
                            'name': method_name,
                            'params': params
                        })
                
                classes.append({
                    'name': class_name,
                    'parent_classes': parent_classes,
                    'methods': methods
                })
        
        elif language in ['javascript', 'typescript']:
            # JavaScript/TypeScript classes
            class_pattern = r'^\s*class\s+(\w+)(?:\s+extends\s+(\w+))?'
            
            for match in re.finditer(class_pattern, content, re.MULTILINE):
                class_name = match.group(1)
                parent_class = match.group(2)
                
                # Find the opening brace
                class_start = match.end()
                brace_index = content.find('{', class_start)
                
                if brace_index != -1:
                    # Find methods in class body
                    class_body = content[brace_index:]
                    methods = []
                    
                    # Method pattern (including constructor)
                    method_patterns = [
                        r'(?:async\s+)?(?:constructor|[\w]+)\s*\(([^)]*)\)',
                        r'(?:async\s+)?(?:get|set)\s+([\w]+)\s*\(([^)]*)\)',
                        r'(?:static\s+)?(?:async\s+)?([\w]+)\s*\(([^)]*)\)'
                    ]
                    
                    # Find the closing brace of the class
                    nest_level = 1
                    class_end = brace_index + 1
                    for i in range(1, len(class_body)):
                        if class_body[i] == '{':
                            nest_level += 1
                        elif class_body[i] == '}':
                            nest_level -= 1
                            if nest_level == 0:
                                class_end = brace_index + i + 1
                                class_body = class_body[:i]
                                break
                    
                    for pattern in method_patterns:
                        for method_match in re.finditer(pattern, class_body):
                            if len(method_match.groups()) == 1:
                                # Constructor
                                methods.append({
                                    'name': 'constructor',
                                    'params': method_match.group(1).strip()
                                })
                            else:
                                # Regular method
                                method_name = method_match.group(1)
                                params = method_match.group(2).strip() if len(method_match.groups()) > 1 else ''
                                
                                methods.append({
                                    'name': method_name,
                                    'params': params
                                })
                    
                    classes.append({
                        'name': class_name,
                        'parent_classes': [parent_class] if parent_class else [],
                        'methods': methods
                    })
            
            # Also detect React components
            component_patterns = [
                (r'^\s*(?:export\s+)?(?:default\s+)?function\s+(\w+)\s*\(([^)]*)\)', 
                 lambda m: {'name': m.group(1), 'type': 'function_component', 'props': m.group(2).strip()}),
                (r'^\s*(?:export\s+)?(?:default\s+)?const\s+(\w+)\s*=\s*(?:React\.)?(?:memo\()?(?:forwardRef\()?(?:\([^)]*\)|[^=]+)=>', 
                 lambda m: {'name': m.group(1), 'type': 'arrow_component'})
            ]
            
            for pattern, parser in component_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    component_info = parser(match)
                    if component_info['name'][0].isupper():  # React components conventionally start with uppercase
                        classes.append(component_info)
        
        elif language == 'java':
            # Java classes
            class_pattern = r'(?:public|protected|private)?\s*(?:abstract|final)?\s*class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?'
            
            for match in re.finditer(class_pattern, content):
                class_name = match.group(1)
                parent_class = match.group(2)
                interfaces = []
                
                if match.group(3):
                    interfaces = [i.strip() for i in match.group(3).split(',')]
                
                classes.append({
                    'name': class_name,
                    'parent_class': parent_class,
                    'interfaces': interfaces
                })
        
        elif language == 'solidity':
            # Solidity contracts are similar to classes
            contract_pattern = r'(?:contract|library|interface)\s+(\w+)(?:\s+is\s+([\w\s,]+))?\s*{'
            
            for match in re.finditer(contract_pattern, content):
                contract_name = match.group(1)
                parent_contracts = []
                
                if match.group(2):
                    parent_contracts = [c.strip() for c in match.group(2).split(',')]
                
                # Find functions in the contract
                contract_start = match.end()
                contract_end = find_closing_brace(content, contract_start)
                contract_body = content[contract_start:contract_end]
                
                methods = []
                function_pattern = r'function\s+(\w+)\s*\(([^)]*)\)'
                for func_match in re.finditer(function_pattern, contract_body):
                    method_name = func_match.group(1)
                    params = func_match.group(2).strip()
                    
                    methods.append({
                        'name': method_name,
                        'params': params
                    })
                
                classes.append({
                    'name': contract_name,
                    'type': 'contract',
                    'parent_contracts': parent_contracts,
                    'methods': methods
                })
            
        return classes
    
    async def extract_functions(self, content: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract function definitions from code.
        
        Args:
            content: Source code
            language: Programming language
            
        Returns:
            List of function information
        """
        functions = []
        
        if language == 'python':
            # Python functions (excluding class methods)
            function_pattern = r'^\s*def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^:]+))?:'
            
            for match in re.finditer(function_pattern, content, re.MULTILINE):
                # Check if this is a method by looking at indentation
                line_start = content.rfind('\n', 0, match.start()) + 1
                indent = match.start() - line_start
                
                # If indentation is 0, it's a top-level function
                if indent == 0:
                    function_name = match.group(1)
                    params = match.group(2).strip()
                    return_type = match.group(3).strip() if match.group(3) else None
                    
                    functions.append({
                        'name': function_name,
                        'params': params,
                        'return_type': return_type
                    })
        
        elif language in ['javascript', 'typescript']:
            # JavaScript/TypeScript functions
            function_patterns = [
                (r'^\s*function\s+(\w+)\s*\(([^)]*)\)', 
                 lambda m: {'name': m.group(1), 'params': m.group(2).strip(), 'type': 'declaration'}),
                (r'^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', 
                 lambda m: {'name': m.group(1), 'params': m.group(2).strip(), 'type': 'declaration', 'exported': True}),
                (r'^\s*(?:export\s+)?(?:default\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>', 
                 lambda m: {'name': m.group(1), 'params': m.group(2).strip(), 'type': 'arrow', 'exported': True}),
                (r'^\s*(?:let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>', 
                 lambda m: {'name': m.group(1), 'params': m.group(2).strip(), 'type': 'arrow'}),
                (r'^\s*(?:export\s+)?(?:default\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?function\s*\(([^)]*)\)', 
                 lambda m: {'name': m.group(1), 'params': m.group(2).strip(), 'type': 'expression', 'exported': True})
            ]
            
            for pattern, parser in function_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    # Skip if this matches a React component (first letter uppercase)
                    function_name = match.group(1)
                    if not function_name[0].isupper():
                        functions.append(parser(match))
        
        elif language == 'java':
            # Java methods outside of classes are not valid, so we don't extract them
            pass
        
        elif language == 'solidity':
            # Solidity functions
            function_pattern = r'function\s+(\w+)\s*\(([^)]*)\)(?:\s+(?:external|public|internal|private))?\s*(?:(?:pure|view|payable))?\s*(?:returns\s*\([^)]*\))?\s*{'
            
            for match in re.finditer(function_pattern, content):
                function_name = match.group(1)
                params = match.group(2).strip()
                
                functions.append({
                    'name': function_name,
                    'params': params
                })
        
        return functions
    
    async def extract_variables(self, content: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract global/important variable definitions from code.
        
        Args:
            content: Source code
            language: Programming language
            
        Returns:
            List of variable information
        """
        variables = []
        
        if language == 'python':
            # Python global variables (simplified, assumes constants are UPPERCASE)
            variable_pattern = r'^([A-Z][A-Z0-9_]*)\s*=\s*(.+?)$'
            
            for match in re.finditer(variable_pattern, content, re.MULTILINE):
                var_name = match.group(1)
                var_value = match.group(2).strip()
                
                variables.append({
                    'name': var_name,
                    'value': var_value,
                    'type': 'constant'
                })
        
        elif language in ['javascript', 'typescript']:
            # JavaScript/TypeScript constants and important variables
            variable_patterns = [
                (r'^\s*(?:export\s+)?const\s+([A-Z][A-Z0-9_]*)\s*=\s*(.+?)$', 
                 lambda m: {'name': m.group(1), 'value': m.group(2).strip(), 'type': 'constant'}),
                (r'^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(.+?)$', 
                 lambda m: {'name': m.group(1), 'value': m.group(2).strip(), 'type': 'constant'}),
                (r'^\s*(?:export\s+)?let\s+(\w+)\s*=\s*(.+?)$', 
                 lambda m: {'name': m.group(1), 'value': m.group(2).strip(), 'type': 'variable'}),
                (r'^\s*(?:export\s+)?var\s+(\w+)\s*=\s*(.+?)$', 
                 lambda m: {'name': m.group(1), 'value': m.group(2).strip(), 'type': 'variable'})
            ]
            
            for pattern, parser in variable_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    variables.append(parser(match))
        
        elif language == 'java':
            # Java constants and fields (simplified)
            variable_pattern = r'^\s*(?:public|private|protected)?\s*(?:static\s+final|final\s+static)?\s+(\w+)\s+([A-Z][A-Z0-9_]*)\s*=\s*(.+?);'
            
            for match in re.finditer(variable_pattern, content, re.MULTILINE):
                var_type = match.group(1)
                var_name = match.group(2)
                var_value = match.group(3).strip()
                
                variables.append({
                    'name': var_name,
                    'type': 'constant',
                    'data_type': var_type,
                    'value': var_value
                })
        
        elif language == 'solidity':
            # Solidity state variables
            variable_pattern = r'(uint|int|bool|address|string|bytes\d*)\s+(public|private|internal)?\s*(\w+)\s*(?:=\s*([^;]+))?;'
            
            for match in re.finditer(variable_pattern, content):
                var_type = match.group(1)
                visibility = match.group(2) or 'internal'  # Default to internal if not specified
                var_name = match.group(3)
                var_value = match.group(4)
                
                variables.append({
                    'name': var_name,
                    'type': var_type,
                    'visibility': visibility,
                    'value': var_value
                })
            
        return variables
    
    async def find_function_location(self, content: str, function_name: str, language: str) -> Optional[Tuple[int, int]]:
        """
        Find the start and end location of a function in the code.
        
        Args:
            content: Source code
            function_name: Name of the function to find
            language: Programming language
            
        Returns:
            Tuple of (start, end) positions or None if not found
        """
        if language == 'python':
            # Python function
            pattern = rf'def\s+{function_name}\s*\([^)]*\)(?:\s*->.*?)?:'
            match = re.search(pattern, content)
            
            if not match:
                return None
            
            start = match.start()
            
            # Find the end of the function by tracking indentation
            lines = content[match.end():].split('\n')
            
            # Get the indentation of the function body
            if not lines:
                return start, len(content)
            
            # Find first non-empty line to get indentation
            body_indent = None
            for line in lines:
                stripped = line.lstrip()
                if stripped:
                    body_indent = len(line) - len(stripped)
                    break
            
            if body_indent is None:
                return start, len(content)
            
            # Find the first line with same or less indentation
            end = match.end()
            for i, line in enumerate(lines):
                stripped = line.lstrip()
                if stripped and (len(line) - len(stripped)) <= body_indent:
                    end += sum(len(l) + 1 for l in lines[:i])
                    break
                end += len(line) + 1
            
            return start, end
        
        elif language in ['javascript', 'typescript']:
            # JavaScript/TypeScript function
            patterns = [
                rf'function\s+{function_name}\s*\([^)]*\)\s*{{',
                rf'const\s+{function_name}\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*{{',
                rf'const\s+{function_name}\s*=\s*function\s*\([^)]*\)\s*{{'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    start = match.start()
                    
                    # Find the opening brace
                    opening_brace = content.find('{', start)
                    if opening_brace == -1:
                        return None
                    
                    # Find the matching closing brace
                    nest_level = 1
                    for i in range(opening_brace + 1, len(content)):
                        if content[i] == '{':
                            nest_level += 1
                        elif content[i] == '}':
                            nest_level -= 1
                            if nest_level == 0:
                                return start, i + 1
                    
                    return start, len(content)
            
            return None
        
        elif language == 'java':
            # Java method
            pattern = rf'(?:public|private|protected)?\s*(?:static\s+)?\w+\s+{function_name}\s*\([^)]*\)'
            match = re.search(pattern, content)
            
            if not match:
                return None
                
            start = match.start()
            
            # Find opening brace
            opening_brace = content.find('{', start)
            if opening_brace == -1:
                return None
                
            # Find matching closing brace
            nest_level = 1
            for i in range(opening_brace + 1, len(content)):
                if content[i] == '{':
                    nest_level += 1
                elif content[i] == '}':
                    nest_level -= 1
                    if nest_level == 0:
                        return start, i + 1
            
            return start, len(content)
        
        return None
    
    async def find_class_by_name(self, file_path: str, class_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a class by name in a file.
        
        Args:
            file_path: Path to the file
            class_name: Name of the class to find
            
        Returns:
            Class information or None if not found
        """
        try:
            parsed_file = await self.parse_file(file_path)
            
            for cls in parsed_file.get('classes', []):
                if cls['name'] == class_name:
                    return cls
                    
            return None
        except Exception:
            return None
    
    async def find_function_by_name(self, file_path: str, function_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a function by name in a file.
        
        Args:
            file_path: Path to the file
            function_name: Name of the function to find
            
        Returns:
            Function information or None if not found
        """
        try:
            parsed_file = await self.parse_file(file_path)
            
            for func in parsed_file.get('functions', []):
                if func['name'] == function_name:
                    return func
                    
            # Also check class methods
            for cls in parsed_file.get('classes', []):
                for method in cls.get('methods', []):
                    if method['name'] == function_name:
                        method['class_name'] = cls['name']
                        return method
                    
            return None
        except Exception:
            return None


    def find_closing_brace(content: str, start_index: int) -> int:
        """Find the position of the closing brace that matches the opening brace."""
        count = 1
        for i in range(start_index, len(content)):
            if content[i] == '{':
                count += 1
            elif content[i] == '}':
                count -= 1
                if count == 0:
                    return i
        return len(content)
