"""
Git operations for local repository management.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class GitOperations:
    def __init__(self, repo_path: Path):
        """
        Initialize Git operations with a repository path.
        
        Args:
            repo_path: Path to the repository directory
        """
        self.repo_path = repo_path
    
    async def clone_repository(self, clone_url: str) -> None:
        """
        Clone a repository.
        
        Args:
            clone_url: Repository clone URL
        """
        # Create parent directory if it doesn't exist
        os.makedirs(self.repo_path.parent, exist_ok=True)
        
        # Clone repository
        cmd = ["clone", clone_url, str(self.repo_path)]
        
        # Run command from parent directory since repository doesn't exist yet
        process = await asyncio.create_subprocess_exec(
            "git", *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.repo_path.parent)
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode("utf-8").strip()
            logger.error(f"Git clone failed: {error_msg}")
            raise Exception(f"Git clone failed: {error_msg}")
        
        logger.info(f"Cloned repository to {self.repo_path}")
    
    async def create_branch(self, branch_name: str) -> None:
        """
        Create and checkout a new branch.
        
        Args:
            branch_name: Branch name
        """
        await self._run_git_command(["checkout", "-b", branch_name])
        logger.info(f"Created and checked out branch: {branch_name}")
    
    async def commit_changes(self, message: str) -> None:
        """
        Commit all changes.
        
        Args:
            message: Commit message
        """
        # Add all changes
        await self._run_git_command(["add", "."])
        
        # Commit changes
        await self._run_git_command(["commit", "-m", message])
        logger.info(f"Committed changes: {message}")
    
    async def push_changes(self, branch_name: str) -> None:
        """
        Push changes to remote repository.
        
        Args:
            branch_name: Branch name
        """
        await self._run_git_command(["push", "-u", "origin", branch_name])
        logger.info(f"Pushed changes to branch: {branch_name}")
    
    async def get_current_branch(self) -> str:
        """
        Get the name of the current branch.
        
        Returns:
            Branch name
        """
        return await self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    
    async def get_changed_files(self) -> List[str]:
        """
        Get a list of modified files in the working directory.
        
        Returns:
            List of file paths
        """
        output = await self._run_git_command(["status", "--porcelain"])
        
        changed_files = []
        for line in output.split("\n"):
            if not line:
                continue
            
            status = line[:2]
            file_path = line[3:]
            
            # Skip untracked files
            if status == "??":
                continue
            
            changed_files.append(file_path)
        
        return changed_files


    async def _run_git_command(self, args: List[str], check: bool = True) -> str:
        """
        Run a git command in the repository directory.
        
        Args:
            args: Git command arguments
            check: Whether to check for command success
            
        Returns:
            Command output
        """
        cmd = ["git"] + args
        logger.debug(f"Running git command: {' '.join(cmd)}")
        
        # Set environment variable for Git credentials if needed
        env = os.environ.copy()
        
        # If this is a GitHub URL operation, ensure we use the correct credentials
        if any(arg for arg in args if "github.com" in str(arg)):
            # Get GitHub token from environment or config
            github_token = os.environ.get("GITHUB_TOKEN", "")
            if github_token:
                # Modify the URL to include the token if it's a GitHub URL
                for i, arg in enumerate(args):
                    if isinstance(arg, str) and "github.com" in arg:
                        # Replace https://github.com with https://token@github.com
                        args[i] = arg.replace("https://github.com", f"https://{github_token}@github.com")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.repo_path),
            env=env
        )
        
        stdout, stderr = await process.communicate()
        
        if check and process.returncode != 0:
            error_msg = stderr.decode("utf-8").strip()
            logger.error(f"Git command failed: {error_msg}")
            raise Exception(f"Git command failed: {error_msg}")
        
        return stdout.decode("utf-8").strip()