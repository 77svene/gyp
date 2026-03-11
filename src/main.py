import asyncio
import logging
from src.core.event_bus import EventBus
from src.core.llm import OllamaClient
from src.knowledge.graph import KnowledgeGraph
from src.knowledge.archive import RelationalArchive
from src.agents.campaign_manager import CampaignManagerAgent
from src.evolution.genome import StrategyGenome, PopulationManager
from src.evolution.experiments import ExperimentManager
from src.tools.forge import ToolForge
from src.governance.auditor import DeepSystemAudit, EcosystemManager
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SystemRunner")

async def main():
    """
    Main entry point for testing the Autonomous Adaptive Marketing Ecosystem Architecture prototype.
    """
    logger.info("Initializing Autonomous Adaptive Marketing Ecosystem...")

    # 1. Infrastructure Initialization
    event_bus = EventBus()
    event_bus.connect()

    llm = OllamaClient()

    kg = KnowledgeGraph()
    await kg.connect()

    archive = RelationalArchive()
    await archive.connect()

    # 2. Subsystem Initialization
    population = PopulationManager(archive, kg)
    experiments = ExperimentManager(event_bus, archive, kg)
    forge = ToolForge(event_bus, llm, kg)

    # 3. Ecosystem Setup
    eco_manager = EcosystemManager("Test Brand", {"budget_limit": 500, "allowed_platforms": ["twitter", "linkedin"]})

    # 4. Agent Spawning
    agent1 = CampaignManagerAgent(event_bus, llm, kg, archive, ecosystem_id=eco_manager.ecosystem_id)
    await agent1.start()

    # 5. Governance Setup
    auditor = DeepSystemAudit(event_bus, kg, archive, llm, interval_seconds=10)
    await auditor.start()

    # Wait for the system to stabilize
    await asyncio.sleep(2)

    # 6. Simulate an external event to trigger the system
    from src.core.events import PerformanceAnomalyEvent, CapabilityGapEvent

    # Simulate an anomaly
    anomaly = PerformanceAnomalyEvent(
        topic=f"performance.anomaly.{eco_manager.ecosystem_id}.ctr_drop",
        ecosystem_id=eco_manager.ecosystem_id,
        metric_name="ctr",
        deviation_magnitude=-35.0,
        temporal_pattern="sudden_spike",
        historical_context={"baseline": 2.5, "current": 1.6},
        payload={}
    )

    logger.info(f"Simulating Anomaly Event: {anomaly.topic}")
    event_bus.publish(anomaly)

    await asyncio.sleep(5)

    # Simulate a capability gap
    gap = CapabilityGapEvent(
        topic="system.capability_gap.platform",
        source_agent_id=agent1.agent_id,
        ecosystem_id=eco_manager.ecosystem_id,
        gap_category="linkedin_integration",
        functional_requirements=["fetch_campaign_metrics", "post_company_update"],
        estimated_complexity="medium",
        priority_assessment="high",
        payload={"reasoning": "Agent decided to shift budget to LinkedIn but lacks integration."}
    )

    logger.info(f"Simulating Capability Gap Event: {gap.topic}")
    event_bus.publish(gap)

    # Let the system run its loops
    try:
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        logger.info("Interrupt received. Shutting down...")
    finally:
        logger.info("Initiating graceful shutdown...")
        await agent1.stop()
        await auditor.stop()
        await llm.close()
        await kg.close()
        await archive.close()

if __name__ == "__main__":
    asyncio.run(main())