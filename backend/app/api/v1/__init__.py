from fastapi import APIRouter

from app.api.v1.agent_runs import router as agent_runs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.documents import router as documents_router
from app.api.v1.memories import router as memories_router
from app.api.v1.stream import router as stream_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.workspaces import router as workspaces_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(workspaces_router)
router.include_router(conversations_router)
router.include_router(documents_router)
router.include_router(memories_router)
router.include_router(tasks_router)
router.include_router(agent_runs_router)
router.include_router(stream_router)


@router.get("/ping", tags=["health"])
async def ping() -> dict[str, str]:
    return {"message": "pong"}
