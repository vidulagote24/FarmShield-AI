"""Abstract base interface and common primitives for data ingestion providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class ProviderFetchResult:
    """Standard container for raw data returned by an external provider."""

    provider_name: str
    endpoint_url: str
    retrieved_at: datetime
    status_code: int
    payload: Dict[str, Any]
    is_live: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base class for all FarmShield AI data ingestion providers."""

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the data provider (e.g., 'Open-Meteo', 'Earth Search STAC')."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Verify reachability and operational status of the provider."""
        pass
