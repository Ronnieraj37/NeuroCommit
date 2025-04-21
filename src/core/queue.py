"""
Simple task queue implementation for managing concurrent requests.
For local development, this is a basic in-memory queue.
"""
import time
import uuid
from typing import Dict, List, Any, Optional

class Task:
    def __init__(self, task_id: str, repo_url: str, description: str):
        self.id = task_id
        self.repo_url = repo_url
        self.description = description
        self.status = "pending"
        self.created_at = time.time()
        self.updated_at = time.time()
        self.result = None
        self.error = None

class TaskQueue:
    def __init__(self):
        """Initialize an empty task queue."""
        self.tasks: Dict[str, Task] = {}
        self.pending_tasks: List[str] = []
        self.in_progress_tasks: List[str] = []
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []
    
    def add_task(self, repo_url: str, description: str) -> str:
        """
        Add a new task to the queue.
        
        Args:
            repo_url: URL of the repository to modify
            description: Description of the feature to implement
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        task = Task(task_id, repo_url, description)
        self.tasks[task_id] = task
        self.pending_tasks.append(task_id)
        return task_id
    
    def get_next_task(self) -> Optional[Task]:
        """
        Get the next pending task.
        
        Returns:
            Next task or None if queue is empty
        """
        if not self.pending_tasks:
            return None
        
        task_id = self.pending_tasks.pop(0)
        self.in_progress_tasks.append(task_id)
        task = self.tasks[task_id]
        task.status = "in_progress"
        task.updated_at = time.time()
        return task
    
    def mark_completed(self, task_id: str, result: Any = None) -> None:
        """
        Mark a task as completed.
        
        Args:
            task_id: ID of the task
            result: Result of the task (e.g., PR URL)
        """
        if task_id in self.in_progress_tasks:
            self.in_progress_tasks.remove(task_id)
            self.completed_tasks.append(task_id)
            
            task = self.tasks[task_id]
            task.status = "completed"
            task.updated_at = time.time()
            task.result = result
    
    def mark_failed(self, task_id: str, error: str) -> None:
        """
        Mark a task as failed.
        
        Args:
            task_id: ID of the task
            error: Error message
        """
        if task_id in self.in_progress_tasks:
            self.in_progress_tasks.remove(task_id)
            self.failed_tasks.append(task_id)
            
            task = self.tasks[task_id]
            task.status = "failed"
            task.updated_at = time.time()
            task.error = error
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Task or None if not found
        """
        return self.tasks.get(task_id)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        return {
            "pending": len(self.pending_tasks),
            "in_progress": len(self.in_progress_tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "total": len(self.tasks)
        }