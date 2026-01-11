from decimal import Decimal

from src.dtos.base import Base
from src.types.common_types import AssetId


class WithdrawalRequest(Base):
    assetId: AssetId
    amount: Decimal
