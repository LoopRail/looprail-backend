import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api import v1_router
from src.api.middlewares import RequestLoggerMiddleware
from src.types import Error, error

app = FastAPI(
    title="Looprail Backend",
    description="LoopRail's backend service",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggerMiddleware)
app.include_router(v1_router, prefix="/api")


@app.exception_handler(error)
async def custom_error_handler(request: Request, exc: Error):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": exc.string()},
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
