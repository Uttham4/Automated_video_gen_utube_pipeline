import hmac
import ipaddress
import logging
import secrets
from pathlib import Path

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app.config.settings import settings
from app.database.repository import repo

logger = logging.getLogger(__name__)

app = FastAPI(title="Kids Animated Video Studio Server")
templates = Jinja2Templates(directory=str(settings.APP_DIR / "web" / "templates"))
csrf_token = secrets.token_urlsafe(32)


@app.middleware("http")
async def restrict_to_local_clients(request: Request, call_next):
    client_host = request.client.host if request.client else ""
    try:
        is_local_client = ipaddress.ip_address(client_host).is_loopback
    except ValueError:
        is_local_client = False

    if (
        not is_local_client
        or request.url.hostname not in {"localhost", "127.0.0.1", "::1"}
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "Dashboard is available on this PC only"},
        )

    return await call_next(request)


def require_same_origin_form(request: Request) -> None:
    origin = request.headers.get("origin")
    expected_origin = str(request.base_url).rstrip("/")
    supplied_token = request.headers.get("x-csrf-token", "")
    if (
        not origin
        or origin.rstrip("/").lower() != expected_origin.lower()
        or not hmac.compare_digest(supplied_token, csrf_token)
    ):
        raise HTTPException(status_code=403, detail="Invalid request origin or CSRF token")

class GenerateRequest(BaseModel):
    topic: str

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    videos = repo.list_all(limit=50)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"videos": videos, "csrf_token": csrf_token},
    )

@app.get("/api/videos")
async def list_videos():
    return [v.__dict__ for v in repo.list_all(limit=50)]

@app.get("/api/media")
async def serve_media(path: str):
    try:
        file_path = Path(path).resolve(strict=True)
    except (OSError, RuntimeError):
        raise HTTPException(status_code=404, detail="File not found")
    allowed_roots = (
        settings.SCENES_DIR,
        settings.AUDIO_DIR,
        settings.RENDERS_DIR,
        settings.THUMBNAILS_DIR,
    )
    if not file_path.is_file() or not any(
        file_path.is_relative_to(root.resolve()) for root in allowed_roots
    ):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path))

@app.post("/api/generate")
async def trigger_generation(
    req: GenerateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    require_same_origin_form(request)
    from app.workflow.generate import generate_pipeline
    import uuid
    episode_id = f"ep_{uuid.uuid4().hex[:8]}"

    # Run in background
    background_tasks.add_task(generate_pipeline.run_generation_workflow, req.topic, episode_id)
    return {"status": "started", "episode_id": episode_id, "topic": req.topic}

@app.post("/api/approve/{episode_id}")
async def approve_episode(
    episode_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
):
    require_same_origin_form(request)
    from app.database.models import VideoStatus
    from app.workflow.publish import publish_pipeline
    video = repo.get_by_episode_id(episode_id)
    if not video:
        raise HTTPException(status_code=404, detail="Episode not found")
    if video.status != VideoStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail="Only episodes waiting for approval can be published",
        )
    background_tasks.add_task(publish_pipeline.publish_video, episode_id)
    return {"status": "approved", "message": f"Episode {episode_id} approved for YouTube publishing!"}

@app.post("/api/reject/{episode_id}")
async def reject_episode(episode_id: str, request: Request):
    require_same_origin_form(request)
    from app.database.models import VideoStatus
    video = repo.get_by_episode_id(episode_id)
    if not video:
        raise HTTPException(status_code=404, detail="Episode not found")
    if video.status != VideoStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail="Only episodes waiting for approval can be rejected",
        )
    if not repo.transition_status(
        episode_id,
        expected_statuses=[VideoStatus.WAITING_APPROVAL],
        status=VideoStatus.REJECTED,
    ):
        raise HTTPException(
            status_code=409,
            detail="Episode is no longer waiting for approval",
        )
    return {"status": "rejected", "message": f"Episode {episode_id} rejected."}
