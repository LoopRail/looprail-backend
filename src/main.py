from fastapi import FastAPI

from src.api.router import user_router, auth_router

app = FastAPI(
    title="Looprail Backend",
    description="A backend service demonstrating Clean Architecture.",
    version="0.1.0",
)

app.include_router(user_router.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")

@app.get("/")
def read_root():
    """A simple root endpoint to confirm the API is running."""
    return {"message": "Welcome to the Looprail Backend API!"}