"""
Command-line interface for the AI Code Modification Agent.
"""
import argparse
import asyncio
import logging
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to Python path to allow importing from src
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(project_root, 'ai_code_agent.log'))
    ]
)

logger = logging.getLogger(__name__)

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the config file, or None to use default
        
    Returns:
        Configuration dictionary
    """
    if config_path is None:
        config_path = os.path.join(project_root, 'config', 'default.json')
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error loading config from {config_path}: {str(e)}")
        
        # Return default configuration
        return {
            "github_token": os.environ.get("GITHUB_TOKEN", ""),
            "claude_api_key": os.environ.get("CLAUDE_API_KEY", "")
        }

async def main() -> None:
    """
    Main entry point for the CLI.
    """
    parser = argparse.ArgumentParser(description="AI Code Modification Agent")
    
    # Command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Implement feature command
    implement_parser = subparsers.add_parser("implement", help="Implement a feature in a repository")
    implement_parser.add_argument("repo_url", help="GitHub repository URL")
    implement_parser.add_argument("description", help="Feature description")
    implement_parser.add_argument("--target-branch", default="main", help="Target branch for the PR")
    implement_parser.add_argument("--config", help="Path to config file")
    implement_parser.add_argument(
        "--language", 
        default="auto", 
        choices=["auto", "python", "javascript", "typescript", "java", "solidity"],
        help="Preferred programming language"
    )
    
    # Fix bug command
    fix_parser = subparsers.add_parser("fix", help="Fix a bug in a repository")
    fix_parser.add_argument("repo_url", help="GitHub repository URL")
    fix_parser.add_argument("description", help="Bug description")
    fix_parser.add_argument("--target-branch", default="main", help="Target branch for the PR")
    fix_parser.add_argument("--config", help="Path to config file")
    fix_parser.add_argument("--language", default="auto", help="Preferred programming language (python, javascript, etc.)")


    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check status of pending tasks")
    status_parser.add_argument("--config", help="Path to config file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load configuration
    config = load_config(args.config if hasattr(args, "config") else None)
    
    # Check for required configuration
    if not config.get("github_token"):
        logger.error("GitHub token is required. Set GITHUB_TOKEN environment variable or provide it in config file.")
        return
    
    if not config.get("claude_api_key"):
        logger.error("Claude API key is required. Set CLAUDE_API_KEY environment variable or provide it in config file.")
        return
    
    # Create orchestrator
    orchestrator = Orchestrator(config)
    
    if args.command == "implement":
        # Implement a feature
        pr_url = await orchestrator.process_request(
            args.repo_url,
            args.description,
            args.target_branch
        )
        
        if pr_url.startswith("Error:"):
            logger.error(pr_url)
        else:
            logger.info(f"Feature implementation PR created: {pr_url}")
    
    elif args.command == "fix":
        # Fix a bug (same as implement, but with different description semantics)
        pr_url = await orchestrator.process_request(
            args.repo_url,
            f"Fix bug: {args.description}",
            args.target_branch
        )
        
        if pr_url.startswith("Error:"):
            logger.error(pr_url)
        else:
            logger.info(f"Bug fix PR created: {pr_url}")
    
    elif args.command == "status":
        # Check status of pending tasks
        stats = orchestrator.task_queue.get_stats()
        
        print("Task queue status:")
        print(f"  Pending: {stats['pending']}")
        print(f"  In progress: {stats['in_progress']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Total: {stats['total']}")

if __name__ == "__main__":
    asyncio.run(main())