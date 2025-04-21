"""
Builds effective prompts for AI code generation.
"""
import json
from typing import Dict, Any, List, Optional

class PromptBuilder:
    def __init__(self, max_context_length: int = 4000):
        """
        Initialize prompt builder with maximum context length.
        
        Args:
            max_context_length: Maximum number of tokens for context
        """
        self.max_context_length = max_context_length
    
    def build_code_generation_prompt(
        self,
        feature_description: str,
        file_path: str,
        file_content: Optional[str] = None,
        related_files: Optional[Dict[str, str]] = None,
        language: str = "python"
    ) -> str:
        """
        Build a prompt for code generation.
        
        Args:
            feature_description: Description of the feature to implement
            file_path: Path to the file to modify
            file_content: Current content of the file (if it exists)
            related_files: Dictionary of related files {path: content}
            language: Programming language
            
        Returns:
            Formatted prompt
        """
        prompt = f"""
        # Task
        You are an expert {language} developer implementing the following feature:
        
        {feature_description}
        
        """
        
        if file_content:
            prompt += f"""
            # Current File: {file_path}
            ```{language}
            {file_content}
            ```
            
            """
        else:
            prompt += f"""
            # New File to Create: {file_path}
            This file doesn't exist yet. You need to create it from scratch.
            
            """
        
        if related_files:
            prompt += "# Related Files\n"
            for path, content in related_files.items():
                # Truncate content if it's too long
                if len(content) > 500:
                    content = content[:500] + "... (truncated)"
                
                prompt += f"""
                ## {path}
                ```{language}
                {content}
                ```
                
                """
        
        prompt += """
        # Instructions
        - Follow the existing code style and patterns
        - Make sure the code is well-documented
        - Handle potential edge cases
        - Ensure compatibility with the existing codebase
        
        Please provide the complete implementation for the file.
        """
        
        return prompt
    
    def build_code_modification_prompt(
        self,
        feature_description: str,
        file_path: str,
        file_content: str,
        modification_type: str,
        modification_details: Dict[str, Any],
        language: str = "python"
    ) -> str:
        """
        Build a prompt for code modification.
        
        Args:
            feature_description: Description of the feature to implement
            file_path: Path to the file to modify
            file_content: Current content of the file
            modification_type: Type of modification (add_method, replace, insert)
            modification_details: Details of the modification
            language: Programming language
            
        Returns:
            Formatted prompt
        """
        prompt = f"""
        # Task
        You are an expert {language} developer implementing the following feature:
        
        {feature_description}
        
        You need to modify an existing file to implement this feature.
        
        # File to Modify: {file_path}
        ```{language}
        {file_content}
        ```
        
        # Modification Required
        Type: {modification_type}
        """
        
        if modification_type == "add_method":
            prompt += f"""
            Add a new method to class '{modification_details.get('class_name')}'.
            The method should:
            - {modification_details.get('purpose', 'Implement the feature described above')}
            """
        elif modification_type == "replace":
            prompt += f"""
            Replace the following code:
            ```{language}
            {modification_details.get('pattern')}
            ```
            
            With new code that:
            - {modification_details.get('purpose', 'Implements the feature described above')}
            """
        elif modification_type == "insert":
            prompt += f"""
            Insert new code at the location identified by:
            ```{language}
            {modification_details.get('location')}
            ```
            
            The new code should:
            - {modification_details.get('purpose', 'Implement the feature described above')}
            """
        
        prompt += """
        # Instructions
        - Follow the existing code style and patterns
        - Make sure the code is well-documented
        - Handle potential edge cases
        - Ensure compatibility with the existing codebase
        
        Please provide the complete modified code segment.
        """
        
        return prompt
    
    def build_test_fix_prompt(
        self,
        test_failures: List[Dict[str, Any]],
        file_path: str,
        file_content: str,
        language: str = "python"
    ) -> str:
        """
        Build a prompt for fixing test failures.
        
        Args:
            test_failures: List of test failures
            file_path: Path to the file to modify
            file_content: Current content of the file
            language: Programming language
            
        Returns:
            Formatted prompt
        """
        failures_str = json.dumps(test_failures, indent=2)
        
        prompt = f"""
        # Task
        You are an expert {language} developer tasked with fixing test failures in a project.
        
        # Test Failures
        ```json
        {failures_str}
        ```
        
        # File to Fix: {file_path}
        ```{language}
        {file_content}
        ```
        
        # Instructions
        - Analyze the test failures and identify the issues in the code
        - Fix the issues while maintaining the existing code style and patterns
        - Make sure the code is well-documented
        - Handle potential edge cases
        
        Please provide the complete fixed code for the file.
        """
        
        return prompt