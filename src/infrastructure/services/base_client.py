import json
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple, Type

from httpx import AsyncClient, ConnectError, Response, TimeoutException
from pydantic import BaseModel

from src.infrastructure import get_logger
from src.types import Error, HTTPMethod, httpError

logger = get_logger(__name__)

type T = BaseModel


class BaseClient(ABC):
    """A base client for interacting with APIs."""

    def __init__(self, path: str) -> None:
        """Initializes the Base client.

        Args:
            path: The base path for the API endpoints.
        """
        self._path = path
        logger.debug("BaseClient initialized with path: %s", path)

    @abstractmethod
    def _get_base_url(self) -> str:
        """Returns the base URL for the API."""
        logger.debug("Getting base URL.")
        raise NotImplementedError

    @abstractmethod
    def _get_headers(self) -> dict[str, str]:
        """Returns the headers for the API request."""
        logger.debug("Getting headers.")
        raise NotImplementedError

    def _get_url(self, path_suffix: str = "") -> str:
        """Constructs the full URL for an API endpoint.

        Args:
            path_suffix: The suffix to append to the base path.

        Returns:
            The full URL.
        """
        url = f"{self._get_base_url()}{self._path}{path_suffix}"
        logger.debug("Constructed URL: %s with suffix: %s", url, path_suffix)
        return url

    async def _send(
        self,
        url: str,
        method: str,
        *,
        data: dict[str, Any] | None = None,
        req_params: dict[str, Any] | None = None,
    ) -> Tuple[Optional[Response], Error]:
        """Sends an HTTP request to the API.

        Args:
            url: The URL to send the request to.
            method: The HTTP method to use.
            data: The data to send with the request.
            req_params: The request parameters.

        Returns:
            A tuple containing the HTTP response and an error, if any.
        """
        logger.debug("Sending %s request to %s with data: %s and params: %s", method, url, data, req_params)
        headers = self._get_headers()
        async with AsyncClient() as client:
            try:
                logger.debug("Sending %s request to %s", method, url)
                res = await client.request(
                    method,
                    url,
                    headers=headers,
                    json=data,
                    params=req_params,
                    timeout=30,
                )
                logger.debug("Received response from %s with status code: %s", url, res.status_code)
                return res, None
            except (
                TimeoutException,
                ConnectError,
                json.JSONDecodeError,
                TypeError,
            ) as e:
                logger.error("Request to %s failed: %s", url, e, exc_info=True)
                return None, httpError(code=504, message="Request to %s failed" % url)

    def _process_response(
        self, res: Response, response_model: Type[T]
    ) -> Tuple[Optional[T], Error]:
        """Processes the HTTP response from the API.

        Args:
            res: The HTTP response.
            response_model: The Pydantic model to validate the response against.

        Returns:
            A tuple containing the response data and an error, if any.
        """
        logger.debug("Processing response for URL: %s with status code: %s", res.url, res.status_code)
        if res.status_code >= 500:
            logger.error(
                "Service not available (status code: %s) for request to %s",
                res.status_code,
                res.url,
            )
            return None, httpError(
                code=res.status_code, message="Service not available %s" % res.status_code
            )

        if not res.is_success:
            logger.error(
                "Request failed (status code: %s): %s for request to %s",
                res.status_code,
                res.text,
                res.url,
            )
            return None, httpError(
                code=res.status_code,
                message="Request failed %s: %s" % (res.status_code, res.text),
            )

        response_data = response_model.model_validate(res.json())
        logger.debug("Successfully processed response for URL: %s", res.url)
        return response_data, None

    async def _get(
        self,
        response_model: Type[T],
        path_suffix: str = "",
        req_params: dict[str, Any] | None = None,
    ) -> Tuple[Optional[T], Error]:
        """Sends a GET request to the API.

        Args:
            response_model: The Pydantic model to validate the response against.
            path_suffix: The suffix to append to the base path.
            req_params: The request parameters.

        Returns:
            A tuple containing the response data and an error, if any.
        """
        logger.debug("Sending GET request with path suffix: %s and params: %s", path_suffix, req_params)
        url = self._get_url(path_suffix)
        res, err = await self._send(url, HTTPMethod.GET, req_params=req_params)
        if err:
            logger.error("GET request to %s failed: %s", url, err.message)
            return None, err
        return self._process_response(res, response_model)

    async def _post(
        self,
        response_model: Type[T],
        path_suffix: str = "",
        data: dict[str, Any] | None = None,
        req_params: dict[str, Any] | None = None,
    ) -> Tuple[Optional[T], Error]:
        """Sends a POST request to the API.

        Args:
            response_model: The Pydantic model to validate the response against.
            path_suffix: The suffix to append to the base path.
            data: The data to send with the request.
            req_params: The request parameters.

        Returns:
            A tuple containing the response data and an error, if any.
        """
        logger.debug("Sending POST request with path suffix: %s, data: %s, and params: %s", path_suffix, data, req_params)
        url = self._get_url(path_suffix)
        res, err = await self._send(
            url, HTTPMethod.POST, data=data, req_params=req_params
        )
        if err:
            logger.error("POST request to %s failed: %s", url, err.message)
            return None, err
        return self._process_response(res, response_model)

    async def _put(
        self,
        response_model: Type[T],
        path_suffix: str = "",
        data: dict[str, Any] | None = None,
        req_params: dict[str, Any] | None = None,
    ) -> Tuple[Optional[T], Error]:
        """Sends a PUT request to the API.

        Args:
            response_model: The Pydantic model to validate the response against.
            path_suffix: The suffix to append to the base path.
            data: The data to send with the request.
            req_params: The request parameters.

        Returns:
            A tuple containing the response data and an error, if any.
        """
        logger.debug("Sending PUT request with path suffix: %s, data: %s, and params: %s", path_suffix, data, req_params)
        url = self._get_url(path_suffix)
        res, err = await self._send(
            url, HTTPMethod.PUT, data=data, req_params=req_params
        )
        if err:
            logger.error("PUT request to %s failed: %s", url, err.message)
            return None, err
        return self._process_response(res, response_model)
