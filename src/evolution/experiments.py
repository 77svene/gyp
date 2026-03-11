import time
import uuid
from typing import Any, Dict

from src.core.event_bus import EventBus
from src.core.events import ExperimentResultEvent
from src.core.logger import system_logger as logger
from src.core.tasks import TaskQueue
from src.knowledge.archive import RelationalArchive
from src.knowledge.graph import KnowledgeGraph


class ExperimentManager:
    """
    Experimentation Framework for continuous strategy evaluation.
    No fixed experiment scheduling; initiated based on informational requirements.
    """
    def __init__(self, event_bus: EventBus, archive: RelationalArchive, kg: KnowledgeGraph):
        self.event_bus = event_bus
        self.archive = archive
        self.kg = kg
        self.active_experiments: Dict[str, Dict[str, Any]] = {}

    async def launch_experiment(self, strategy_id: str, ecosystem_id: str, design_parameters: Dict[str, Any]) -> str:
        """Initiate a continuous experiment for a strategic variant."""
        experiment_id = str(uuid.uuid4())

        experiment_record = {
            "experiment_id": experiment_id,
            "strategy_id": strategy_id,
            "ecosystem_id": ecosystem_id,
            "design_parameters": design_parameters,
            "status": "running",
            "start_time": time.time(),
            "observed_outcomes": {},
            "statistical_significance": 0.0
        }

        self.active_experiments[experiment_id] = experiment_record

        # Log to Relational Archive
        await self.archive.log_experiment_result(
            experiment_id=experiment_id,
            strategy_id=strategy_id,
            ecosystem_id=ecosystem_id,
            parameters=design_parameters,
            outcomes={},
            significance=0.0
        )

        # Link in Knowledge Graph
        strategy_node = await self.kg.get_node_by_property("Strategy", "strategy_id", strategy_id)
        if strategy_node and "_id" in strategy_node:
            exp_node_id_str = await self.kg.create_node("Experiment", {"experiment_id": experiment_id, "status": "running"})
            await self.kg.create_relationship(
                int(strategy_node["_id"]),
                int(exp_node_id_str),
                "EVALUATED_BY"
            )

        logger.info(f"Launched experiment {experiment_id} for strategy {strategy_id}")
        return experiment_id

    async def record_observation(self, experiment_id: str, outcomes: Dict[str, Any], confidence_interval: float):
        """Update running experiment with new data."""
        if experiment_id not in self.active_experiments:
            logger.warning(f"Attempted to record observation for unknown experiment: {experiment_id}")
            return

        exp = self.active_experiments[experiment_id]

        # Incremental update (simplified)
        for k, v in outcomes.items():
            if k in exp["observed_outcomes"]:
                exp["observed_outcomes"][k] = (exp["observed_outcomes"][k] + v) / 2.0  # Simple moving average for demonstration
            else:
                exp["observed_outcomes"][k] = v

        # Offload statistical calculation / Bayesian updating to Redis Background Queue
        await TaskQueue.enqueue(
            "process_experiment_results",
            experiment_id=experiment_id,
            ecosystem_id=exp["ecosystem_id"]
        )

        sample_size = exp.get("sample_size", 0) + 1
        exp["sample_size"] = sample_size
        exp["statistical_significance"] = min(0.99, sample_size * 0.05 + confidence_interval)

        # Early stopping rule evaluation
        if exp["statistical_significance"] > 0.95 or (time.time() - exp["start_time"] > 86400 * 7):  # 7 days max
            await self.conclude_experiment(experiment_id)

    async def conclude_experiment(self, experiment_id: str):
        """Terminate experiment based on informational value (conclusive or futile)."""
        if experiment_id not in self.active_experiments:
            return

        exp = self.active_experiments.pop(experiment_id)
        exp["status"] = "completed"
        exp["end_time"] = time.time()

        # Publish result event
        result_event = ExperimentResultEvent(
            topic=f"experiment.result.{exp['ecosystem_id']}.completed",
            experiment_id=experiment_id,
            strategy_id=exp["strategy_id"],
            ecosystem_id=exp["ecosystem_id"],
            observed_outcomes=exp["observed_outcomes"],
            statistical_significance=exp["statistical_significance"],
            payload={"conclusion": "Statistically significant result achieved or time limit reached."}
        )
        await self.event_bus.publish(result_event)

        # Archive final state
        await self.archive.log_experiment_result(
            experiment_id=experiment_id,
            strategy_id=exp["strategy_id"],
            ecosystem_id=exp["ecosystem_id"],
            parameters=exp["design_parameters"],
            outcomes=exp["observed_outcomes"],
            significance=exp["statistical_significance"]
        )

        # Update Knowledge Graph status
        # ... logic to update Experiment node status to 'completed' ...

        logger.info(f"Concluded experiment {experiment_id}. Significance: {exp['statistical_significance']:.2f}")
