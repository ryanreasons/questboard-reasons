from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json, os

try:
    from .database import initialize_database
    from .auth import AuthUser, get_current_user, require_parent, router as auth_router
except ImportError:  # Docker runtime imports modules from /app directly.
    from database import initialize_database
    from auth import AuthUser, get_current_user, require_parent, router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_DATA_DIR   = os.environ.get("QUESTBOARD_DATA", "/data")
STATE_FILE  = os.path.join(_DATA_DIR, "state.json")
CONFIG_FILE = os.path.join(_DATA_DIR, "config.json")


def read_json(path):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


@app.get("/state")
def get_state(_: AuthUser = Depends(get_current_user)):
    return read_json(STATE_FILE) or {}


@app.post("/state")
async def post_state(
    request: Request,
    _: AuthUser = Depends(get_current_user),
):
    # Transitional compatibility endpoint. It now requires a real session,
    # while fine-grained per-action authorization remains a later hardening step.
    data = await request.json()
    if not isinstance(data, dict):
        return {"ok": False, "error": "invalid"}
    write_json(STATE_FILE, data)
    return {"ok": True}


@app.get("/config")
def get_config(_: AuthUser = Depends(get_current_user)):
    config = read_json(CONFIG_FILE)
    if config is None:
        return {"needs_setup": True}
    return config


@app.post("/config")
async def post_config(
    request: Request,
    _: AuthUser = Depends(require_parent),
):
    data = await request.json()
    if not isinstance(data, dict):
        return {"ok": False, "error": "invalid"}
    write_json(CONFIG_FILE, data)
    return {"ok": True}
