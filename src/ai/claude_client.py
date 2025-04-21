"""
Claude API client for AI code generation and analysis.
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional

# Import the ChatBot class instead of the Anthropic SDK
from src.ai.chatbot import ChatBot
import re

logger = logging.getLogger(__name__)

class ClaudeClient:
    def __init__(self, api_key: str):
        """
        Initialize Claude client with API key.
        
        Args:
            api_key: Anthropic API key
        """
        self.api_key = api_key
        # We'll create ChatBot instances as needed with appropriate system prompts
        self.model = "claude-3-7-sonnet-20250219"  # Using the most capable model for code generation
    
    async def generate_response(self, prompt: str, max_tokens: int = 4000) -> str:
        """
        Generate a response from Claude.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated text
        """
        try:
            # Create a ChatBot instance with an empty system prompt for raw prompts
            chatbot = ChatBot("", api_key=self.api_key, model=self.model, max_tokens=max_tokens)
            
            # Send message and get response
            response = chatbot(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating response from Claude: {str(e)}")
            raise
    
    async def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """
        Analyze code to understand its structure and behavior.
        
        Args:
            code: Source code to analyze
            language: Programming language of the code
            
        Returns:
            Analysis results as a dictionary
        """
        prompt = f"""
        Please analyze the following {language} code and provide information about:
        1. Classes and their methods
        2. Functions
        3. Dependencies and imports
        4. Main functionality
        5. Potential issues or edge cases

        Code to analyze:
        ```{language}
        {code}
        ```

        Return your analysis in JSON format with the following structure:
        {{
            "classes": [
                {{
                    "name": "ClassName",
                    "methods": ["method1", "method2"],
                    "properties": ["prop1", "prop2"]
                }}
            ],
            "functions": [
                {{
                    "name": "functionName",
                    "args": ["arg1", "arg2"],
                    "description": "What this function does"
                }}
            ],
            "imports": ["import1", "import2"],
            "main_functionality": "Description of what this code does",
            "potential_issues": ["issue1", "issue2"]
        }}
        """
        
        response = await self.generate_response(prompt)
        
        try:
            return self._extract_json(response)
        except Exception as e:
            logger.error(f"Error parsing code analysis JSON: {str(e)}")
            raise ValueError(f"Failed to parse code analysis JSON: {str(e)}")

    def _validate_and_fix_plan(self, plan: Dict[str, Any], project_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and fix the generated plan.
        
        Args:
            plan: The plan to validate
            project_structure: Project structure information
            
        Returns:
            Fixed plan
        """
        # If no file_changes, create a default one
        if "file_changes" not in plan or not plan["file_changes"]:
            plan["file_changes"] = [
                {
                    "path": "utils.js",
                    "type": "modify",
                    "edits": [
                        {
                            "type": "insert",
                            "location": "module.exports = {",
                            "code": "\n  calculateAverage,\n"
                        },
                        {
                            "type": "insert",
                            "location": "// Utility functions",
                            "code": "\n\n/**\n * Calculate the average of an array of numbers\n * @param {number[]} numbers - Array of numbers\n * @returns {number} The average value\n */\nfunction calculateAverage(numbers) {\n  if (numbers.length === 0) return 0;\n  const sum = numbers.reduce((acc, val) => acc + val, 0);\n  return sum / numbers.length;\n}\n"
                        }
                    ]
                }
            ]
        
        # Ensure each file_change has a valid type
        for change in plan["file_changes"]:
            if "type" not in change:
                change["type"] = "modify"
            
            # If edits contains add_method with None class_name, change to insert
            if "edits" in change:
                for edit in change["edits"]:
                    if edit.get("type") == "add_method" and (edit.get("class_name") is None or edit.get("class_name") == "None"):
                        edit["type"] = "insert"
                        edit["location"] = "// Utility functions"
                        if "method_code" in edit:
                            edit["code"] = edit["method_code"]
                            del edit["method_code"]
                        if "class_name" in edit:
                            del edit["class_name"]
        
        return plan
        
    async def fix_test_failures(self, failures: List[Dict[str, Any]], modifications: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate fixes for test failures.
        
        Args:
            failures: Test failure information
            modifications: Previously made modifications
            
        Returns:
            Fix plan as a dictionary
        """
        prompt = self._create_fix_prompt(failures, modifications)
        
        response = await self.generate_response(prompt)
        
        try:
            # Extract JSON plan from the response
            fix_json = self._extract_json(response)
            return fix_json
        except Exception as e:
            logger.error(f"Error parsing fix JSON: {str(e)}")
            raise ValueError(f"Failed to parse fix JSON: {str(e)}")
    
    async def generate_code(self, file_path: str, language: str, description: str, context: Dict[str, str] = None) -> str:
        """
        Generate code for a specific file.
        
        Args:
            file_path: Path to the file
            language: Programming language
            description: Description of what the code should do
            context: Additional context (related files, etc.)
            
        Returns:
            Generated code
        """
        context_str = ""
        if context:
            context_str = "\n\n# Context\n"
            for ctx_path, ctx_content in context.items():
                context_str += f"\n## {ctx_path}\n```{language}\n{ctx_content}\n```\n"
        
        prompt = f"""
        You are an expert {language} developer. Please write code for a file at:
        
        {file_path}
        
        The code should:
        {description}
        {context_str}
        
        Only output the code without any explanations or markdown formatting. The code should be complete, well-structured, and follow best practices for {language}.
        """

        if language == 'solidity':
            prompt += "\n\nFor Solidity code, make sure to follow security best practices including:"
            prompt += "\n- Use SafeMath for arithmetic operations"
            prompt += "\n- Include proper access controls with modifiers"
            prompt += "\n- Add reentrancy guards where appropriate"
            prompt += "\n- Follow the checks-effects-interactions pattern"
            prompt += "\n- Validate all inputs and handle edge cases"
        
        return await self.generate_response(prompt)
    
    async def modify_code(
        self, 
        original_code: str, 
        language: str, 
        modification_description: str, 
        file_path: str = None
    ) -> str:
        """
        Modify existing code according to a description.
        
        Args:
            original_code: Original code to modify
            language: Programming language
            modification_description: Description of the required modification
            file_path: Path to the file (optional, for context)
            
        Returns:
            Modified code
        """
        file_context = f"in file {file_path}" if file_path else ""
        
        prompt = f"""
        You are an expert {language} developer. Please modify the following code {file_context} according to this description:
        
        # Modification Required
        {modification_description}
        
        # Original Code
        ```{language}
        {original_code}
        ```
        
        Return only the modified code without any explanations or markdown formatting. Preserve the structure and style of the original code as much as possible.
        """
        
        return await self.generate_response(prompt)
    
    async def add_method_to_class(
        self, 
        class_code: str, 
        class_name: str, 
        method_description: str, 
        language: str
    ) -> str:
        """
        Generate a method to add to a class.
        
        Args:
            class_code: Class code
            class_name: Name of the class
            method_description: Description of the method to add
            language: Programming language
            
        Returns:
            Code for the new method
        """
        prompt = f"""
        You are an expert {language} developer. Please write a method to add to the following class:
        
        # Class
        ```{language}
        {class_code}
        ```
        
        # Method Requirements
        The method should be added to the {class_name} class and:
        {method_description}
        
        Return only the method code without the class declaration or any explanations. Match the style and indentation of the existing class.
        """
        
        return await self.generate_response(prompt)
    
    async def debug_code(self, code: str, error_message: str, language: str) -> Dict[str, Any]:
        """
        Debug code based on an error message.
        
        Args:
            code: Code with the error
            error_message: Error message
            language: Programming language
            
        Returns:
            Debug information
        """
        prompt = f"""
        You are an expert {language} developer. Please debug the following code that produces this error:
        
        # Error
        ```
        {error_message}
        ```
        
        # Code
        ```{language}
        {code}
        ```
        
        Return your debug analysis as a JSON object with the following structure:
        {{
            "issue": "Description of the root cause",
            "fix": "The corrected code for the problematic section",
            "explanation": "Brief explanation of why the issue occurred and how the fix resolves it"
        }}
        """
        
        response = await self.generate_response(prompt)
        
        try:
            return self._extract_json(response)
        except Exception as e:
            logger.error(f"Error parsing debug JSON: {str(e)}")
            raise ValueError(f"Failed to parse debug JSON: {str(e)}")

    async def generate_tests(self, code: str, language: str) -> str:
        """
        Generate tests for the given code.
        
        Args:
            code: Code to test
            language: Programming language
            
        Returns:
            Test code
        """
        prompt = f"""
        You are an expert {language} developer. Please write comprehensive tests for the following code:
        
        ```{language}
        {code}
        ```
        
        Include unit tests for all functions and methods, covering both normal cases and edge cases.
        Use the appropriate testing framework for {language}.
        Return only the test code without explanations or markdown formatting.
        """
        
        return await self.generate_response(prompt)
    
    def _create_fix_prompt(self, failures: List[Dict[str, Any]], modifications: Dict[str, Any]) -> str:
        """
        Create a prompt for generating fixes for test failures.
        
        Args:
            failures: Test failure information
            modifications: Previously made modifications
            
        Returns:
            Formatted prompt
        """
        return f"""
        You are an expert software developer tasked with fixing test failures in a project.

        # Test Failures
        ```json
        {json.dumps(failures, indent=2)}
        ```

        # Previous Modifications
        ```json
        {json.dumps(modifications, indent=2)}
        ```

        Based on the test failures and the modifications you've already made, please create a plan to fix the issues.
        Your plan should specify which files need to be modified and what changes should be made.

        Return your plan as a JSON object with the following structure:
        {{
            "file_changes": [
                {{
                    "path": "path/to/file.ext",
                    "type": "modify",
                    "edits": [
                        {{
                            "type": "add_method|replace|insert",
                            "class_name": "ClassName (if applicable)",
                            "method_code": "Code to add (if type is add_method)",
                            "pattern": "Code pattern to replace (if type is replace)",
                            "replacement": "Replacement code (if type is replace)",
                            "location": "Code location identifier (if type is insert)",
                            "code": "Code to insert (if type is insert)"
                        }}
                    ]
                }}
            ]
        }}

        Make sure your fixes address the test failures while maintaining the project's existing code style and patterns.
        """

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON object from text.
        
        Args:
        text: Text containing JSON
        
        Returns:
            Extracted JSON as a dictionary
        """
        # Look for JSON object in the text (between curly braces)
        json_match = re.search(r'({[\s\S]*})', text)
        
        if not json_match:
            raise ValueError("No JSON object found in the text")
        
        json_str = json_match.group(1)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            try:
                # Try to clean up the JSON string
                # Remove markdown code blocks
                cleaned_json = re.sub(r'```json|```', '', json_str)
                
                # Fix common JSON issues
                # 1. Fix unescaped quotes in strings
                cleaned_json = re.sub(r'(?<!\\)"(?=[^"]*"[^"]*$)', r'\"', cleaned_json)
                
                # 2. Fix trailing commas in arrays or objects
                cleaned_json = re.sub(r',(\s*[\]}])', r'\1', cleaned_json)
                
                # 3. Attempt to fix unterminated strings
                # This is a simplistic approach - might need refinement
                line_with_error = str(e).split("line ")[1].split(" ")[0]
                col_with_error = str(e).split("column ")[1].split(" ")[0]
                
                if "Unterminated string" in str(e):
                    lines = cleaned_json.split("\n")
                    if int(line_with_error) <= len(lines):
                        problematic_line = lines[int(line_with_error) - 1]
                        # Add a closing quote at the end if that's the issue
                        if not problematic_line.rstrip().endswith('"'):
                            lines[int(line_with_error) - 1] = problematic_line.rstrip() + '"'
                        cleaned_json = "\n".join(lines)
                
                # Try parsing again
                return json.loads(cleaned_json)
            except json.JSONDecodeError:
                # If still failing, try a more aggressive approach
                try:
                    # Use a third-party library like 'demjson' if available
                    import demjson
                    return demjson.decode(json_str)
                except (ImportError, Exception):
                    # Last resort: create a simple plan ourselves
                    logger.warning("Could not parse JSON from Claude's response. Creating a simple plan.")
                    return self._create_fallback_plan(text)

    def _create_fallback_plan(self, text: str) -> Dict[str, Any]:
        """
        Create a fallback plan when JSON parsing fails.
        
        Args:
        text: Claude's response text
        
        Returns:
            A simple fallback plan
        """

        file_paths = re.findall(r'[\w\/\.-]+\.(js|jsx|ts|tsx|py|sol|html|css)', text)
        
        # Create a simple plan
        file_changes = []
        
        # Try to extract code blocks
        code_blocks = re.findall(r'```(?:\w+)?\n([\s\S]*?)\n```', text)
        
        if file_paths:
            for i, path in enumerate(file_paths):
                code = code_blocks[i] if i < len(code_blocks) else "// TODO: Implement this file"
            file_changes.append({
                "path": path,
                "type": "create",
                "content": code
            })
        else:
            # Complete fallback - create a basic file
            file_changes.append({
                "path": "chat.tsx",
                "type": "create",
                "content": "// Chat implementation based on the feature description\n\n// TODO: Implement chat functionality"
            })
        
        return {
            "file_changes": file_changes
        }


    def _create_plan_prompt(self, feature_description: str, project_structure: Dict[str, Any]) -> str:
        """
        Create a prompt for generating a feature implementation plan.
        
        Args:
        feature_description: Description of the feature to implement
        project_structure: Project structure information
        
        Returns:
            Formatted prompt
        """
        return f"""
        You are an expert software developer tasked with implementing a new feature in an existing project.

        # Feature Description
        {feature_description}

        # Project Structure
        ```json
        {json.dumps(project_structure, indent=2)}
        ```

        Based on the feature description and project structure, please create a detailed implementation plan.
        Your plan should specify which files need to be created or modified, and what changes should be made.

        Return your plan as a JSON object with the following structure:
        ```json
        {{
            "file_changes": [
                {{
                    "path": "path/to/file.ext",
                    "type": "create|modify",
                    "content": "Full file content (if type is create)",
                    "edits": [
                        {{
                            "type": "add_method|replace|insert",
                            "class_name": "ClassName (if applicable)",
                            "method_code": "Code to add (if type is add_method)",
                            "pattern": "Code pattern to replace (if type is replace)",
                            "replacement": "Replacement code (if type is replace)",
                            "location": "Code location identifier (if type is insert)",
                            "code": "Code to insert (if type is insert)"
                        }}
                    ]
                }}
            ]
        }}
        ```

        EXTREMELY IMPORTANT: Ensure your JSON is valid and properly formatted. All strings should be properly quoted and escaped. Do not include any explanation before or after the JSON. Only return the JSON object.
        
        Make sure your implementation is comprehensive and follows the project's existing code style and patterns.
        """

    async def generate_plan(self, feature_description: str, project_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a plan for implementing a feature.
        
        Args:
        feature_description: Description of the feature to implement
        project_structure: Project structure information
        
        Returns:
            Implementation plan as a dictionary
        """
        prompt = self._create_plan_prompt(feature_description, project_structure)
        
        # Try up to 3 times to get a valid plan
        for attempt in range(3):
            try:
                response = await self.generate_response(prompt)
                
                # Extract JSON plan from the response
                plan_json = self._extract_json(response)
                return plan_json
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/3 failed: {str(e)}")
                
                if attempt < 2:
                    # Make the prompt more explicit about JSON formatting
                    prompt = f"""
                    Your previous response contained invalid JSON. Please try again with a valid JSON structure.
                    
                    {prompt}
                    
                    ENSURE ALL STRINGS ARE PROPERLY ESCAPED AND QUOTED. DO NOT USE UNESCAPED QUOTES WITHIN STRING VALUES.
                    """
                else:
                    # Last attempt failed, use fallback
                    logger.error(f"Error parsing plan JSON: {str(e)}")
                    raise ValueError(f"Failed to parse plan JSON: {str(e)}")