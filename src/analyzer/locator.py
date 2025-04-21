"""
Locates where code changes should be made in a project.
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

from src.analyzer.code_parser import CodeParser
from src.analyzer.project import ProjectAnalyzer

class CodeLocator:
    def __init__(self, repo_path: Path):
        """
        Initialize code locator.
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
        self.code_parser = CodeParser(repo_path)
        self.project_analyzer = ProjectAnalyzer(repo_path)
    
    async def find_suitable_locations(self, feature_description: str) -> Dict[str, Any]:
        """
        Find suitable locations for implementing a feature.
        
        Args:
            feature_description: Description of the feature to implement
            
        Returns:
            Dictionary with suitable locations information
        """
        # Analyze project structure
        project_structure = await self.project_analyzer.analyze()
        
        # Extract important keywords from the feature description
        keywords = self._extract_keywords(feature_description)
        
        # Find files that match the keywords
        matching_files = await self._find_matching_files(keywords, project_structure)
        
        # Find locations within files for feature implementation
        locations = await self._find_specific_locations(matching_files, keywords, feature_description)
        
        return {
            'matching_files': matching_files,
            'specific_locations': locations
        }
    
    def _extract_keywords(self, feature_description: str) -> List[str]:
        """
        Extract important keywords from the feature description.
        
        Args:
            feature_description: Description of the feature to implement
            
        Returns:
            List of keywords
        """
        # Simple keyword extraction (could be improved with NLP)
        words = re.findall(r'\b\w+\b', feature_description.lower())
        
        # Filter out common stop words
        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'in', 'on', 'to', 'with',
            'for', 'of', 'at', 'by', 'it', 'be', 'is', 'are', 'was', 'were',
            'has', 'have', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'can', 'could', 'may', 'might', 'feature', 'implement', 'add', 'create',
            'update', 'change', 'modify'
        }
        
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Remove duplicates while preserving order
        unique_keywords = []
        seen = set()
        for keyword in keywords:
            if keyword not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword)
        
        return unique_keywords
    
    async def _find_matching_files(self, keywords: List[str], project_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find files that match the keywords.
        
        Args:
            keywords: List of keywords
            project_structure: Project structure information
            
        Returns:
            List of matching file information
        """
        matching_files = []
        
        # Get all code files in the project
        code_files = self._collect_code_files(project_structure['file_structure'])
        
        # Get entry points from project structure
        entry_points = set(file_info['path'] for file_info in project_structure.get('important_files', []) 
                         if file_info.get('type') == 'entry_point')
        
        # Check each file for keyword matches
        for file_path in code_files:
            try:
                content = (self.repo_path / file_path).read_text(encoding='utf-8')
                
                # Calculate a score based on keyword matches
                score = 0
                match_count = 0
                
                for keyword in keywords:
                    pattern = rf'\b{re.escape(keyword)}\b'
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    match_count += len(matches)
                
                # Entry points get a bonus
                is_entry_point = file_path in entry_points
                if is_entry_point:
                    score += 5
                
                # File name match bonus
                for keyword in keywords:
                    if keyword.lower() in file_path.lower():
                        score += 3
                
                # Match count contributes to score
                score += min(match_count, 10)  # Cap the contribution to avoid outliers
                
                # Add to matching files if there's any match
                if score > 0:
                    language = self.code_parser.get_language_from_file(file_path)
                    
                    matching_files.append({
                        'path': file_path,
                        'score': score,
                        'is_entry_point': is_entry_point,
                        'language': language
                    })
            
            except (UnicodeDecodeError, IOError):
                # Skip files that can't be read
                continue
        
        # Sort by score (descending)
        matching_files.sort(key=lambda x: x['score'], reverse=True)
        
        return matching_files[:10]  # Return top 10 matches
    
    def _collect_code_files(self, file_structure: Dict[str, Any], current_path: str = '') -> List[str]:
        """
        Recursively collect code files from file structure.
        
        Args:
            file_structure: File structure dictionary
            current_path: Current path prefix
            
        Returns:
            List of code file paths
        """
        code_files = []
        
        if file_structure.get('type') != 'directory':
            return code_files
        
        for name, info in file_structure.get('contents', {}).items():
            path = os.path.join(current_path, name)
            
            if info.get('type') == 'file':
                # Check if it's a code file (has a language)
                if 'language' in info and not info.get('too_large', False):
                    code_files.append(path)
            
            elif info.get('type') == 'directory':
                # Recursively collect files from subdirectories
                code_files.extend(self._collect_code_files(info, path))
        
        return code_files
    
    async def _find_specific_locations(
        self,
        matching_files: List[Dict[str, Any]],
        keywords: List[str],
        feature_description: str
    ) -> List[Dict[str, Any]]:
        """
        Find specific locations in files for feature implementation.
        
        Args:
            matching_files: List of matching file information
            keywords: List of keywords
            feature_description: Description of the feature to implement
            
        Returns:
            List of specific location information
        """
        locations = []
        
        for file_info in matching_files[:5]:  # Check top 5 matching files
            file_path = file_info['path']
            language = file_info['language']
            
            try:
                content = (self.repo_path / file_path).read_text(encoding='utf-8')
                
                # Parse the file to get structure
                parsed_file = await self.code_parser.parse_file(file_path)
                
                # Find suitable classes and functions
                for cls in parsed_file.get('classes', []):
                    class_name = cls['name']
                    
                    # Calculate class match score
                    class_score = self._calculate_name_match_score(class_name, keywords)
                    
                    if class_score > 0:
                        locations.append({
                            'type': 'class',
                            'file_path': file_path,
                            'class_name': class_name,
                            'score': class_score,
                            'recommendation': 'Add method to class'
                        })
                
                for func in parsed_file.get('functions', []):
                    function_name = func['name']
                    
                    # Calculate function match score
                    function_score = self._calculate_name_match_score(function_name, keywords)
                    
                    if function_score > 0:
                        locations.append({
                            'type': 'function',
                            'file_path': file_path,
                            'function_name': function_name,
                            'score': function_score,
                            'recommendation': 'Modify function'
                        })
                
                # If no specific locations found, recommend creating a new function
                if not any(loc['file_path'] == file_path for loc in locations):
                    locations.append({
                        'type': 'file',
                        'file_path': file_path,
                        'score': file_info['score'],
                        'recommendation': 'Create new function in file'
                    })
            
            except (UnicodeDecodeError, IOError, Exception) as e:
                # Skip files that cause errors
                continue
        
        # Sort by score (descending)
        locations.sort(key=lambda x: x['score'], reverse=True)
        
        # If no locations found, recommend creating a new file
        if not locations:
            # Determine the best language based on project structure
            default_language = self._determine_default_language(matching_files)
            
            # Recommend creating a new file in a suitable directory
            suitable_dir = self._find_suitable_directory()
            
            locations.append({
                'type': 'new_file',
                'directory': suitable_dir,
                'language': default_language,
                'recommendation': f'Create new file in {suitable_dir}'
            })
        
        return locations
    
    def _calculate_name_match_score(self, name: str, keywords: List[str]) -> int:
        """
        Calculate a match score for a name based on keywords.
        
        Args:
            name: Name to check
            keywords: List of keywords
            
        Returns:
            Match score
        """
        score = 0
        
        # Split camelCase and snake_case names
        name_parts = re.findall(r'[A-Z][a-z]*|[a-z]+', name)
        name_words = [part.lower() for part in name_parts]
        
        # Add score for each keyword match
        for keyword in keywords:
            if keyword.lower() in name.lower():
                score += 3
            
            for word in name_words:
                if keyword.lower() == word.lower():
                    score += 2
        
        return score
    
    def _determine_default_language(self, matching_files: List[Dict[str, Any]]) -> str:
        """
        Determine the default language for a new file based on matching files.
        
        Args:
            matching_files: List of matching file information
            
        Returns:
            Default language
        """
        # Count language occurrences
        language_counts = {}
        for file_info in matching_files:
            lang = file_info.get('language')
            if lang:
                language_counts[lang] = language_counts.get(lang, 0) + 1
        
        # Return the most common language
        if language_counts:
            return max(language_counts.items(), key=lambda x: x[1])[0]
        
        # Get project languages from repository analysis if no matching files
        try:
            project_structure = self.project_analyzer.analyze_sync()
            languages = project_structure.get('languages', [])
            if languages:
                return languages[0]
        except Exception:
            pass
        
        # Default to Python if no language found
        return 'python'
    
    def _find_suitable_directory(self) -> str:
        """
        Find a suitable directory for creating a new file.
        
        Returns:
            Directory path
        """
        # Common directory patterns by convention
        common_src_dirs = [
            'src',                   # Standard source directory
            'app',                   # Common for web applications
            'lib',                   # Libraries and utilities
            'core',                  # Core functionality
            'modules',               # Modular components
            'components',            # UI components (especially in frontend)
            'services',              # Service-oriented architecture
            'controllers',           # MVC pattern controllers
            'models',                # MVC pattern models
            'views',                 # MVC pattern views
            'utils',                 # Utility functions
            'helpers',               # Helper functions
            'api',                   # API related code
            'internal',              # Internal implementation
            'main'                   # Main application code
        ]
        
        # Check for feature-specific directories based on common patterns
        feature_dirs = [
            'features',              # Feature modules
            'domain',                # Domain logic
            'infrastructure',        # Infrastructure components
            'presentation',          # Presentation layer
            'ui',                    # User interface
            'pages',                 # Page components (web)
            'screens',               # Screen components (mobile)
            'routes',                # Routing
            'middleware',            # Middleware components
            'hooks',                 # React hooks or similar
            'store',                 # State management
            'reducers',              # Redux reducers
            'actions',               # Redux actions
            'sagas',                 # Redux sagas
            'thunks'                 # Redux thunks
        ]
        
        # First check if any of the common source directories exist
        for dir_name in common_src_dirs:
            if (self.repo_path / dir_name).is_dir():
                return dir_name
        
        # Then check feature-specific directories
        for dir_name in feature_dirs:
            if (self.repo_path / dir_name).is_dir():
                return dir_name
        
        # Look for most populated directory with code files
        try:
            dirs_with_code = {}
            for root, dirs, files in os.walk(str(self.repo_path)):
                rel_path = os.path.relpath(root, start=str(self.repo_path))
                if rel_path == '.':
                    rel_path = ''
                    
                # Skip hidden directories and common non-code directories
                if (rel_path.startswith('.') or 
                    any(part.startswith('.') for part in rel_path.split(os.sep)) or
                    any(ignored in rel_path.split(os.sep) for ignored in 
                        ['node_modules', 'venv', '__pycache__', 'dist', 'build', 'target'])):
                    continue
                
                # Count code files
                code_files = 0
                for file in files:
                    if self.code_parser.get_language_from_file(os.path.join(rel_path, file)):
                        code_files += 1
                
                if code_files > 0:
                    dirs_with_code[rel_path] = code_files
            
            # Return directory with most code files
            if dirs_with_code:
                return max(dirs_with_code.items(), key=lambda x: x[1])[0]
        except Exception:
            pass
        
        # If nothing else, return empty string (root directory)
        return ''
    
    def analyze_sync(self) -> Dict[str, Any]:
        """
        Synchronous wrapper for project analysis.
        
        Returns:
            Project structure information
        """
        import asyncio
        
        try:
            # Try to create a new event loop for synchronous context
            loop = asyncio.new_event_loop()
            return loop.run_until_complete(self.project_analyzer.analyze())
        except RuntimeError:
            # If there's already an event loop, use it
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.project_analyzer.analyze())
        except Exception:
            # If all else fails, return a minimal structure
            return {
                'languages': [],
                'file_structure': {'type': 'directory', 'contents': {}}
            }