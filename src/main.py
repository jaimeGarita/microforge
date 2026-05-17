"""ASGI application entrypoint."""

from fastapi import FastAPI

from microforge.infrastructure.inbound.api.v1.routes import router

app = FastAPI(title="microforge API")
app.include_router(router, prefix="/api/v1")
