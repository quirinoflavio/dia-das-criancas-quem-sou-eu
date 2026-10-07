"""Ponto de entrada do FastAPI: monta rotas, WS, static do frontend e tasks de fundo."""
from __future__ import annotations

import contextlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.realtime.hub import Hub
from app.routes import rooms as rooms_routes
from app.routes import ws as ws_routes
from app.services.cleanup import cleanup_loop
from app.services.room_manager import RoomManager

STATIC_DIR = Path(__file__).parent / "static"


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    hub = Hub()
    manager = RoomManager(settings=settings, hub=hub)
    manager.load_from_disk()
    app.state.settings = settings
    app.state.hub = hub
    app.state.manager = manager
    from app.services.ratelimit import RateLimiter

    app.state.rl_create = RateLimiter(max_events=10, window_seconds=60.0)
    app.state.rl_upload = RateLimiter(max_events=20, window_seconds=60.0)
    cleanup_task = None
    import asyncio

    cleanup_task = asyncio.create_task(cleanup_loop(manager))
    try:
        yield
    finally:
        cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cleanup_task


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Quem Sou Eu?", version="0.1.0", lifespan=lifespan)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "name": "quem-sou-eu"}

    app.include_router(rooms_routes.router)
    app.include_router(ws_routes.router)

    # Servir o frontend buildado (se existir), com fallback para index (SPA).
    if STATIC_DIR.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=STATIC_DIR / "assets"),
            name="assets",
        )

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            # Não interceptar rotas de API/WS.
            if full_path.startswith(("api/", "ws/")):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            candidate = STATIC_DIR / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
