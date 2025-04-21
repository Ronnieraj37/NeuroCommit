"""
Project structure analyzer.
"""
import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

class ProjectAnalyzer:
    def __init__(self, repo_path: Path):
        """
        Initialize project analyzer with repository path.
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
        self.ignored_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'dist', 'build'}
        self.code_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cs': 'csharp',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala'
        }
    
    async def analyze(self) -> Dict[str, Any]:
        """
        Analyze the project structure.
        
        Returns:
            Dictionary with project structure information
        """
        project_info = {
            'name': self.repo_path.name,
            'languages': set(),
            'file_structure': {},
            'dependencies': await self._detect_dependencies(),
            'entry_points': await self._find_entry_points(),
            'important_files': []
        }
        
        # Analyze file structure
        project_info['file_structure'] = await self._analyze_directory(self.repo_path)
        
        # Identify important files
        project_info['important_files'] = await self._identify_important_files()
        
        # Convert languages set to list for JSON serialization
        project_info['languages'] = list(project_info['languages'])
        
        return project_info
    
    async def _analyze_directory(
        self, 
        directory: Path, 
        relative_path: str = '', 
        max_depth: int = 3,
        max_files_per_dir: int = 10
    ) -> Dict[str, Any]:
        """
        Recursively analyze a directory.
        
        Args:
            directory: Directory path
            relative_path: Path relative to repository root
            max_depth: Maximum recursion depth
            max_files_per_dir: Maximum number of files to analyze per directory
            
        Returns:
            Directory analysis results
        """
        if max_depth <= 0:
            return {'type': 'directory', 'truncated': True}
        
        result = {'type': 'directory', 'contents': {}}
        
        try:
            entries = list(directory.iterdir())
        except (PermissionError, OSError):
            return {'type': 'directory', 'error': 'Access denied'}
        
        # Sort entries (directories first, then files)
        dirs = sorted([e for e in entries if e.is_dir() and e.name not in self.ignored_dirs])
        files = sorted([e for e in entries if e.is_file()])
        
        # Process directories
        for dir_path in dirs:
            dir_rel_path = os.path.join(relative_path, dir_path.name)
            result['contents'][dir_path.name] = await self._analyze_directory(
                dir_path, 
                dir_rel_path, 
                max_depth - 1,
                max_files_per_dir
            )
        
        # Process files (up to max_files_per_dir)
        file_count = min(len(files), max_files_per_dir)
        for file_path in files[:file_count]:
            file_info = await self._analyze_file(file_path, os.path.join(relative_path, file_path.name))
            if file_info:
                result['contents'][file_path.name] = file_info
        
        # Indicate if we truncated the file list
        if len(files) > max_files_per_dir:
            result['truncated_files'] = len(files) - max_files_per_dir
        
        return result
    
    async def _analyze_file(self, file_path: Path, relative_path: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a single file.
        
        Args:
            file_path: File path
            relative_path: Path relative to repository root
            
        Returns:
            File analysis results or None if file should be ignored
        """
        # Skip large files
        if file_path.stat().st_size > 1_000_000:  # 1MB
            return {'type': 'file', 'size': file_path.stat().st_size, 'too_large': True}
        
        # Get file extension
        _, ext = os.path.splitext(file_path.name.lower())
        
        file_info = {
            'type': 'file',
            'size': file_path.stat().st_size,
            'last_modified': file_path.stat().st_mtime
        }
        
        # Detect language based on extension
        if ext in self.code_extensions:
            language = self.code_extensions[ext]
            file_info['language'] = language
            
            # Add language to project languages
            # Call it as a method to satisfy mypy
            self._add_language(language)
            
            # For Python, JavaScript and TypeScript files, extract imports
            if ext in ['.py', '.js', '.ts', '.jsx', '.tsx']:
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Extract imports
                    imports = await self._extract_imports(content, ext)
                    if imports:
                        file_info['imports'] = imports
                    
                    # Extract classes and functions (basic implementation)
                    classes = await self._extract_classes(content, ext)
                    if classes:
                        file_info['classes'] = classes
                    
                    functions = await self._extract_functions(content, ext)
                    if functions:
                        file_info['functions'] = functions
                    
                except (UnicodeDecodeError, PermissionError, OSError):
                    file_info['error'] = 'Could not read file'
        
        return file_info
    
    def _add_language(self, language: str) -> None:
        """
        Add a language to the project languages set.
        """
        if hasattr(self, 'project_info'):
            self.project_info['languages'].add(language)
    
    async def _extract_imports(self, content: str, ext: str) -> List[str]:
        """
        Extract import statements from file content.
        
        Args:
            content: File content
            ext: File extension
            
        Returns:
            List of import statements
        """
        imports = []
        
        if ext == '.py':
            # Python imports
            import_patterns = [
                r'^\s*import\s+([\w.]+)',
                r'^\s*from\s+([\w.]+)\s+import'
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    imports.append(match.group(1))
        
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            # JavaScript/TypeScript imports
            import_patterns = [
                r'import.*?from\s+[\'"]([^\'"]+)[\'"]',
                r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    imports.append(match.group(1))
        
        return imports
    
    async def _extract_classes(self, content: str, ext: str) -> List[Dict[str, Any]]:
        """
        Extract class definitions from file content.
        
        Args:
            content: File content
            ext: File extension
            
        Returns:
            List of class information
        """
        classes = []
        
        if ext == '.py':
            # Python classes
            class_pattern = r'^\s*class\s+(\w+)(?:\(([^)]*)\))?:'
            
            for match in re.finditer(class_pattern, content, re.MULTILINE):
                class_name = match.group(1)
                parent_classes = []
                
                if match.group(2):
                    parent_classes = [p.strip() for p in match.group(2).split(',')]
                
                classes.append({
                    'name': class_name,
                    'parent_classes': parent_classes
                })
        
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            # JavaScript/TypeScript classes
            class_pattern = r'^\s*class\s+(\w+)(?:\s+extends\s+(\w+))?'
            
            for match in re.finditer(class_pattern, content, re.MULTILINE):
                class_name = match.group(1)
                parent_class = match.group(2)
                
                classes.append({
                    'name': class_name,
                    'parent_classes': [parent_class] if parent_class else []
                })
            
            # Also detect React components
            component_patterns = [
                r'^\s*(?:export\s+)?(?:default\s+)?function\s+(\w+)',
                r'^\s*(?:export\s+)?(?:default\s+)?const\s+(\w+)\s*=\s*(?:React\.)?(?:memo\()?(?:forwardRef\()?(?:\([^)]*\)|[^=]+)=>'
            ]
            
            for pattern in component_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    component_name = match.group(1)
                    if component_name[0].isupper():  # React components conventionally start with uppercase
                        classes.append({
                            'name': component_name,
                            'type': 'component'
                        })
        
        return classes
    
    async def _extract_functions(self, content: str, ext: str) -> List[Dict[str, Any]]:
        """
        Extract function definitions from file content.
        
        Args:
            content: File content
            ext: File extension
            
        Returns:
            List of function information
        """
        functions = []
        
        if ext == '.py':
            # Python functions
            function_pattern = r'^\s*def\s+(\w+)\s*\(([^)]*)\):'
            
            for match in re.finditer(function_pattern, content, re.MULTILINE):
                function_name = match.group(1)
                params = match.group(2).strip()
                
                # Skip private methods
                if function_name.startswith('_') and function_name != '__init__':
                    continue
                
                functions.append({
                    'name': function_name,
                    'params': params
                })
        
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            # JavaScript/TypeScript functions
            function_patterns = [
                r'^\s*function\s+(\w+)\s*\(([^)]*)\)',
                r'^\s*(?:export\s+)?(?:default\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>'
            ]
            
            for pattern in function_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    function_name = match.group(1)
                    params = match.group(2).strip()
                    
                    # Skip private methods
                    if function_name.startswith('_'):
                        continue
                    
                    functions.append({
                        'name': function_name,
                        'params': params
                    })
        
        return functions
    
    async def _detect_dependencies(self) -> Dict[str, Any]:
        """
        Detect project dependencies.
        
        Returns:
            Dictionary of detected dependencies
        """
        dependencies = {}
        
        # Check for package.json (Node.js)
        package_json_path = self.repo_path / 'package.json'
        if package_json_path.exists():
            try:
                package_data = json.loads(package_json_path.read_text(encoding='utf-8'))
                dependencies['node'] = {
                    'dependencies': package_data.get('dependencies', {}),
                    'devDependencies': package_data.get('devDependencies', {})
                }
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        
        # Check for requirements.txt (Python)
        requirements_path = self.repo_path / 'requirements.txt'
        if requirements_path.exists():
            try:
                requirements = requirements_path.read_text(encoding='utf-8').splitlines()
                dependencies['python'] = {
                    'requirements': [r.strip() for r in requirements if r.strip() and not r.startswith('#')]
                }
            except UnicodeDecodeError:
                pass
        
        # Check for setup.py (Python)
        setup_py_path = self.repo_path / 'setup.py'
        if setup_py_path.exists():
            dependencies['python'] = dependencies.get('python', {})
            dependencies['python']['has_setup_py'] = True
        
        # Check for pom.xml (Java/Maven)
        pom_xml_path = self.repo_path / 'pom.xml'
        if pom_xml_path.exists():
            dependencies['java'] = {
                'build_system': 'maven'
            }
        
        # Check for build.gradle (Java/Gradle)
        build_gradle_path = self.repo_path / 'build.gradle'
        if build_gradle_path.exists():
            dependencies['java'] = {
                'build_system': 'gradle'
            }
        
        # Check for Cargo.toml (Rust)
        cargo_toml_path = self.repo_path / 'Cargo.toml'
        if cargo_toml_path.exists():
            dependencies['rust'] = {
                'has_cargo_toml': True
            }
        
        return dependencies
    
    async def _find_entry_points(self) -> List[str]:
        """
        Find potential entry points for the application.
        
        Returns:
            List of entry point file paths
        """
        entry_points = []
        
        # Common entry point patterns
        entry_point_patterns = [
            (self.repo_path / 'main.py', 'python'),
            (self.repo_path / 'app.py', 'python'),
            (self.repo_path / 'index.js', 'javascript'),
            (self.repo_path / 'server.js', 'javascript'),
            (self.repo_path / 'src/index.js', 'javascript'),
            (self.repo_path / 'src/main.js', 'javascript'),
            (self.repo_path / 'src/App.js', 'javascript'),
            (self.repo_path / 'src/index.ts', 'typescript'),
            (self.repo_path / 'src/main.ts', 'typescript'),
            (self.repo_path / 'src/App.ts', 'typescript'),
            (self.repo_path / 'src/Main.java', 'java'),
            (self.repo_path / 'src/App.java', 'java')
        ]
        
        for path, language in entry_point_patterns:
            if path.exists() and path.is_file():
                entry_points.append(str(path.relative_to(self.repo_path)))
        
        return entry_points
    
    async def _identify_important_files(self) -> List[Dict[str, Any]]:
        """
        Identify important files in the project.
        
        Returns:
            List of important file information
        """
        important_files = []
        
        # Configuration files
        config_files = [
            '.gitignore',
            '.env',
            '.env.example',
            'docker-compose.yml',
            'Dockerfile',
            'tsconfig.json',
            'webpack.config.js',
            'babel.config.js',
            '.eslintrc.js',
            '.eslintrc.json',
            'jest.config.js',
            'pyproject.toml',
            'setup.cfg',
            'tox.ini',
            'pytest.ini'
        ]
        
        for filename in config_files:
            file_path = self.repo_path / filename
            if file_path.exists() and file_path.is_file():
                important_files.append({
                    'path': filename,
                    'type': 'config'
                })
        
        # Documentation files
        doc_files = [
            'README.md',
            'CONTRIBUTING.md',
            'CHANGELOG.md',
            'LICENSE',
            'docs/index.md'
        ]
        
        for filename in doc_files:
            file_path = self.repo_path / filename
            if file_path.exists() and file_path.is_file():
                important_files.append({
                    'path': filename,
                    'type': 'documentation'
                })
        
        # Entry points
        entry_points = await self._find_entry_points()
        for entry_point in entry_points:
            important_files.append({
                'path': entry_point,
                'type': 'entry_point'
            })
        
        return important_files