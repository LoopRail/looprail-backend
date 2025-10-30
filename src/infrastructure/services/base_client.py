from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple, Type

from httpx import AsyncClient, ConnectError, Response, TimeoutException
from pydantic import BaseModel

from src.types import Error, HTTPMethod, httpError

type T = BaseModel


class BaseClient(ABC):
    """A base client for interacting with APIs."""

    def __init__(self, path: str) -> None:
        """Initializes the Base client.

        Args:
            path: The base path for the API endpoints.
        """
        self._path = path

    @abstractmethod
    def _get_base_url(self) -> str:
        """Returns the base URL for the API."""
        raise NotImplementedError

    @abstractmethod
    def _get_headers(self) -> dict[str, str]:
        """Returns the headers for the API request."""
        raise NotImplementedError

    def _get_url(self, path_suffix: str = "") -> str:
        """Constructs the full URL for an API endpoint.

        Args:
            path_suffix: The suffix to append to the base path.

        Returns:
            The full URL.
        """
        return f"{self._get_base_url()}{self._path}{path_suffix}"

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
        headers = self._get_headers()
        async with AsyncClient() as client:
            try:
                res = await client.request(
                    method,
                    url,
                    headers=headers,
                    json=data,
                    params=req_params,
                    timeout=30,
                )
                return res, None
            except (TimeoutException, ConnectError):
                return None, httpError(
                    code=504, message=f"Request to {url} failed"
                )

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
        if res.status_code >= 500:
            return None, httpError(
                code=res.status_code, message=f"Service not available {res.status_code}"
            )

        if not res.is_success:
            return None, httpError(
                code=res.status_code,
                message=f"Request failed {res.status_code}: {res.text}",
            )

        response_data = response_model.model_validate(res.json())
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
        url = self._get_url(path_suffix)
        res, err = await self._send(url, HTTPMethod.GET, req_params=req_params)
        if err:
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
        url = self._get_url(path_suffix)
        res, err = await self._send(
            url, HTTPMethod.POST, data=data, req_params=req_params
        )
        if err:
            return None, err
        return self._process_response(res, response_model)


