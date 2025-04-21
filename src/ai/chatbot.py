"""
Claude API Wrapper

This module provides a simple wrapper around the Anthropic Claude API
for generating text completions and following instructions.
"""

import os
import requests
import json
import logging
import time
from typing import Optional, Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChatBot:
    """
    A wrapper for the Claude API that provides a simple interface for generating 
    text completions and carrying on conversations.
    """
    
    def __init__(self, system_prompt: str, api_key: Optional[str] = None, 
                 model: str = "claude-3-7-sonnet-20250219", max_tokens: int = 4000):
        """
        Initialize the ChatBot with API credentials and settings.
        
        Args:
            system_prompt (str): The system prompt that defines Claude's behavior
            api_key (str, optional): Claude API key. If not provided, will use CLAUDE_API_KEY env var
            model (str): Claude model to use
            max_tokens (int): Maximum number of tokens in the response
        """
        # Set API key from provided value or environment
        self.api_key = api_key or os.environ.get("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError("No Claude API key provided. Set CLAUDE_API_KEY environment variable or pass it to the constructor.")
        
        # Set API parameters
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.api_url = "https://api.anthropic.com/v1/messages"
        
        # Initialize conversation history
        self.conversation_history = []
        
        # Add system prompt as the first message
        if system_prompt:
            self.conversation_history.append({
                "role": "system",
                "content": system_prompt
            })
        
        logger.info(f"Initialized ChatBot with model: {model}")
    
    def __call__(self, message: str) -> str:
        """
        Send a message to Claude and get a response.
        
        Args:
            message (str): The user message to send to Claude
            
        Returns:
            str: Claude's response
        """
        return self.send_message(message)
    
    def send_message(self, message: str, stream: bool = False) -> str:
        """
        Send a message to Claude and get a response.
        
        Args:
            message (str): The user message to send to Claude
            stream (bool): Whether to stream the response
            
        Returns:
            str: Claude's response
        """
        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # Prepare messages for the API
        messages = self._prepare_messages()
        
        # Send request to Claude API
        response_text = self._send_api_request(messages, stream)
        
        # Add assistant response to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": response_text
        })
        
        return response_text
    
    def _prepare_messages(self) -> List[Dict[str, str]]:
        """
        Prepare messages for the Claude API.
        
        Returns:
            List[Dict[str, str]]: List of message objects
        """
        # Extract messages from conversation history
        messages = []
        system_message = None
        
        # Separate system message and other messages
        for msg in self.conversation_history:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                messages.append(msg)
        
        return messages
    
    def _send_api_request(self, messages: List[Dict[str, str]], stream: bool = False) -> str:
        """
        Send a request to the Claude API.
        
        Args:
            messages (List[Dict[str, str]]): List of message objects
            stream (bool): Whether to stream the response
            
        Returns:
            str: Claude's response
        """
        try:
            # Extract system prompt if it exists
            system = None
            if messages and messages[0]["role"] == "system":
                system = messages[0]["content"]
                messages = messages[1:]
            
            # Prepare request headers
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            # Prepare request payload
            payload = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "stream": stream,
                "messages": messages,
            }
            
            # Add system prompt if available
            if system:
                payload["system"] = system
            
            # Send request
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload
            )
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return f"API Error: {response.status_code} - {response.text}"
            
            # Parse response
            response_data = response.json()
            
            # Extract content
            if "content" in response_data:
                content = response_data["content"][0]["text"]
                return content
            else:
                return response_data.get("completion", "No content received")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return f"Request error: {e}"
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return f"JSON decode error: {e}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return f"Unexpected error: {e}"
    
    def reset_conversation(self) -> None:
        """
        Reset the conversation history, keeping only the system prompt.
        """
        system_prompt = None
        for msg in self.conversation_history:
            if msg["role"] == "system":
                system_prompt = msg["content"]
                break
                
        self.conversation_history = []
        
        if system_prompt:
            self.conversation_history.append({
                "role": "system",
                "content": system_prompt
            })
        
        logger.info("Conversation history reset")