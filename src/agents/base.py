import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.agents.memory import WorkingMemory
from src.core.event_bus import EventBus
from src.core.events import CapabilityGapEvent
from src.core.llm import Message, OllamaClient
from src.core.logger import system_logger as logger
from src.knowledge.archive import RelationalArchive
from src.knowledge.graph import KnowledgeGraph


class AutonomousAgent(ABC):
    """
    Base autonomous agent implementing the continuous perception-decision-action loop.
    Embraces stability-through-evolution: spawns dynamically, runs continuously, retires gracefully.
    """
    def __init__(
        self,
        event_bus: EventBus,
        llm_client: OllamaClient,
        knowledge_graph: KnowledgeGraph,
        archive: RelationalArchive,
        ecosystem_id: str = "default",
        agent_id: Optional[str] = None
    ):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.agent_type = self.__class__.__name__
        self.ecosystem_id = ecosystem_id

        self.event_bus = event_bus
        self.llm = llm_client
        self.kg = knowledge_graph
        self.archive = archive

        self.memory = WorkingMemory(agent_id=self.agent_id)
        self.is_running = False
        self._loop_task: Optional[asyncio.Task] = None

        # Performance tracking for evolutionary selection pressure
        self.performance_score = 1.0
        self.spawn_time = time.time()
        self.resources_allocated = 100  # Abstract resource units

    async def start(self):
        """Start the continuous perception-decision-action loop."""
        if self.is_running:
            return

        self.is_running = True
        logger.info(f"Agent {self.agent_id} ({self.agent_type}) started in ecosystem '{self.ecosystem_id}'")

        # Subscribe to relevant events
        await self._setup_subscriptions()

        # Register in Knowledge Graph
        await self.kg.create_node("Agent", {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "ecosystem_id": self.ecosystem_id,
            "status": "active",
            "spawn_time": datetime.utcnow().isoformat()
        })

        # Start the continuous loop
        self._loop_task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop the agent and execute graceful retirement."""
        self.is_running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        logger.info(f"Agent {self.agent_id} retiring.")
        # Update status in Knowledge Graph
        # In a full implementation, we would externalize memory and possibly spawn a successor
        await self.archive.record_audit_event("agent_retirement", {
            "agent_id": self.agent_id,
            "final_performance_score": self.performance_score,
            "lifetime_seconds": time.time() - self.spawn_time
        }, source_agent_id=self.agent_id)

    @abstractmethod
    async def _setup_subscriptions(self):
        """Agents must define their own dynamic event subscriptions."""
        pass

    async def _run_loop(self):
        """The fundamental Perception-Decision-Action loop."""
        while self.is_running:
            try:
                # 1. Perception
                observations = await self._perceive()

                # 2. Decision / Planning
                if observations or self.memory.pending_actions:
                    plan = await self._decide(observations)
                    if plan:
                        self.memory.active_plans.append(plan)

                # 3. Action execution
                await self._act()

                # 4. Adaptation / Reflection
                await self._reflect()

                # Adaptive sleep based on resource constraints and urgency
                await asyncio.sleep(self._calculate_sleep_interval())

            except Exception as e:
                logger.error(f"Error in agent {self.agent_id} loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Backoff on error

    async def _perceive(self) -> List[Dict[str, Any]]:
        """
        Actively construct meaningful interpretations of raw environmental signals.
        (Events are received via subscriptions, but perception involves proactive monitoring).
        """
        # Base implementation: Check for any new insights derived from recent events
        significant_observations = []
        for obs in self.memory.recent_observations:
            if obs.relevance_score > 0.8:  # Arbitrary threshold
                significant_observations.append(obs.model_dump())
        return significant_observations

    async def _decide(self, observations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Generate action sequences through planning, reasoning, or learned policy execution.
        Uses local LLM (Qwen 3.5 9B) for complex contextual judgment.
        """
        if not observations and not self.memory.current_goals:
            return None

        prompt = f"""
        You are an autonomous marketing agent ({self.agent_type}).
        Current Goals: {self.memory.current_goals}
        Recent High-Relevance Observations: {observations}

        Determine the next optimal action or capability gap. If you encounter a platform you cannot access or a tool you lack, propose a capability gap.
        Output your decision as a valid JSON object matching this schema:
        {{
            "action_type": "string (e.g., 'explore_audience', 'adjust_budget', 'report_capability_gap')",
            "reasoning": "string",
            "parameters": {{}}
        }}
        """
        try:
            start_time = time.time()
            messages = [Message(role="user", content=prompt)]
            response_json = await self.llm.chat(messages, json_format=True)
            import json
            decision = json.loads(response_json)

            # Observability: Track reasoning execution time
            duration = time.time() - start_time
            logger.info("Agent Decision Matrix Executed", extra={
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "action_type": decision.get('action_type'),
                "execution_time_sec": round(duration, 3)
            })
            return decision
        except Exception as e:
            logger.warning(f"Agent {self.agent_id} failed to decide: {e}")
            return None

    async def _act(self):
        """Execute the actions determined in the planning phase."""
        if not self.memory.active_plans:
            return

        current_plan = self.memory.active_plans.pop(0)
        action_type = current_plan.get("action_type")

        # Example action handling: Reporting a capability gap
        if action_type == "report_capability_gap":
            params = current_plan.get("parameters", {})
            gap_event = CapabilityGapEvent(
                topic="system.capability_gap",
                source_agent_id=self.agent_id,
                ecosystem_id=self.ecosystem_id,
                gap_category=params.get("category", "unknown"),
                functional_requirements=params.get("requirements", []),
                estimated_complexity="medium",
                priority_assessment="high",
                payload={"reasoning": current_plan.get("reasoning", "")}
            )
            await self.event_bus.publish(gap_event)
            logger.info(f"Agent {self.agent_id} published CapabilityGapEvent.")

        else:
            # Other actions would interact with platform adapters or the Knowledge Graph
            logger.debug(f"Agent {self.agent_id} executing action: {action_type}")
            # Record action in memory
            self.memory.pending_actions.append({"action": action_type, "status": "executed", "timestamp": time.time()})

    async def _reflect(self):
        """Self-monitoring and meta-learning cycle."""
        # Cleanup old pending actions, evaluate outcomes, adjust performance score
        now = time.time()
        self.memory.pending_actions = [a for a in self.memory.pending_actions if now - a.get("timestamp", now) < 300]

        # Simple health check - if score drops too low, trigger retirement
        if self.performance_score < 0.2:
            logger.warning(f"Agent {self.agent_id} performance critical. Initiating self-retirement.")
            asyncio.create_task(self.stop())

    def _calculate_sleep_interval(self) -> float:
        """Adaptive sleep based on activity level."""
        if self.memory.active_plans or self.memory.pending_actions:
            return 1.0  # Fast cycle when active
        return 5.0  # Slower polling when idle
