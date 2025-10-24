from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.api.dependencies import get_paycrest_service
from src.infrastructure.services.paycrest.paycrest_service import PaycrestService

router = APIRouter(prefix="/offramp", tags=["Offramp"])

