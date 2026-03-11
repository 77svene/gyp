import time
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class Observation(BaseModel):
    """An observation recorded by an agent."""
    timestamp: float = Field(default_factory=time.time)
    source: str
    content: Any
    relevance_score: float = 1.0

class MemoryEntry(BaseModel):
    """A generic entry in an agent's working memory."""
    id: str
    timestamp: float = Field(default_factory=time.time)
    category: str
    data: Dict[str, Any]

class WorkingMemory(BaseModel):
    """
    Short-Term Working Memory Per Agent.
    Maintains immediate operational context for ongoing tasks and conversations.
    """
    agent_id: str
    current_goals: List[str] = Field(default_factory=list)
    recent_observations: List[Observation] = Field(default_factory=list)
    active_plans: List[Dict[str, Any]] = Field(default_factory=list)
    pending_actions: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)

    max_observations: int = 50
    max_history: int = 20

    def add_observation(self, observation: Observation):
        """Add an observation, maintaining the capacity limit based on time-decayed importance/relevance."""
        self.recent_observations.append(observation)
        if len(self.recent_observations) > self.max_observations:
            # Simple retention policy: drop oldest (or lowest relevance)
            # A more sophisticated approach would externalize to long-term memory
            self.recent_observations.sort(key=lambda x: (x.relevance_score, x.timestamp), reverse=True)
            self.recent_observations.pop()

    def add_conversation_turn(self, role: str, content: str):
        """Record a turn in the conversation history."""
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)

    def set_goals(self, goals: List[str]):
        """Update current active goals."""
        self.current_goals = goals

    def clear(self):
        """Clear the working memory (e.g., on agent restart)."""
        self.current_goals.clear()
        self.recent_observations.clear()
        self.active_plans.clear()
        self.pending_actions.clear()
        self.conversation_history.clear()
