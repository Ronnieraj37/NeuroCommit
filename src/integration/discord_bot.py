"""
Discord bot integration for the AI Code Modification Agent.
"""
import os
import logging
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional

import discord
from discord.ext import commands
from discord import app_commands

# Add project root to Python path to allow importing from src
import sys
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(project_root, 'discord_bot.log'))
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
            "claude_api_key": os.environ.get("CLAUDE_API_KEY", ""),
            "discord_token": os.environ.get("DISCORD_TOKEN", "")
        }

class AICodeAgentBot(commands.Bot):
    def __init__(self, config: Dict[str, Any]):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        self.config = config
        self.orchestrator = Orchestrator(config)
        self.active_tasks = {}
        
    async def setup_hook(self):
        """Setup hook that runs when the bot is started."""
        await self.tree.sync()
        logger.info("Bot commands synced")
        
    async def on_ready(self):
        """Event called when the bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")

class TaskView(discord.ui.View):
    """View with buttons for task management."""
    def __init__(self, task_id: str, orchestrator: Orchestrator):
        super().__init__(timeout=None)
        self.task_id = task_id
        self.orchestrator = orchestrator
    
    @discord.ui.button(label="Check Status", style=discord.ButtonStyle.primary)
    async def check_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to check the status of a task."""
        task = self.orchestrator.task_queue.get_task(self.task_id)
        if task:
            await interaction.response.send_message(
                f"Task ID: {task.id}\n"
                f"Status: {task.status}\n"
                f"Repository: {task.repo_url}\n"
                f"Description: {task.description}\n"
                f"Result: {task.result if task.result else 'N/A'}\n"
                f"Error: {task.error if task.error else 'None'}"
            )
        else:
            await interaction.response.send_message(f"Task ID {self.task_id} not found")

async def main():
    """Main entry point for the Discord bot."""
    config = load_config()
    
    # Check for required configuration
    if not config.get("github_token"):
        logger.error("GitHub token is required. Set GITHUB_TOKEN environment variable or provide it in config file.")
        return
    
    if not config.get("claude_api_key"):
        logger.error("Claude API key is required. Set CLAUDE_API_KEY environment variable or provide it in config file.")
        return
    
    if not config.get("discord_token"):
        logger.error("Discord token is required. Set DISCORD_TOKEN environment variable or provide it in config file.")
        return
    
    # Create bot
    bot = AICodeAgentBot(config)
    
    # Register slash commands
    @bot.tree.command(name="implement", description="Implement a feature in a GitHub repository")
    @app_commands.describe(
        repo_url="GitHub repository URL",
        description="Feature description",
        target_branch="Target branch for the PR (default: main)"
    )
    async def implement(
        interaction: discord.Interaction, 
        repo_url: str, 
        description: str, 
        target_branch: str = "main"
    ):
        await interaction.response.defer(thinking=True)
        
        try:
            # Log the request
            logger.info(f"Implement request from {interaction.user}: {repo_url} - {description}")
            
            # Start the implementation in a background task
            task_id = bot.orchestrator.task_queue.add_task(repo_url, description)
            
            await interaction.followup.send(
                f"Started feature implementation task (ID: {task_id})\n"
                f"Repository: {repo_url}\n"
                f"Feature: {description}\n"
                f"This may take several minutes to complete...",
                view=TaskView(task_id, bot.orchestrator)
            )
            
            # Process the request in the background
            bot.active_tasks[task_id] = asyncio.create_task(
                process_implement_request(bot, interaction, task_id, repo_url, description, target_branch)
            )
            
        except Exception as e:
            logger.error(f"Error processing implement command: {str(e)}")
            await interaction.followup.send(f"Error: {str(e)}")
    
    @bot.tree.command(name="fix", description="Fix a bug in a GitHub repository")
    @app_commands.describe(
        repo_url="GitHub repository URL",
        description="Bug description",
        target_branch="Target branch for the PR (default: main)"
    )
    async def fix(
        interaction: discord.Interaction, 
        repo_url: str, 
        description: str, 
        target_branch: str = "main"
    ):
        await interaction.response.defer(thinking=True)
        
        try:
            # Log the request
            logger.info(f"Fix request from {interaction.user}: {repo_url} - {description}")
            
            # Start the implementation in a background task
            task_id = bot.orchestrator.task_queue.add_task(repo_url, f"Fix bug: {description}")
            
            await interaction.followup.send(
                f"Started bug fix task (ID: {task_id})\n"
                f"Repository: {repo_url}\n"
                f"Bug: {description}\n"
                f"This may take several minutes to complete...",
                view=TaskView(task_id, bot.orchestrator)
            )
            
            # Process the request in the background
            bot.active_tasks[task_id] = asyncio.create_task(
                process_implement_request(bot, interaction, task_id, repo_url, f"Fix bug: {description}", target_branch)
            )
            
        except Exception as e:
            logger.error(f"Error processing fix command: {str(e)}")
            await interaction.followup.send(f"Error: {str(e)}")
    
    @bot.tree.command(name="status", description="Check status of AI code agent tasks")
    async def status(interaction: discord.Interaction):
        stats = bot.orchestrator.task_queue.get_stats()
        
        await interaction.response.send_message(
            "Task queue status:\n"
            f"  Pending: {stats['pending']}\n"
            f"  In progress: {stats['in_progress']}\n"
            f"  Completed: {stats['completed']}\n"
            f"  Failed: {stats['failed']}\n"
            f"  Total: {stats['total']}"
        )
        
    # Regular command for simple interaction
    @bot.command(name="ping")
    async def ping(ctx):
        await ctx.send("Pong! AI Code Agent is online.")
    
    # Start the bot
    async with bot:
        await bot.start(config["discord_token"])

async def process_implement_request(
    bot: AICodeAgentBot,
    interaction: discord.Interaction,
    task_id: str,
    repo_url: str,
    description: str,
    target_branch: str
):
    """
    Process an implementation request in the background.
    
    Args:
        bot: Bot instance
        interaction: Discord interaction
        task_id: Task ID
        repo_url: GitHub repository URL
        description: Feature description
        target_branch: Target branch for the PR
    """
    try:
        # Process the request
        pr_url = await bot.orchestrator.process_request(repo_url, description, target_branch)
        
        if pr_url.startswith("Error:"):
            bot.orchestrator.task_queue.mark_failed(task_id, pr_url)
            await interaction.followup.send(f"Task {task_id} failed: {pr_url}")
        else:
            bot.orchestrator.task_queue.mark_completed(task_id, pr_url)
            await interaction.followup.send(
                f"Task {task_id} completed successfully!\n"
                f"Pull Request created: {pr_url}"
            )
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {str(e)}")
        bot.orchestrator.task_queue.mark_failed(task_id, str(e))
        await interaction.followup.send(f"Task {task_id} failed with error: {str(e)}")
    finally:
        # Remove the task from active tasks
        if task_id in bot.active_tasks:
            del bot.active_tasks[task_id]

if __name__ == "__main__":
    asyncio.run(main())