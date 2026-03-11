import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base event model for the event-driven nervous system."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    topic: str
    source_agent_id: Optional[str] = None
    ecosystem_id: str = "default"  # Brand or project isolation
    payload: Dict[str, Any]

class PerformanceAnomalyEvent(BaseEvent):
    """Event triggered when a performance anomaly is detected."""
    metric_name: str
    deviation_magnitude: float
    temporal_pattern: str
    historical_context: Dict[str, Any]

class AudienceSignalEvent(BaseEvent):
    """Event triggered by changes in attention patterns or content engagement."""
    signal_type: str
    confidence_score: float
    demographic_segments: List[str]

class CompetitorActivityEvent(BaseEvent):
    """Event triggered when competitor activity is detected."""
    competitor_id: str
    activity_type: str
    assessed_threat_level: str

class CampaignFatigueEvent(BaseEvent):
    """Event indicating declining effectiveness of a campaign."""
    campaign_id: str
    decay_pattern: str
    confidence_score: float

class CapabilityGapEvent(BaseEvent):
    """Event triggered when an agent encounters a task it cannot perform."""
    gap_category: str
    functional_requirements: List[str]
    estimated_complexity: str
    priority_assessment: str

class PlatformOpportunityEvent(BaseEvent):
    """Event indicating a new platform or feature opportunity."""
    platform_name: str
    opportunity_magnitude: float
    integration_complexity: str

class ExperimentResultEvent(BaseEvent):
    """Event generated when an experiment concludes or yields significant results."""
    experiment_id: str
    strategy_id: str
    observed_outcomes: Dict[str, Any]
    statistical_significance: float
