from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from .db import init_db
from .routers import admin, auth, community, connections, help, home, projects, settings, social, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Keystone API", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")

# Everything lives under /api so the Vite proxy and the Vercel rewrite can forward one prefix.
api = APIRouter(prefix="/api")


@api.get("/health")
def health():
    return {"ok": True}


for r in (auth.router, users.router, projects.router, help.router, social.router, connections.router, settings.router, admin.router, home.router, community.router):
    api.include_router(r)

app.include_router(api)
