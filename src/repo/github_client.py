"""
GitHub API client for repository operations.
"""
import logging
import re
from typing import Dict, Any, List, Optional
import aiohttp

logger = logging.getLogger(__name__)

class GitHubClient:
    BASE_URL = "https://api.github.com"
    
    def __init__(self, access_token: str):
        """
        Initialize GitHub client with access token.
        
        Args:
            access_token: GitHub personal access token
        """
        self.access_token = access_token
        self.headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Code-Agent"
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an HTTP request to the GitHub API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            data: Request data for POST/PUT/PATCH requests
            
        Returns:
            Response data as dictionary
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=self.headers, json=data) as response:
                response_data = await response.json()
                
                if response.status >= 400:
                    logger.error(f"GitHub API error: {response.status} - {response_data.get('message')}")
                    raise Exception(f"GitHub API error: {response_data.get('message')}")
                
                return response_data
    
    async def get_repository(self, repo_url: str) -> Dict[str, Any]:
        """
        Get repository information.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Repository information
        """
        # Extract owner and repo name from URL
        match = re.match(r"https?://github.com/([^/]+)/([^/]+)", repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
        
        owner, name = match.groups()
        name = name.replace(".git", "")
        
        response = await self._make_request("GET", f"/repos/{owner}/{name}")
        return {
            "id": response["id"],
            "owner": owner,
            "name": name,
            "clone_url": response["clone_url"],
            "default_branch": response["default_branch"],
            "language": response["language"],
            "has_issues": response["has_issues"]
        }

    async def fork_repository(self, repo_url: str) -> Dict[str, Any]:
        """
        Fork a repository.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Forked repository information
        """
        repo_info = await self.get_repository(repo_url)
        original_owner, name = repo_info["owner"], repo_info["name"]
        
        # Check if fork already exists
        user = await self._make_request("GET", "/user")
        username = user["login"]
        
        try:
            existing_fork = await self._make_request("GET", f"/repos/{username}/{name}")
            logger.info(f"Fork already exists: {existing_fork['html_url']}")
            
            return {
                "id": existing_fork["id"],
                "owner": username,
                "name": name,
                "original_owner": original_owner,  # Store original owner for PR creation
                "clone_url": existing_fork["clone_url"].replace("https://github.com", 
                            f"https://{self.access_token}@github.com"),
                "default_branch": existing_fork["default_branch"]
            }
        except Exception:
            # Fork doesn't exist, create it
            logger.info(f"Creating fork of {original_owner}/{name}")
            response = await self._make_request("POST", f"/repos/{original_owner}/{name}/forks")
            
            # Wait a moment for the fork to be ready
            await asyncio.sleep(5)
            
            return {
                "id": response["id"],
                "owner": username,
                "name": name,
                "original_owner": original_owner,  # Store original owner for PR creation
                "clone_url": response["clone_url"].replace("https://github.com", 
                            f"https://{self.access_token}@github.com"),
                "default_branch": response["default_branch"]
            }
            
    async def get_file_content(self, owner: str, repo: str, path: str, ref: str = None) -> str:
        """
        Get the content of a file from the repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            ref: Git reference (branch name, commit SHA, etc.)
            
        Returns:
            File content as string
        """
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        if ref:
            endpoint += f"?ref={ref}"
        
        response = await self._make_request("GET", endpoint)
        
        import base64
        content = base64.b64decode(response["content"]).decode("utf-8")
        return content


    async def create_pull_request(
        self, 
        owner: str, 
        repo: str, 
        head_branch: str, 
        base_branch: str, 
        title: str, 
        body: str,
        original_owner: str = None
    ) -> str:
        """
        Create a pull request.
        
        Args:
            owner: Repository owner (your username)
            repo: Repository name
            head_branch: Head branch name
            base_branch: Base branch name
            title: PR title
            body: PR description
            original_owner: Original repository owner (for forks)
            
        Returns:
            URL of the created PR
        """
        user = await self._make_request("GET", "/user")
        username = user["login"]
        
        # If this is a fork, use the original owner as the base
        target_owner = original_owner or owner
        
        data = {
            "title": title,
            "body": body,
            "head": f"{username}:{head_branch}",
            "base": base_branch
        }
        
        try:
            response = await self._make_request("POST", f"/repos/{target_owner}/{repo}/pulls", data)
            return response["html_url"]
        except Exception as e:
            logger.error(f"Error creating PR: {str(e)}")
            # More detailed error information
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Error details: {e.response.text}")
            raise