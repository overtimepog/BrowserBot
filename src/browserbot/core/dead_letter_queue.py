"""
Dead Letter Queue implementation for failed operations.
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import pickle
import aiofiles
import os

from .logger import get_logger
from .errors import BrowserBotError

logger = get_logger(__name__)


class MessageStatus(Enum):
    """Message status in DLQ."""
    PENDING = "pending"
    PROCESSING = "processing"
    FAILED = "failed"
    RESOLVED = "resolved"
    EXPIRED = "expired"


@dataclass
class DLQMessage:
    """Message in dead letter queue."""
    id: str
    operation: str
    payload: Dict[str, Any]
    error: str
    error_type: str
    retry_count: int
    max_retries: int
    created_at: datetime
    last_retry_at: Optional[datetime] = None
    status: MessageStatus = MessageStatus.PENDING
    resolution_notes: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return (
            self.retry_count < self.max_retries
            and self.status in (MessageStatus.PENDING, MessageStatus.FAILED)
            and not self.is_expired()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for field_name in ('created_at', 'last_retry_at', 'expires_at'):
            if data[field_name] is not None:
                data[field_name] = data[field_name].isoformat()
        data['status'] = data['status'].value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DLQMessage':
        """Create from dictionary."""
        # Convert ISO strings back to datetime objects
        for field_name in ('created_at', 'last_retry_at', 'expires_at'):
            if data[field_name] is not None:
                data[field_name] = datetime.fromisoformat(data[field_name])
        data['status'] = MessageStatus(data['status'])
        return cls(**data)


class DeadLetterQueue:
    """Dead Letter Queue for failed operations."""
    
    def __init__(
        self,
        storage_path: str = "data/dlq",
        max_message_age: timedelta = timedelta(days=30),
        cleanup_interval: int = 3600,  # 1 hour
        enable_persistence: bool = True
    ):
        self.storage_path = storage_path
        self.max_message_age = max_message_age
        self.cleanup_interval = cleanup_interval
        self.enable_persistence = enable_persistence
        
        self.messages: Dict[str, DLQMessage] = {}
        self.handlers: Dict[str, Callable] = {}
        
        # Ensure storage directory exists
        if self.enable_persistence:
            os.makedirs(self.storage_path, exist_ok=True)
        
        # Start background cleanup task
        asyncio.create_task(self._cleanup_task())
    
    async def add_message(
        self,
        operation: str,
        payload: Dict[str, Any],
        error: Exception,
        max_retries: int = 3,
        expires_in: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a failed operation to the DLQ."""
        message_id = str(uuid.uuid4())
        
        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + expires_in
        
        message = DLQMessage(
            id=message_id,
            operation=operation,
            payload=payload,
            error=str(error),
            error_type=type(error).__name__,
            retry_count=0,
            max_retries=max_retries,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        self.messages[message_id] = message
        
        # Persist to disk
        if self.enable_persistence:
            await self._save_message(message)
        
        logger.info(
            "Message added to DLQ",
            message_id=message_id,
            operation=operation,
            error_type=type(error).__name__
        )
        
        return message_id
    
    async def get_message(self, message_id: str) -> Optional[DLQMessage]:
        """Get message by ID."""
        return self.messages.get(message_id)
    
    async def list_messages(
        self,
        status: Optional[MessageStatus] = None,
        operation: Optional[str] = None,
        limit: int = 100
    ) -> List[DLQMessage]:
        """List messages with optional filtering."""
        filtered_messages = []
        
        for message in self.messages.values():
            if status and message.status != status:
                continue
            if operation and message.operation != operation:
                continue
            filtered_messages.append(message)
        
        # Sort by creation time (newest first)
        filtered_messages.sort(key=lambda m: m.created_at, reverse=True)
        
        return filtered_messages[:limit]
    
    async def retry_message(self, message_id: str) -> bool:
        """Retry a specific message."""
        message = self.messages.get(message_id)
        if not message:
            logger.warning("Message not found for retry", message_id=message_id)
            return False
        
        if not message.can_retry():
            logger.warning(
                "Message cannot be retried",
                message_id=message_id,
                status=message.status.value,
                retry_count=message.retry_count,
                max_retries=message.max_retries
            )
            return False
        
        # Check if handler is registered
        handler = self.handlers.get(message.operation)
        if not handler:
            logger.warning(
                "No handler registered for operation",
                operation=message.operation,
                message_id=message_id
            )
            return False
        
        message.status = MessageStatus.PROCESSING
        message.last_retry_at = datetime.utcnow()
        message.retry_count += 1
        
        try:
            # Execute handler
            result = await handler(message.payload)
            
            # Mark as resolved
            message.status = MessageStatus.RESOLVED
            message.resolution_notes = f"Resolved after {message.retry_count} retries"
            
            logger.info(
                "Message retry successful",
                message_id=message_id,
                retry_count=message.retry_count
            )
            
            # Persist changes
            if self.enable_persistence:
                await self._save_message(message)
            
            return True
            
        except Exception as e:
            logger.error(
                "Message retry failed",
                message_id=message_id,
                error=str(e),
                retry_count=message.retry_count
            )
            
            # Update status
            if message.retry_count >= message.max_retries:
                message.status = MessageStatus.FAILED
                message.resolution_notes = f"Failed after {message.retry_count} retries: {str(e)}"
            else:
                message.status = MessageStatus.PENDING
            
            # Persist changes
            if self.enable_persistence:
                await self._save_message(message)
            
            return False
    
    async def retry_all_pending(self) -> Dict[str, Any]:
        """Retry all pending messages."""
        pending_messages = await self.list_messages(status=MessageStatus.PENDING)
        
        results = {
            "total": len(pending_messages),
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }
        
        for message in pending_messages:
            if not message.can_retry():
                results["skipped"] += 1
                continue
            
            success = await self.retry_message(message.id)
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
        
        logger.info("Bulk retry completed", **results)
        return results
    
    def register_handler(self, operation: str, handler: Callable) -> None:
        """Register a handler for an operation type."""
        self.handlers[operation] = handler
        logger.info(f"Handler registered for operation: {operation}")
    
    async def resolve_message(
        self,
        message_id: str,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """Manually resolve a message."""
        message = self.messages.get(message_id)
        if not message:
            return False
        
        message.status = MessageStatus.RESOLVED
        message.resolution_notes = resolution_notes or "Manually resolved"
        
        # Persist changes
        if self.enable_persistence:
            await self._save_message(message)
        
        logger.info(
            "Message manually resolved",
            message_id=message_id,
            notes=resolution_notes
        )
        
        return True
    
    async def delete_message(self, message_id: str) -> bool:
        """Delete a message from the DLQ."""
        if message_id not in self.messages:
            return False
        
        del self.messages[message_id]
        
        # Remove from disk
        if self.enable_persistence:
            message_file = os.path.join(self.storage_path, f"{message_id}.json")
            try:
                os.remove(message_file)
            except FileNotFoundError:
                pass
        
        logger.info("Message deleted from DLQ", message_id=message_id)
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics."""
        stats = {
            "total_messages": len(self.messages),
            "status_counts": {},
            "operation_counts": {},
            "oldest_message": None,
            "newest_message": None
        }
        
        # Count by status
        for message in self.messages.values():
            status = message.status.value
            stats["status_counts"][status] = stats["status_counts"].get(status, 0) + 1
            
            # Count by operation
            operation = message.operation
            stats["operation_counts"][operation] = stats["operation_counts"].get(operation, 0) + 1
        
        # Find oldest and newest messages
        if self.messages:
            sorted_messages = sorted(self.messages.values(), key=lambda m: m.created_at)
            stats["oldest_message"] = sorted_messages[0].created_at.isoformat()
            stats["newest_message"] = sorted_messages[-1].created_at.isoformat()
        
        return stats
    
    async def _save_message(self, message: DLQMessage) -> None:
        """Save message to disk."""
        message_file = os.path.join(self.storage_path, f"{message.id}.json")
        
        try:
            async with aiofiles.open(message_file, 'w') as f:
                await f.write(json.dumps(message.to_dict(), indent=2))
        except Exception as e:
            logger.error(f"Failed to save message to disk: {e}")
    
    async def _load_messages(self) -> None:
        """Load messages from disk."""
        if not os.path.exists(self.storage_path):
            return
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                message_file = os.path.join(self.storage_path, filename)
                try:
                    async with aiofiles.open(message_file, 'r') as f:
                        data = json.loads(await f.read())
                        message = DLQMessage.from_dict(data)
                        self.messages[message.id] = message
                except Exception as e:
                    logger.error(f"Failed to load message from {filename}: {e}")
    
    async def _cleanup_task(self) -> None:
        """Background task to clean up expired messages."""
        while True:
            await asyncio.sleep(self.cleanup_interval)
            await self._cleanup_expired_messages()
    
    async def _cleanup_expired_messages(self) -> None:
        """Remove expired messages."""
        current_time = datetime.utcnow()
        expired_messages = []
        
        for message_id, message in self.messages.items():
            # Mark as expired if past max age
            if current_time - message.created_at > self.max_message_age:
                message.status = MessageStatus.EXPIRED
                expired_messages.append(message_id)
            elif message.is_expired():
                expired_messages.append(message_id)
        
        # Remove expired messages
        for message_id in expired_messages:
            await self.delete_message(message_id)
        
        if expired_messages:
            logger.info(f"Cleaned up {len(expired_messages)} expired messages")


# Global DLQ instance
_dlq_instance: Optional[DeadLetterQueue] = None


def get_dlq() -> DeadLetterQueue:
    """Get global DLQ instance."""
    global _dlq_instance
    if _dlq_instance is None:
        _dlq_instance = DeadLetterQueue()
    return _dlq_instance