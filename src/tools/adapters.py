import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class PlatformAdapter(ABC):
    """
    Universal Platform Adapter Architecture Base.
    Exposes standard interfaces to the rest of the system, hiding platform heterogeneity.
    """
    def __init__(self, platform_name: str, credentials: Dict[str, str]):
        self.platform_name = platform_name
        self.credentials = credentials
        self.is_connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection and authenticate with the platform."""
        pass

    @abstractmethod
    async def get_health(self) -> Dict[str, Any]:
        """Health monitor for API availability and credential validity."""
        pass

    @abstractmethod
    async def publish_content(self, content_payload: Dict[str, Any]) -> str:
        """Publish content or execute an action on the platform."""
        pass

    @abstractmethod
    async def fetch_metrics(self, resource_id: str, metric_types: List[str]) -> Dict[str, Any]:
        """Retrieve performance measurement data."""
        pass

    async def disconnect(self):
        """Cleanup resources and connections."""
        self.is_connected = False
        logger.info(f"Disconnected from {self.platform_name}")
