import asyncio
import time
from typing import Dict

from src.agents.base import AutonomousAgent
from src.agents.campaign_manager import CampaignManagerAgent
from src.core.event_bus import EventBus
from src.core.llm import OllamaClient
from src.core.logger import system_logger as logger
from src.knowledge.archive import RelationalArchive
from src.knowledge.graph import KnowledgeGraph


class AgentSupervisor:
    """
    Autonomous Agent Supervision.
    Monitors the health of running agents, restarts them if they crash,
    and handles dynamic spawning or graceful retirement based on system load and agent performance.
    """
    def __init__(self, event_bus: EventBus, llm: OllamaClient, kg: KnowledgeGraph, archive: RelationalArchive):
        self.event_bus = event_bus
        self.llm = llm
        self.kg = kg
        self.archive = archive

        # Registry of active agents
        self.managed_agents: Dict[str, AutonomousAgent] = {}

        # Supervision metrics
        self.crash_counts: Dict[str, int] = {}
        self.last_health_check: Dict[str, float] = {}

    async def spawn_agent(self, agent_class, ecosystem_id: str, **kwargs) -> AutonomousAgent:
        """Dynamically spawns an agent and begins managing its lifecycle."""
        agent = agent_class(
            event_bus=self.event_bus,
            llm_client=self.llm,
            knowledge_graph=self.kg,
            archive=self.archive,
            ecosystem_id=ecosystem_id,
            **kwargs
        )

        self.managed_agents[agent.agent_id] = agent
        self.crash_counts[agent.agent_id] = 0
        self.last_health_check[agent.agent_id] = time.time()

        await agent.start()
        logger.info(f"Supervisor spawned {agent.agent_type}", extra={"agent_id": agent.agent_id, "ecosystem": ecosystem_id})
        return agent

    async def retire_agent(self, agent_id: str):
        """Gracefully removes an agent from active duty."""
        agent = self.managed_agents.get(agent_id)
        if agent:
            await agent.stop()
            del self.managed_agents[agent_id]
            logger.info(f"Supervisor retired agent {agent_id}")

    async def supervise_loop(self, interval_seconds: int = 15):
        """Continuous background loop to monitor agent health and performance."""
        logger.info("AgentSupervisor starting monitoring loop.")
        while True:
            await asyncio.sleep(interval_seconds)

            for agent_id, agent in list(self.managed_agents.items()):
                # 1. Liveness check: Is the agent's asyncio task still running?
                if agent._loop_task and agent._loop_task.done():
                    # Check if it crashed with an exception
                    exception = agent._loop_task.exception()
                    if exception:
                        self.crash_counts[agent_id] += 1
                        logger.error(f"Agent {agent_id} crashed: {exception}", extra={"crash_count": self.crash_counts[agent_id]})

                        if self.crash_counts[agent_id] > 3:
                            logger.error(f"Agent {agent_id} exceeded crash threshold. Permanently retiring.")
                            await self.retire_agent(agent_id)
                        else:
                            # Attempt restart
                            logger.info(f"Supervisor restarting Agent {agent_id}")
                            agent.is_running = False
                            await agent.start()
                    else:
                        # Task finished normally (perhaps self-retired)
                        logger.info(f"Agent {agent_id} completed its task gracefully.")
                        await self.retire_agent(agent_id)

                # 2. Performance Check: If the agent is underperforming, reallocate resources or retire
                elif agent.is_running and agent.performance_score < 0.3:
                    logger.warning(f"Agent {agent_id} underperforming (score: {agent.performance_score}). Initiating retirement.")
                    await self.retire_agent(agent_id)

            # 3. Dynamic Scaling (Simulated)
            # In a real enterprise system, if the queue depth > threshold, we would spawn more CampaignManagerAgents
            # For this prototype, we just ensure at least 1 is running
            if len(self.managed_agents) == 0:
                logger.info("No active agents. Supervisor triggering auto-scale rule: spawning CampaignManagerAgent.")
                await self.spawn_agent(CampaignManagerAgent, "default")
