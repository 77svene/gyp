import copy
import random
import time
import uuid
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class StrategyGenome(BaseModel):
    """
    Encoding of Marketing Strategies as Genetic Representations.
    Supports variation, selection, and inheritance.
    """
    strategy_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ecosystem_id: str
    parent_ids: List[str] = Field(default_factory=list)
    fitness_history: List[Dict[str, float]] = Field(default_factory=list)
    current_fitness: float = 0.0
    status: str = "active"  # "active", "dormant", "retired"

    # Genomic components
    objectives: Dict[str, float] = Field(default_factory=dict)  # Target outcomes, success metrics, optimization criteria
    audience_targeting: Dict[str, Any] = Field(default_factory=dict)  # Segment definitions, selection criteria
    channel_selection: Dict[str, float] = Field(default_factory=dict)  # Platform priorities, cross-channel allocation
    creative_direction: Dict[str, Any] = Field(default_factory=dict)  # Messaging themes, tone
    execution_parameters: Dict[str, Any] = Field(default_factory=dict)  # Budget allocation, bid strategies
    adaptation_rules: List[Dict[str, Any]] = Field(default_factory=list)  # Triggers for strategic adjustment

    def mutate(self, mutation_rate: float = 0.1) -> 'StrategyGenome':
        """
        Continuous Mutation Operations.
        Generates strategic variation through small, random changes.
        """
        child_genome = self.model_copy(deep=True)
        child_genome.strategy_id = str(uuid.uuid4())
        child_genome.parent_ids = [self.strategy_id]
        child_genome.fitness_history = []
        child_genome.current_fitness = 0.0

        # Point mutation: Adjusting budget allocation parameter
        if 'budget' in child_genome.execution_parameters and random.random() < mutation_rate:
            budget = float(child_genome.execution_parameters['budget'])
            variation = budget * random.uniform(-0.2, 0.2)  # +/- 20%
            child_genome.execution_parameters['budget'] = max(0, budget + variation)

        # Gene duplication/deletion: Channel selection
        if child_genome.channel_selection and random.random() < mutation_rate:
            channels = list(child_genome.channel_selection.keys())
            if random.random() < 0.5 and len(channels) > 1:
                # Deletion
                channel_to_remove = random.choice(channels)
                del child_genome.channel_selection[channel_to_remove]
            else:
                # Duplication (split a channel into two similar variants with slightly different weights)
                channel_to_split = random.choice(channels)
                weight = child_genome.channel_selection[channel_to_split]
                child_genome.channel_selection[f"{channel_to_split}_variant_a"] = weight * 0.6
                child_genome.channel_selection[f"{channel_to_split}_variant_b"] = weight * 0.4
                del child_genome.channel_selection[channel_to_split]

        # Parameter perturbation: Audience targeting age
        if 'age_range' in child_genome.audience_targeting and random.random() < mutation_rate:
            age_range = child_genome.audience_targeting['age_range']
            if isinstance(age_range, list) and len(age_range) == 2:
                # Shift age range slightly
                shift = random.randint(-5, 5)
                child_genome.audience_targeting['age_range'] = [max(18, age_range[0] + shift), min(65, age_range[1] + shift)]

        # Add/modify adaptation rule
        if random.random() < mutation_rate:
            new_rule = {
                "trigger": f"performance_drop_{random.randint(10, 30)}pct",
                "action": "pause_and_evaluate"
            }
            child_genome.adaptation_rules.append(new_rule)

        return child_genome

    def crossover(self, partner: 'StrategyGenome') -> 'StrategyGenome':
        """
        Crossover combines genetic material from multiple parent strategies.
        """
        if self.ecosystem_id != partner.ecosystem_id:
            raise ValueError("Crossover must occur within the same ecosystem.")

        child_genome = StrategyGenome(
            ecosystem_id=self.ecosystem_id,
            parent_ids=[self.strategy_id, partner.strategy_id]
        )

        # Intelligent/Fixed crossover: Pick components from parents based on assumed linkage/fitness
        # In a full implementation, component selection would be weighted by component-level historical fitness
        child_genome.objectives = copy.deepcopy(self.objectives) if random.random() < 0.5 else copy.deepcopy(partner.objectives)
        child_genome.audience_targeting = copy.deepcopy(self.audience_targeting) if random.random() < 0.5 else copy.deepcopy(partner.audience_targeting)
        child_genome.channel_selection = copy.deepcopy(self.channel_selection) if random.random() < 0.5 else copy.deepcopy(partner.channel_selection)
        child_genome.creative_direction = copy.deepcopy(self.creative_direction) if random.random() < 0.5 else copy.deepcopy(partner.creative_direction)

        # Blend execution parameters (e.g., average budget)
        budget_self = float(self.execution_parameters.get('budget', 100))
        budget_partner = float(partner.execution_parameters.get('budget', 100))
        child_genome.execution_parameters['budget'] = (budget_self + budget_partner) / 2.0

        # Combine adaptation rules
        all_rules = self.adaptation_rules + partner.adaptation_rules
        # Randomly select a subset of rules to prevent uncontrolled growth
        child_genome.adaptation_rules = random.sample(all_rules, k=min(len(all_rules), max(len(self.adaptation_rules), len(partner.adaptation_rules))))

        return child_genome

    def update_fitness(self, performance_metrics: Dict[str, float], novelty_score: float = 0.0):
        """
        Fitness Evaluation Based on Performance Metrics.
        Multi-objective fitness incorporating direct performance, efficiency, robustness, and novelty.
        """
        # Example calculation: weighted sum of normalized metrics
        # Real implementation would use historical context and non-linear functions
        base_fitness = (
            performance_metrics.get("conversions", 0) * 0.5 +
            performance_metrics.get("roas", 0) * 0.3 +
            performance_metrics.get("engagement", 0) * 0.2
        )

        # Penalty for high cost or inefficiency
        efficiency_penalty = performance_metrics.get("cpa", 1.0) / 100.0

        # Novelty bonus for diversity maintenance
        exploration_value = novelty_score * 0.1

        new_fitness = max(0, (base_fitness - efficiency_penalty) + exploration_value)

        self.fitness_history.append({"timestamp": time.time(), "fitness": new_fitness})
        self.current_fitness = new_fitness

class PopulationManager:
    """Manages the ecosystem strategy population, selection pressure, and resource allocation."""
    def __init__(self, archive, kg):
        self.archive = archive
        self.kg = kg
        self.population: Dict[str, StrategyGenome] = {}

    def add_strategy(self, strategy: StrategyGenome):
        self.population[strategy.strategy_id] = strategy

    def remove_strategy(self, strategy_id: str):
        if strategy_id in self.population:
            del self.population[strategy_id]

    async def evolve(self, ecosystem_id: str, generation_size: int = 10, mutation_rate: float = 0.1):
        """Perform one step of evolutionary dynamics on the active population."""
        active_strats = [s for s in self.population.values() if s.ecosystem_id == ecosystem_id and s.status == "active"]

        if len(active_strats) < 2:
            return  # Not enough population to evolve

        # 1. Evaluate fitness (simulated here, would be driven by experiment results in reality)
        # 2. Selection: Preferential Resource Distribution to High Performers
        # Sort by fitness descending
        active_strats.sort(key=lambda s: s.current_fitness, reverse=True)

        # Top performers (elite preservation)
        elites = active_strats[:max(1, int(len(active_strats) * 0.2))]

        # 3. Automatic Termination of Underperforming Strategies
        # Bottom performers are retired unless they have high novelty
        bottom_strats = active_strats[int(len(active_strats) * 0.8):]
        for s in bottom_strats:
            if random.random() > 0.1:  # 10% chance to survive for diversity
                s.status = "dormant"
                await self.archive.save_strategy(s.strategy_id, s.ecosystem_id, s.model_dump(), s.current_fitness, s.parent_ids)
                await self.kg.create_node("Strategy", {"strategy_id": s.strategy_id, "status": "dormant"})
                self.remove_strategy(s.strategy_id)

        # 4. Generate new offspring via mutation and crossover
        new_strats = []
        while len(self.population) < generation_size:
            if random.random() < 0.7:  # 70% chance of mutation
                parent = random.choice(elites)
                child = parent.mutate(mutation_rate)
                new_strats.append(child)
                await self.kg.add_strategy_lineage(parent.strategy_id, child.strategy_id, "mutation")
            else:  # 30% chance of crossover
                parent1, parent2 = random.sample(elites, 2)
                child = parent1.crossover(parent2)
                new_strats.append(child)
                await self.kg.add_strategy_lineage(parent1.strategy_id, child.strategy_id, "crossover_p1")
                await self.kg.add_strategy_lineage(parent2.strategy_id, child.strategy_id, "crossover_p2")

        # 5. Integrate new offspring
        for child in new_strats:
            self.add_strategy(child)
            await self.archive.save_strategy(child.strategy_id, child.ecosystem_id, child.model_dump(), child.current_fitness, child.parent_ids)
            await self.kg.create_node("Strategy", {"strategy_id": child.strategy_id, "status": "active"})
