"""
Test runner for executing project tests.
"""
import asyncio
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

class TestResult:
    def __init__(self, success: bool, output: str, failures: List[Dict[str, Any]] = None):
        """
        Initialize test result.
        
        Args:
            success: Whether tests passed
            output: Test output
            failures: List of test failures
        """
        self.success = success
        self.output = output
        self.failures = failures or []

class TestRunner:
    def __init__(self, repo_path: Path):
        """
        Initialize test runner.
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
    
    async def run_tests(self) -> TestResult:
        """
        Run tests for the project.
        
        Returns:
            Test result
        """
        # Determine what kind of project this is
        test_command = await self._determine_test_command()
        
        if not test_command:
            return TestResult(
                False, 
                "Could not determine how to run tests for this project",
                [{"error": "No test command found"}]
            )
        
        try:
            # Run the test command
            process = await asyncio.create_subprocess_shell(
                test_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.repo_path)
            )
            
            stdout, stderr = await process.communicate()
            combined_output = stdout.decode('utf-8', errors='replace') + stderr.decode('utf-8', errors='replace')
            
            # Check if tests passed
            success = process.returncode == 0
            
            # Parse failures
            failures = self._parse_test_failures(combined_output, test_command)
            
            return TestResult(success, combined_output, failures)
        
        except Exception as e:
            return TestResult(False, f"Error running tests: {str(e)}", [{"error": str(e)}])
    
    async def _determine_test_command(self) -> Optional[str]:
        """
        Determine the command to run tests based on project structure.
        
        Returns:
            Test command or None if not found
        """
        # Check for npm (Node.js) project
        if (self.repo_path / 'package.json').exists():
            try:
                with open(self.repo_path / 'package.json') as f:
                    package_data = json.load(f)
                
                scripts = package_data.get('scripts', {})
                
                # Check for common test script names
                for script_name in ['test', 'tests', 'unit', 'jest', 'mocha']:
                    if script_name in scripts:
                        return f"npm run {script_name}"
                
                # If no test script found, check if Jest is installed
                if (self.repo_path / 'node_modules' / 'jest').exists():
                    return "npx jest"
                
                # Check if Mocha is installed
                if (self.repo_path / 'node_modules' / 'mocha').exists():
                    return "npx mocha"
            
            except (json.JSONDecodeError, IOError):
                pass
        
        # Check for Python project
        python_test_files = list(self.repo_path.glob('**/test_*.py'))
        if python_test_files or (self.repo_path / 'tests').exists() or (self.repo_path / 'test').exists():
            # Check for pytest
            if self._check_requirements_for_package('pytest'):
                return "python -m pytest"
            
            # Check for unittest
            return "python -m unittest discover"
        
        # Check for Maven project
        if (self.repo_path / 'pom.xml').exists():
            return "mvn test"
        
        # Check for Gradle project
        if (self.repo_path / 'build.gradle').exists() or (self.repo_path / 'build.gradle.kts').exists():
            gradle_command = "./gradlew" if (self.repo_path / 'gradlew').exists() else "gradle"
            return f"{gradle_command} test"
        
        # Default to None if no test command can be determined
        return None
    
    def _check_requirements_for_package(self, package: str) -> bool:
        """
        Check if a Python package is in requirements.txt.
        
        Args:
            package: Package name
            
        Returns:
            True if the package is in requirements, False otherwise
        """
        req_files = [
            self.repo_path / 'requirements.txt',
            self.repo_path / 'requirements-dev.txt',
            self.repo_path / 'dev-requirements.txt'
        ]
        
        for req_file in req_files:
            if req_file.exists():
                try:
                    content = req_file.read_text(encoding='utf-8')
                    if re.search(rf'\b{re.escape(package)}\b', content):
                        return True
                except UnicodeDecodeError:
                    continue
        
        return False
    
    def _parse_test_failures(self, output: str, test_command: str) -> List[Dict[str, Any]]:
        """
        Parse test failures from output.
        
        Args:
            output: Test output
            test_command: Test command used
            
        Returns:
            List of test failures
        """
        failures = []
        
        if 'pytest' in test_command:
            # PyTest failure parsing
            error_blocks = re.findall(r'_{40,}\n(.*?)\n\n', output, re.DOTALL)
            
            for block in error_blocks:
                file_match = re.search(r'([\w/\\.-]+\.py):(\d+)', block)
                error_match = re.search(r'E\s+(.*)', block)
                
                if file_match and error_match:
                    file_path = file_match.group(1)
                    line_number = int(file_match.group(2))
                    error_message = error_match.group(1).strip()
                    
                    failures.append({
                        'file': file_path,
                        'line': line_number,
                        'message': error_message
                    })
        
        elif 'jest' in test_command or 'npm' in test_command:
            # Jest/Mocha failure parsing
            error_blocks = re.findall(r'● (.*?)\n\n(.*?)(?=\n\n●|\n\nRan all test suites|$)', output, re.DOTALL)
            
            for test_name, details in error_blocks:
                file_match = re.search(r'\s+at\s+.*?\s+\((.*?):(\d+):(\d+)\)', details)
                
                if file_match:
                    file_path = file_match.group(1)
                    line_number = int(file_match.group(2))
                    
                    failures.append({
                        'file': file_path,
                        'line': line_number,
                        'message': test_name.strip()
                    })
                else:
                    failures.append({
                        'message': test_name.strip()
                    })
        
        elif 'mvn' in test_command or 'gradle' in test_command:
            # Maven/Gradle failure parsing
            test_failures = re.findall(r'Tests in error:\s+(.*?)(?=\n\nTests run:|$)', output, re.DOTALL)
            
            if test_failures:
                for failure_block in test_failures:
                    for line in failure_block.split('\n'):
                        test_match = re.match(r'\s*(\w+)(?:\([\w.]+\))?: (.*)', line.strip())
                        if test_match:
                            failures.append({
                                'test': test_match.group(1),
                                'message': test_match.group(2)
                            })
        
        # If no specific failures could be parsed, add a generic failure
        if not failures and "FAILED" in output:
            failures.append({
                'message': "Tests failed, but could not parse specific failures."
            })
        
        return failures