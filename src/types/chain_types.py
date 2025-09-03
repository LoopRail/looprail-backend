from enum import Enum


class Chain(str, Enum):
    POLYGON = "polygon"
    BASE = "base"
    ETHEREUM = "ethereum"
