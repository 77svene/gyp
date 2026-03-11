import asyncio
import logging
from typing import Any, Dict, List
import json

from src.agents.base import AutonomousAgent
from src.core.events import BaseEvent, PerformanceAnomalyEvent, AudienceSignalEvent

logger = logging.getLogger(__name__)

class CampaignManagerAgent(AutonomousAgent):
    """
    An agent specializing in continuous monitoring and optimization of active campaigns.
    Reacts to performance anomalies and audience signals without external triggers.
    """
    async def _setup_subscriptions(self):
        """Subscribe to events relevant to campaign management."""
        self.event_bus.subscribe(f"performance.anomaly.{self.ecosystem_id}.*", self.handle_anomaly)
        self.event_bus.subscribe(f"audience.signal.{self.ecosystem_id}.*", self.handle_audience_signal)
        logger.info(f"CampaignManagerAgent {self.agent_id} subscribed to performance and audience events.")

    async def handle_anomaly(self, event: BaseEvent):
        """Interrupt current activity to incorporate significant anomaly events."""
        logger.warning(f"CampaignManagerAgent {self.agent_id} received anomaly: {event.topic}")
        # Add to working memory as a high-relevance observation
        from src.agents.memory import Observation
        try:
            anomaly_data = event.payload
            metric = anomaly_data.get("metric_name", "unknown")
            deviation = anomaly_data.get("deviation_magnitude", 0.0)

            obs = Observation(
                source=f"EventBus:{event.topic}",
                content=f"Anomaly detected in {metric}: {deviation} deviation.",
                relevance_score=0.9  # High priority for immediate reaction
            )
            self.memory.add_observation(obs)

            # Immediately add a goal to resolve the anomaly
            self.memory.current_goals.append(f"Investigate and mitigate anomaly on {metric}")

            # Record the event in the Knowledge Graph for historical context
            await self.kg.create_node("EventLog", {
                "event_id": event.event_id,
                "topic": event.topic,
                "agent_id": self.agent_id,
                "timestamp": event.timestamp.isoformat(),
                "payload": json.dumps(event.payload)
            })
        except Exception as e:
            logger.error(f"Error handling anomaly in agent {self.agent_id}: {e}")

    async def handle_audience_signal(self, event: BaseEvent):
        """Process emerging opportunities or shifting market conditions."""
        logger.info(f"CampaignManagerAgent {self.agent_id} received audience signal: {event.topic}")
        # Add to working memory as a medium-to-high relevance observation
        from src.agents.memory import Observation
        try:
            signal_data = event.payload
            signal_type = signal_data.get("signal_type", "unknown")
            confidence = signal_data.get("confidence_score", 0.5)

            obs = Observation(
                source=f"EventBus:{event.topic}",
                content=f"Audience signal {signal_type} detected with {confidence} confidence.",
                relevance_score=0.7 + (confidence * 0.2)  # Higher confidence = higher priority
            )
            self.memory.add_observation(obs)

            if confidence > 0.8:
                self.memory.current_goals.append(f"Exploit audience signal: {signal_type}")

        except Exception as e:
            logger.error(f"Error handling audience signal in agent {self.agent_id}: {e}")
