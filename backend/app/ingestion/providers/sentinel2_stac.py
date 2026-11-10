"""Copernicus Sentinel-2 Level-2A STAC catalog provider.

Queries Element84 Earth Search STAC API for Sentinel-2 MSI surface reflectance scenes,
extracting granule metadata, cloud coverage, acquisition timestamps, and band asset URLs.

Scientific and Provenance Requirements (per AGENTS.md, AI_SPEC.md, DATA_SOURCES.md):
- Retains scene/product identifier (e.g., S2A_MSIL2A_...)
- Retains acquisition UTC timestamp.
- Never fabricates cloud-free observations when scenes are cloudy or absent.
- Preserves explicit cloud cover percentage and quality flags.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

from app.ingestion.providers.base import BaseProvider, ProviderFetchResult


class Sentinel2STACProvider(BaseProvider):
    """Client for querying Sentinel-2 Level-2A STAC items."""

    STAC_SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
    COLLECTION_ID = "sentinel-2-l2a"

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    @property
    def provider_name(self) -> str:
        return "Copernicus Sentinel-2 L2A (STAC)"

    def health_check(self) -> bool:
        """Verify STAC catalog reachability."""
        try:
            url = "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a"
            req = urllib.request.Request(url, headers={"User-Agent": "FarmShield-AI/1.0"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def search_scenes(
        self,
        bbox: List[float],
        start_date: str,
        end_date: str,
        max_cloud_cover_pct: float = 40.0,
        limit: int = 5,
        fallback_fixture: Optional[Dict[str, Any]] = None,
    ) -> ProviderFetchResult:
        """Search Sentinel-2 L2A STAC catalog for scenes intersecting a bounding box.

        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat] in EPSG:4326.
            start_date: ISO date string (e.g. '2024-10-01').
            end_date: ISO date string (e.g. '2024-11-01').
            max_cloud_cover_pct: Maximum permissible cloud cover percentage (0-100).
            limit: Maximum number of scenes to return.
            fallback_fixture: Optional recorded STAC JSON fixture for offline use.

        Returns:
            ProviderFetchResult with STAC items.
        """
        retrieved_at = datetime.now(timezone.utc)
        payload_request = {
            "collections": [self.COLLECTION_ID],
            "bbox": bbox,
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "query": {
                "eo:cloud_cover": {"lte": max_cloud_cover_pct}
            },
            "limit": max(1, min(limit, 20)),
        }

        try:
            req_data = json.dumps(payload_request).encode("utf-8")
            req = urllib.request.Request(
                self.STAC_SEARCH_URL,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/geo+json",
                    "User-Agent": "FarmShield-AI/1.0 (Earth Observation Ingestion)",
                },
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                status_code = resp.status
                payload = json.loads(resp.read().decode("utf-8"))
                return ProviderFetchResult(
                    provider_name=self.provider_name,
                    endpoint_url=self.STAC_SEARCH_URL,
                    retrieved_at=retrieved_at,
                    status_code=status_code,
                    payload=payload,
                    is_live=True,
                    metadata={
                        "bbox": bbox,
                        "date_range": f"{start_date} to {end_date}",
                        "max_cloud_cover_pct": max_cloud_cover_pct,
                    },
                )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as err:
            if fallback_fixture is not None:
                return ProviderFetchResult(
                    provider_name=self.provider_name,
                    endpoint_url=self.STAC_SEARCH_URL,
                    retrieved_at=retrieved_at,
                    status_code=200,
                    payload=fallback_fixture,
                    is_live=False,
                    metadata={
                        "bbox": bbox,
                        "note": "Loaded from recorded fallback fixture due to network unavailability",
                        "network_error": str(err),
                    },
                )
            return ProviderFetchResult(
                provider_name=self.provider_name,
                endpoint_url=self.STAC_SEARCH_URL,
                retrieved_at=retrieved_at,
                status_code=503,
                payload={},
                is_live=False,
                error_message=f"Sentinel-2 STAC search failed: {err}",
            )
