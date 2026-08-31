"""
Priority-based Request Queue
Manages API requests with priority queuing for better traffic management
"""

import asyncio
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RequestPriority(Enum):
    CRITICAL = 1  # Enterprise users, urgent requests
    HIGH = 2      # Professional users
    NORMAL = 3    # Starter users
    LOW = 4       # Free users, background tasks


@dataclass
class QueuedRequest:
    user_email: str
    endpoint: str
    priority: RequestPriority
    timestamp: datetime = field(default_factory=datetime.utcnow)
    callback: Optional[Callable] = None
    request_id: str = ""
    
    def __lt__(self, other):
        """For priority queue ordering"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.timestamp < other.timestamp


class RequestQueue:
    """Priority-based request queue for API calls"""
    
    def __init__(self, max_concurrent: int = 20):
        self.queue = asyncio.PriorityQueue()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.processing = set()
        self.stats = {
            'total_queued': 0,
            'total_processed': 0,
            'total_failed': 0,
            'avg_wait_time': 0.0
        }
        self._processing_task = None
        self._start_processing()
    
    def _start_processing(self):
        """Start background processing task"""
        # Will be started when needed
        pass
    
    async def add_request(
        self, 
        user_email: str,
        endpoint: str,
        priority: RequestPriority,
        callback: Callable
    ) -> str:
        """Add request to priority queue"""
        request_id = f"{user_email}_{endpoint}_{datetime.utcnow().timestamp()}"
        
        request = QueuedRequest(
            user_email=user_email,
            endpoint=endpoint,
            priority=priority,
            callback=callback,
            request_id=request_id
        )
        
        await self.queue.put((priority.value, request))
        self.stats['total_queued'] += 1
        
        logger.debug(f"Request queued: {request_id} with priority {priority.name}")
        return request_id
    
    async def process_request(self) -> Any:
        """Process a single request from the queue"""
        try:
            priority_value, request = await self.queue.get()
            
            async with self.semaphore:
                wait_time = (datetime.utcnow() - request.timestamp).total_seconds()
                self.stats['avg_wait_time'] = (
                    (self.stats['avg_wait_time'] * self.stats['total_processed'] + wait_time) /
                    (self.stats['total_processed'] + 1) if self.stats['total_processed'] > 0 else wait_time
                )
                
                self.processing.add(request.request_id)
                
                try:
                    if request.callback:
                        result = await request.callback()
                        self.stats['total_processed'] += 1
                        logger.debug(f"Request processed: {request.request_id}")
                        return result
                except Exception as e:
                    self.stats['total_failed'] += 1
                    logger.error(f"Request processing error: {e}")
                    raise
                finally:
                    self.processing.discard(request.request_id)
        except Exception as e:
            logger.error(f"Queue processing error: {e}")
            raise
    
    async def process_queue(self):
        """Process queued requests in priority order (background task)"""
        while True:
            try:
                await self.process_request()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(0.1)  # Brief pause before retry
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            **self.stats,
            'queue_size': self.queue.qsize(),
            'processing_count': len(self.processing)
        }


# Global queue instance
request_queue = RequestQueue()

