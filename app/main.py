from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router.blockradar import blockradar

from .router.paycrest import paycrest, transaction, webhook
from .router import user, auth, offramp

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Looprail API"}

app.include_router(user.router)
app.include_router(auth.router)

app.include_router(offramp.router)

app.include_router(paycrest.router)
app.include_router(transaction.router)
app.include_router(webhook.router)

app.include_router(blockradar.router)