import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional

import aio_pika
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.events import BaseEvent

logger = logging.getLogger(__name__)

class EventBus:
    """
    Event-Driven Nervous System Implementation.
    Uses RabbitMQ for local-first asynchronous event distribution.
    """
    def __init__(self, rabbitmq_url: Optional[str] = None, exchange_name: Optional[str] = None):
        self.rabbitmq_url = rabbitmq_url or settings.RABBITMQ_URL
        self.exchange_name = exchange_name or settings.RABBITMQ_EXCHANGE
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None
        self.exchange: Optional[aio_pika.RobustExchange] = None
        self.subscribers: Dict[str, List[Callable[[BaseEvent], Coroutine[Any, Any, None]]]] = {}

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def connect(self):
        """Establish async connection to RabbitMQ with automatic retries."""
        try:
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()
            self.exchange = await self.channel.declare_exchange(self.exchange_name, aio_pika.ExchangeType.TOPIC, durable=True)
            logger.info("Connected to Event Bus (RabbitMQ)")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ (retrying): {e}")
            raise

    @retry(
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception)
    )
    async def publish(self, event: BaseEvent):
        """Publish an event asynchronously to the topic exchange with retry logic."""
        if not self.connection or self.connection.is_closed:
            await self.connect()

        try:
            payload = event.model_dump_json().encode('utf-8')
            message = aio_pika.Message(
                body=payload,
                content_type='application/json',
                message_id=event.event_id,
                timestamp=event.timestamp
            )

            # The topic string (e.g., 'performance.anomaly.ctr_drop') is used as the routing key
            await self.exchange.publish(
                message,
                routing_key=event.topic
            )
            logger.debug(f"Published event [{event.topic}] - ID: {event.event_id}")

            # Also invoke local in-memory subscribers for the same process
            asyncio.create_task(self._notify_local_subscribers(event))

        except Exception as e:
            logger.error(f"Error publishing event {event.topic} (retrying): {e}")
            raise

    async def _notify_local_subscribers(self, event: BaseEvent):
        """Notify any in-process subscribers to the topic."""
        # Simple pattern matching for local subscribers (e.g., matching 'performance.*')
        for pattern, callbacks in self.subscribers.items():
            if self._match_topic(pattern, event.topic):
                for callback in callbacks:
                    try:
                        await callback(event)
                    except Exception as e:
                        logger.error(f"Error in local subscriber callback for {event.topic}: {e}")

    def _match_topic(self, pattern: str, topic: str) -> bool:
        """Simple RabbitMQ-style topic matching (supports * and #)."""
        if pattern == "#":
            return True

        pattern_parts = pattern.split(".")
        topic_parts = topic.split(".")

        if len(pattern_parts) != len(topic_parts) and "#" not in pattern_parts:
            return False

        for p, t in zip(pattern_parts, topic_parts):
            if p == "*":
                continue
            if p == "#":
                return True
            if p != t:
                return False

        return True

    def subscribe(self, pattern: str, callback: Callable[[BaseEvent], Coroutine[Any, Any, None]]):
        """Register a local async callback for a given topic pattern."""
        if pattern not in self.subscribers:
            self.subscribers[pattern] = []
        self.subscribers[pattern].append(callback)
        logger.info(f"Subscribed local callback to pattern: {pattern}")

    async def start_consuming_external(self, queue_name: str, pattern: str, callback: Callable[[str, Dict[str, Any]], Coroutine[Any, Any, None]]):
        """
        Starts an async consumer for a specific queue to listen to RabbitMQ.
        """
        if not self.connection or self.connection.is_closed:
            await self.connect()

        queue = await self.channel.declare_queue(queue_name, exclusive=True)
        await queue.bind(self.exchange, routing_key=pattern)

        async def _process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    await callback(message.routing_key, data)
                except Exception as e:
                    logger.error(f"Error processing consumed message: {e}")

        await queue.consume(_process_message)
        logger.info(f"Started consuming external queue '{queue_name}' for pattern '{pattern}'")
