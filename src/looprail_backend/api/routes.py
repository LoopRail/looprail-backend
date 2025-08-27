# src/looprail_backend/api/routes.py
# This file defines the API endpoints for the application.
# It acts as the presentation layer, handling HTTP requests and responses.

# This layer should be as thin as possible. Its primary responsibility is to:
# 1. Parse and validate incoming request data (e.g., from JSON payloads).
# 2. Call the appropriate application service with that data.
# 3. Serialize the data returned by the service into an HTTP response (e.g., to JSON).

# It uses a "dependency injection" pattern (FastAPI's `Depends`) to get an instance
# of the application service. This decouples the API from the service instantiation.

# --- Example ---
# The following defines API endpoints for creating and retrieving users.

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.application.services import UserService
from ..core.domain.models import User as DomainUser
from .dependencies import get_user_service

# Create a new router for user-related endpoints
router = APIRouter()

# --- Pydantic Models for API data ---
# These models define the shape of the data for requests and responses.
# They are part of the API layer, not the domain layer, to allow for flexibility.

class UserCreate(BaseModel):
    username: str
    email: str

class UserPublic(BaseModel):
    id: UUID
    username: str
    email: str

    class Config:
        from_attributes = True # Allows creating from a domain model

# --- API Endpoints ---

@router.post("/users/", response_model=UserPublic, status_code=201)
def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """API endpoint to create a new user."""
    try:
        created_user = user_service.create_user(
            username=user_data.username, email=user_data.email
        )
        return created_user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/{user_id}", response_model=UserPublic)
def get_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service)
):
    """API endpoint to retrieve a user by their ID."""
    user = user_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=44, detail="User not found")
    return user
