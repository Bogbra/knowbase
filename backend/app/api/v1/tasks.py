import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_dep
from app.db.models.task import TaskStatus
from app.db.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(tags=["tasks"])


def _service(db: AsyncSession = Depends(get_db_dep)) -> TaskService:
    return TaskService(db)


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(_service),
) -> TaskRead:
    task = await service.create(body.workspace_id, current_user.id, body.title, body.description)
    return TaskRead.model_validate(task)


@router.get("/workspaces/{workspace_id}/tasks", response_model=list[TaskRead])
async def list_tasks(
    workspace_id: uuid.UUID,
    status: TaskStatus | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(_service),
) -> list[TaskRead]:
    tasks = await service.list_by_workspace(workspace_id, current_user.id, status)
    return [TaskRead.model_validate(t) for t in tasks]


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(_service),
) -> TaskRead:
    task = await service.get(task_id, current_user.id)
    return TaskRead.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(_service),
) -> TaskRead:
    task = await service.update(
        task_id,
        current_user.id,
        title=body.title,
        description=body.description,
        status=body.status,
        assigned_agent=body.assigned_agent,
    )
    return TaskRead.model_validate(task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(_service),
) -> None:
    await service.delete(task_id, current_user.id)
