import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from src.core.event_bus import EventBus
from src.core.llm import Message, OllamaClient
from src.knowledge.archive import RelationalArchive
from src.knowledge.graph import KnowledgeGraph

logger = logging.getLogger(__name__)

class DeepSystemAudit:
    """
    Scheduled Audit Cycles as Sole Fixed Schedule.
    Comprehensive system health evaluation, architectural drift detection,
    and evolution direction assessment.
    """
    def __init__(
        self,
        event_bus: EventBus,
        kg: KnowledgeGraph,
        archive: RelationalArchive,
        llm: OllamaClient,
        interval_seconds: int = 3600  # Default 1 hour for testing
    ):
        self.event_bus = event_bus
        self.kg = kg
        self.archive = archive
        self.llm = llm
        self.interval = interval_seconds
        self.is_running = False
        self._task = None

    async def start(self):
        """Start the scheduled audit cycle."""
        if self.is_running:
            return
        self.is_running = True
        logger.info(f"System Auditor started with interval {self.interval}s")
        self._task = asyncio.create_task(self._audit_loop())

    async def stop(self):
        """Stop the scheduled audit cycle."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("System Auditor stopped.")

    async def _audit_loop(self):
        while self.is_running:
            await asyncio.sleep(self.interval)
            try:
                await self.perform_audit()

                # Dynamic interval adjustment (Stability check)
                # If stable, increase interval. If unstable, decrease.
                self.interval = self._adjust_interval()

            except Exception as e:
                logger.error(f"Error during system audit: {e}", exc_info=True)

    def _adjust_interval(self) -> int:
        """Adaptive frequency optimization based on system stability indicators."""
        # Simple placeholder implementation
        # A real implementation would analyze the recent audit results for drift/errors
        return max(600, min(86400, self.interval))

    async def perform_audit(self):
        """Execute the comprehensive multi-dimensional assessment."""
        logger.info("Starting Deep System Audit...")

        audit_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "health_evaluation": {},
            "evolution_direction": {},
            "architectural_drift": {},
            "agent_population": {}
        }

        # 1. Comprehensive System Health Evaluation (Agent Population Quality)
        agent_data = await self.kg.query("MATCH (a:Agent) RETURN a.status as status, count(a) as count")
        active_agents = sum(row["count"] for row in agent_data if row["status"] == "active")
        retired_agents = sum(row["count"] for row in agent_data if row["status"] == "retired")

        audit_report["agent_population"] = {
            "active": active_agents,
            "retired": retired_agents,
            "churn_rate": retired_agents / max(1, (active_agents + retired_agents))
        }

        # 2. Evolution Direction Assessment (Strategy Diversity)
        strategy_data = await self.kg.query("MATCH (s:Strategy) RETURN s.status as status, count(s) as count")
        active_strategies = sum(row["count"] for row in strategy_data if row["status"] == "active")

        # Calculate strategy fitness metrics via PostgreSQL
        # We would typically use self.archive.pool.fetch here for complex aggregations
        audit_report["evolution_direction"] = {
            "active_strategies": active_strategies,
            "mutation_effectiveness": "pending"  # Placeholder
        }

        # 3. Architectural Drift Detection via LLM Analysis
        drift_assessment = await self._analyze_architectural_drift(audit_report)
        audit_report["architectural_drift"] = drift_assessment

        # Save audit report to PostgreSQL
        await self.archive.record_audit_event("system_audit_completed", audit_report)
        logger.info(f"Deep System Audit completed. Found {active_agents} active agents.")

    async def _analyze_architectural_drift(self, partial_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identification of implementation deviations from design intent.
        Uses the LLM to analyze the system state and recent event logs.
        """
        # Fetch recent system logs (e.g., last 100 audit events)
        # For simplicity, we just pass the partial report to the LLM
        prompt = f"""
        Analyze the following system state metrics for an Autonomous Adaptive Marketing Ecosystem.
        Metrics: {partial_report}

        Assess if the system is exhibiting 'Architectural Drift' such as:
        1. Workflow reintroduction (centralization instead of distributed autonomy).
        2. Rigidity accumulation (loss of evolutionary capability).
        3. Premature convergence in strategy space.

        Return your assessment as a JSON object containing:
        - drift_detected (boolean)
        - drift_type (string, or null if none)
        - recommended_intervention (string)
        - severity (integer 1-5)
        """
        try:
            response = await self.llm.chat([Message(role="user", content=prompt)], json_format=True)
            import json
            return json.loads(response)
        except Exception as e:
            logger.error(f"Failed LLM drift analysis: {e}")
            return {"drift_detected": False, "error": str(e)}

class EcosystemManager:
    """
    Brand and Project Isolation logic.
    Provides isolated namespaces and contexts for specific brands.
    """
    def __init__(self, brand_name: str, config: Dict[str, Any]):
        self.brand_name = brand_name
        self.ecosystem_id = f"eco_{brand_name.lower().replace(' ', '_')}"
        self.config = config

        # Isolation parameters
        self.budget_limit = config.get("budget_limit", 1000)
        self.allowed_platforms = config.get("allowed_platforms", [])
        self.performance_kpis = config.get("performance_kpis", ["roas", "cpa"])

    def validate_action(self, action_type: str, parameters: Dict[str, Any]) -> bool:
        """Check if an action proposed by an agent violates ecosystem constraints."""
        if action_type == "allocate_budget":
            amount = parameters.get("amount", 0)
            if amount > self.budget_limit:
                logger.warning(f"Ecosystem {self.ecosystem_id} blocked budget allocation: {amount} > {self.budget_limit}")
                return False

        if action_type == "deploy_campaign":
            platform = parameters.get("platform")
            if platform and platform not in self.allowed_platforms:
                logger.warning(f"Ecosystem {self.ecosystem_id} blocked platform: {platform} not in allowed platforms.")
                return False

        return True
