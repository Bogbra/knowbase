import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_dep
from app.db.models.user import User
from app.schemas.memory import MemoryCreate, MemoryRead
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memories", tags=["memories"])


def _service(db: AsyncSession = Depends(get_db_dep)) -> MemoryService:
    return MemoryService(db)


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def create_memory(
    body: MemoryCreate,
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(_service),
) -> MemoryRead:
    memory = await service.create(
        user_id=current_user.id,
        scope=body.scope,
        content=body.content,
        workspace_id=body.workspace_id,
        tags=body.tags,
    )
    return MemoryRead.model_validate(memory)


@router.get("", response_model=list[MemoryRead])
async def list_memories(
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(_service),
) -> list[MemoryRead]:
    memories = await service.list_for_user(current_user.id)
    return [MemoryRead.model_validate(m) for m in memories]


@router.get("/{memory_id}", response_model=MemoryRead)
async def get_memory(
    memory_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(_service),
) -> MemoryRead:
    memory = await service.get(memory_id, current_user.id)
    return MemoryRead.model_validate(memory)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(_service),
) -> None:
    await service.delete(memory_id, current_user.id)
