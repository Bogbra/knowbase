"""Redis cache key patterns and TTL constants."""

import uuid

REFRESH_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
WORKSPACE_MEMBERS_TTL_SECONDS = 5 * 60  # 5 minutes
CONVERSATION_TTL_SECONDS = 60 * 60  # 1 hour


def refresh_token_key(jti: str) -> str:
    return f"refresh:{jti}"


def workspace_members_key(workspace_id: uuid.UUID) -> str:
    return f"workspace:{workspace_id}:members"


def conversation_messages_key(conversation_id: uuid.UUID) -> str:
    return f"conversation:{conversation_id}:messages"


def user_workspaces_key(user_id: uuid.UUID) -> str:
    return f"user:{user_id}:workspaces"


def sse_stream_key(conversation_id: uuid.UUID) -> str:
    return f"sse:{conversation_id}"
