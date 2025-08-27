# src/looprail_backend/main.py
# This file is the main entry point for the application.

# Its responsibilities are:
# 1. Creating the main FastAPI application instance.
# 2. Including the API routers from the `api` layer.
# 3. (Optionally) Configuring middleware, exception handlers, etc.
# 4. Providing a way to run the application (e.g., with uvicorn).

# This is the file you will point your ASGI server (like uvicorn) to.
# Example: `uvicorn looprail_backend.main:app --reload`

from fastapi import FastAPI

from .api.router import user_router

# Create the FastAPI app instance
app = FastAPI(
    title="Looprail Backend",
    description="A backend service demonstrating Clean Architecture.",
    version="0.1.0",
)

# Include the API router
# This makes all the endpoints defined in `api/routes.py` available.
app.include_router(user_router.router, prefix="/api", tags=["Users"])


@app.get("/")
def read_root():
    """A simple root endpoint to confirm the API is running."""
    return {"message": "Welcome to the Looprail Backend API!"}


# --- How to Run ---
# To run this application, use an ASGI server like uvicorn:
#
# 1. Make sure you have installed the dependencies:
#    pip install -r requirements.txt (or equivalent for your package manager)
#
# 2. Run the server from your project's root directory:
#    uvicorn src.looprail_backend.main:app --reload
#
# The API will be available at http://127.0.0.1:8000
