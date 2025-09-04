from enum import Enum


class Chain(str, Enum):
    polygon = "polygon"
    base = "base"
    ethereum = "ethereum"


class KYCStatus(str, Enum):
    """Represents the KYC status of a user."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
