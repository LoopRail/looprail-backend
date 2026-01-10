from typing import Callable, Dict

from src.types.blockrader.webhook_dtos import WebhookEvent, WebhookEventType

WebhookHandler = Callable[[WebhookEvent], None]
HandlerRegistry = Dict[WebhookEventType, WebhookHandler]

_registry: HandlerRegistry = {}


def register(event_type: WebhookEventType) -> Callable[[WebhookHandler], WebhookHandler]:
    def decorator(handler: WebhookHandler) -> WebhookHandler:
        _registry[event_type] = handler
        return handler

    return decorator


def get_registry() -> HandlerRegistry:
    return _registry