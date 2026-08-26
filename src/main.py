"""ASGI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from microforge.infrastructure.inbound.api.v1.routes import router

ALLOWED_ORIGINS = [
    "http://localhost:4321",
    "http://127.0.0.1:4321",
]

app = FastAPI(title="microforge API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")
