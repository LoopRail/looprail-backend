from typing import Optional, Tuple
from pydantic import BaseModel

from src.infrastructure.services.base_client import BaseClient
from src.infrastructure.logger import get_logger
from src.types import Error

logger = get_logger(__name__)


class GeolocationData(BaseModel):
    status: str
    country: Optional[str] = None
    countryCode: Optional[str] = None
    region: Optional[str] = None
    regionName: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    as_: Optional[str] = None
    query: str  # The IP address


class GeolocationService(BaseClient):
    """A service for fetching geolocation data from IP addresses using ip-api.com."""

    def __init__(self) -> None:
        """Initializes the GeolocationService."""
        super().__init__(path="")
        logger.debug("GeolocationService initialized.")

    def _get_base_url(self) -> str:
        """Returns the base URL for ip-api.com."""
        return "http://ip-api.com/json/"

    def _get_headers(self) -> dict[str, str]:
        """Returns the headers for ip-api.com."""
        return {"Accept": "application/json"}

    async def get_location(self, ip: str) -> Tuple[Optional[GeolocationData], Error]:
        """Fetches geolocation data for the given IP address.

        Args:
            ip: The IP address to geolocate.

        Returns:
            A tuple containing the GeolocationData and an error, if any.
        """
        logger.debug("Attempting to fetch geolocation for IP: %s", ip)
        
        # Free API usage: http://ip-api.com/json/{query}
        # We append the IP to the base URL
        data, err = await self._get(response_model=GeolocationData, path_suffix=ip)
        
        if err:
            logger.error("Failed to fetch geolocation for IP %s: %s", ip, err.message)
            return None, err
            
        if data.status != "success":
            logger.warning("Geolocation API returned non-success status for IP %s: %s", ip, data.status)
            return data, None # Still return data but it might be empty/error status
            
        logger.info("Successfully fetched geolocation for IP %s: %s, %s, %s", 
                    ip, data.city, data.regionName, data.country)
        return data, None
