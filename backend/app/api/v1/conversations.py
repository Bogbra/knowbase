import asyncio
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_dep
from app.db.models.conversation import MessageRole
from app.db.models.user import User
from app.db.repositories.agent_repository import AgentRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import (
    ConversationCreate,
    ConversationRead,
    ConversationUpdate,
    MessageCreate,
    MessageRead,
    MessageSentRead,
)
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["conversations"])

_DEFAULT_TITLE = "New conversation"


def _service(db: AsyncSession = Depends(get_db_dep)) -> ConversationService:
    return ConversationService(db)


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(_service),
) -> ConversationRead:
    conv = await service.create(body.workspace_id, current_user.id, body.title)
    return ConversationRead.model_validate(conv)


@router.get("/workspaces/{workspace_id}/conversations", response_model=list[ConversationRead])
async def list_conversations(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(_service),
) -> list[ConversationRead]:
    convs = await service.list_by_workspace(workspace_id, current_user.id)
    return [ConversationRead.model_validate(c) for c in convs]


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(_service),
) -> ConversationRead:
    conv = await service.get(conversation_id, current_user.id)
    return ConversationRead.model_validate(conv)


@router.patch("/conversations/{conversation_id}", response_model=ConversationRead)
async def rename_conversation(
    conversation_id: uuid.UUID,
    body: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(_service),
    db: AsyncSession = Depends(get_db_dep),
) -> ConversationRead:
    await service.get(conversation_id, current_user.id)
    repo = ConversationRepository(db)
    updated = await repo.update_title(conversation_id, body.title)
    await db.commit()
    conv = updated or await service.get(conversation_id, current_user.id)
    return ConversationRead.model_validate(conv)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(_service),
) -> None:
    await service.delete(conversation_id, current_user.id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(_service),
) -> list[MessageRead]:
    messages = await service.list_messages(conversation_id, current_user.id)
    return [MessageRead.model_validate(m) for m in messages]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageSentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    conversation_id: uuid.UUID,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(_service),
    db: AsyncSession = Depends(get_db_dep),
) -> MessageSentRead:
    message = await service.add_message(conversation_id, current_user.id, body.role, body.content)

    run_id: uuid.UUID | None = None

    if body.role == MessageRole.user:
        conv_repo = ConversationRepository(db)
        conversation = await conv_repo.get_by_id(conversation_id)
        if conversation is not None:
            # Auto-title: set title from first user message
            if conversation.title == _DEFAULT_TITLE:
                auto_title = body.content[:60].strip()
                if len(body.content) > 60:
                    auto_title += "…"
                await conv_repo.update_title(conversation_id, auto_title)

            agent_repo = AgentRepository(db)
            run = await agent_repo.create_run(conversation_id, message.id)
            await db.commit()
            run_id = run.id

            workspace_id = conversation.workspace_id
            user_id = current_user.id
            captured_run_id = run.id

            async def _trigger() -> None:
                from app.agents.runner import run_agent

                await run_agent(
                    conversation_id=conversation_id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    run_id=captured_run_id,
                )

            asyncio.create_task(_trigger())

    return MessageSentRead(
        message=MessageRead.model_validate(message),
        run_id=run_id,
    )
