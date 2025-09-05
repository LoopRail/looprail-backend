from fastapi import FastAPI

from src.api.router import auth_router, user_router

app = FastAPI(
    title="Looprail Backend",
    description="LoopRail's backend service",
    version="0.1.0",
)

app.include_router(user_router.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")
