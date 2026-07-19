"""Idempotent seed script — runs on every startup, skips if data already present."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.conversation import Conversation, Message, MessageRole
from app.db.models.memory import Memory, MemoryScope
from app.db.models.task import Task, TaskStatus
from app.db.models.user import User, UserRole
from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceMemberRole
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

_ADMIN_EMAIL = "admin@knowbase.dev"
_ADMIN_PASSWORD = "Admin1234!"
_WORKSPACE_NAME = "AI Research 2025"


async def run_seed() -> None:
    """Entry point — called from app lifespan. Skips silently if already seeded."""
    async with AsyncSessionLocal() as session:
        if await _already_seeded(session):
            return
        logger.info("seed_start")
        try:
            admin = await _create_admin(session)
            workspace = await _create_workspace(session, admin)
            await _create_conversations(session, admin, workspace)
            await _create_memories(session, admin, workspace)
            await _create_tasks(session, workspace)
            await session.commit()
            logger.info("seed_complete")
        except Exception:
            await session.rollback()
            logger.exception("seed_failed")


async def _already_seeded(session: AsyncSession) -> bool:
    result = await session.execute(select(User).where(User.email == _ADMIN_EMAIL))
    return result.scalar_one_or_none() is not None


async def _create_admin(session: AsyncSession) -> User:
    admin = User(
        id=uuid.uuid4(),
        email=_ADMIN_EMAIL,
        hashed_password=hash_password(_ADMIN_PASSWORD),
        role=UserRole.admin,
        is_active=True,
    )
    session.add(admin)
    await session.flush()
    return admin


async def _create_workspace(session: AsyncSession, admin: User) -> Workspace:
    workspace = Workspace(
        id=uuid.uuid4(),
        name=_WORKSPACE_NAME,
        owner_id=admin.id,
    )
    session.add(workspace)
    await session.flush()

    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=admin.id,
        role=WorkspaceMemberRole.owner,
    )
    session.add(member)
    await session.flush()
    return workspace


async def _create_conversations(session: AsyncSession, admin: User, workspace: Workspace) -> None:
    conv1 = Conversation(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=admin.id,
        title="Was ist ein Transformer-Modell?",
    )
    conv2 = Conversation(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=admin.id,
        title="Retrieval-Augmented Generation erklärt",
    )
    session.add_all([conv1, conv2])
    await session.flush()

    messages: list[Message] = [
        Message(
            id=uuid.uuid4(),
            conversation_id=conv1.id,
            role=MessageRole.user,
            content="Was ist ein Transformer-Modell und wie funktioniert Attention?",
        ),
        Message(
            id=uuid.uuid4(),
            conversation_id=conv1.id,
            role=MessageRole.assistant,
            content=(
                "Ein Transformer ist eine neuronale Netzarchitektur, die auf dem "
                "Self-Attention-Mechanismus basiert. Anstatt Sequenzen schrittweise "
                "zu verarbeiten (wie RNNs), betrachtet ein Transformer alle Positionen "
                "gleichzeitig und berechnet für jede Position, wie relevant alle anderen "
                "Positionen sind — das nennt sich Attention.\n\n"
                "Der Query-Key-Value-Mechanismus funktioniert so: Jedes Token erzeugt "
                "drei Vektoren (Q, K, V). Die Attention-Gewichte entstehen durch das "
                "Skalarprodukt von Q und K, normalisiert durch Softmax. Das Ergebnis "
                "gewichtet dann die V-Vektoren."
            ),
        ),
        Message(
            id=uuid.uuid4(),
            conversation_id=conv2.id,
            role=MessageRole.user,
            content="Erkläre mir Retrieval-Augmented Generation (RAG) in einfachen Worten.",
        ),
        Message(
            id=uuid.uuid4(),
            conversation_id=conv2.id,
            role=MessageRole.assistant,
            content=(
                "RAG kombiniert zwei Fähigkeiten: Suche und Sprachgenerierung.\n\n"
                "**So funktioniert es:**\n"
                "1. Deine Frage wird in einen Vektor umgewandelt (Embedding)\n"
                "2. Ähnliche Textpassagen werden aus einer Datenbank gesucht\n"
                "3. Diese Passagen werden dem Sprachmodell als Kontext übergeben\n"
                "4. Das Modell generiert eine Antwort basierend auf diesem Kontext\n\n"
                "Der Vorteil: Das Modell muss nicht alles auswendig wissen — "
                "es kann auf aktuellen, firmeninternen Dokumenten basieren."
            ),
        ),
    ]
    session.add_all(messages)
    await session.flush()


async def _create_memories(session: AsyncSession, admin: User, workspace: Workspace) -> None:
    memories_data: list[dict[str, Any]] = [
        {
            "scope": MemoryScope.workspace,
            "content": "Der Nutzer bevorzugt Erklärungen auf Deutsch mit konkreten Codebeispielen.",
            "tags": ["präferenz", "sprache"],
        },
        {
            "scope": MemoryScope.workspace,
            "content": "Workspace fokussiert auf Machine Learning und NLP-Forschung aus 2024-2025.",
            "tags": ["thema", "fokus"],
        },
        {
            "scope": MemoryScope.global_,
            "content": "Transformer-Architekturen sind das Fundament moderner LLMs (GPT, Claude, Gemini).",  # noqa: E501
            "tags": ["ml", "transformer"],
        },
        {
            "scope": MemoryScope.workspace,
            "content": "pgvector mit HNSW-Index wird für semantische Suche verwendet (1536-dim).",
            "tags": ["technik", "vektor"],
        },
        {
            "scope": MemoryScope.global_,
            "content": "RAG (Retrieval-Augmented Generation) verbessert Antwortqualität durch Dokumentensuche.",  # noqa: E501
            "tags": ["rag", "retrieval"],
        },
    ]

    for m in memories_data:
        memory = Memory(
            id=uuid.uuid4(),
            user_id=admin.id,
            workspace_id=workspace.id if m["scope"] != MemoryScope.global_ else None,
            scope=m["scope"],
            content=m["content"],
            tags=m["tags"],
        )
        session.add(memory)

    await session.flush()


async def _create_tasks(session: AsyncSession, workspace: Workspace) -> None:
    tasks_data = [
        {
            "title": "Neue Dokumente zum RAG-Pipeline testen",
            "description": "5 wissenschaftliche Papers hochladen und Retrieval-Qualität prüfen.",
            "status": TaskStatus.pending,
        },
        {
            "title": "Memory-Agent Evaluierung",
            "description": "Erinnerungen korrekt über Gespräche hinweg prüfen.",
            "status": TaskStatus.in_progress,
        },
        {
            "title": "Prometheus Dashboard einrichten",
            "description": "Grafana für http_request_duration_seconds und agent_runs_total.",
            "status": TaskStatus.completed,
        },
    ]

    for t in tasks_data:
        task = Task(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            title=t["title"],
            description=t["description"],
            status=t["status"],
        )
        session.add(task)

    await session.flush()
