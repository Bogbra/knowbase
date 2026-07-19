"""Unit tests for account deletion (three-case workspace rule) and export safety.

All DB and Redis access is mocked — no infrastructure required.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ConflictError, InvalidCredentialsError
from app.db.models.workspace import WorkspaceMemberRole
from app.schemas.account import ExportApiKey
from app.services.account_service import AccountService


def _make_service() -> tuple[AccountService, AsyncMock, AsyncMock]:
    db = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    redis = AsyncMock()
    redis.scan = AsyncMock(return_value=(0, []))
    return AccountService(db, redis), db, redis


def _membership(
    workspace_id: uuid.UUID,
    role: WorkspaceMemberRole = WorkspaceMemberRole.owner,
) -> MagicMock:
    m = MagicMock()
    m.workspace_id = workspace_id
    m.role = role
    return m


def _workspace(workspace_id: uuid.UUID, name: str = "My Workspace") -> MagicMock:
    w = MagicMock()
    w.id = workspace_id
    w.name = name
    return w


def _user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.hashed_password = "hashed"
    return u


class TestThreeCaseWorkspaceDeletion:
    async def test_sole_member_workspace_is_deleted(self) -> None:
        """Case 1: sole member → workspace object deleted (cascade handles DB contents)."""
        service, db, _ = _make_service()
        ws_id = uuid.uuid4()
        user = _user()

        with (
            patch("app.services.account_service.verify_password", return_value=True),
            patch("app.services.account_service.WorkspaceRepository") as mock_ws_repo_cls,
            patch("app.services.account_service.DocumentRepository") as mock_doc_repo_cls,
        ):
            ws_repo = mock_ws_repo_cls.return_value
            ws_repo.get_memberships_for_user = AsyncMock(
                return_value=[_membership(ws_id, WorkspaceMemberRole.owner)]
            )
            ws_repo.get_members = AsyncMock(return_value=[MagicMock()])  # sole member
            ws_repo.get_by_id = AsyncMock(return_value=_workspace(ws_id))

            doc_repo = mock_doc_repo_cls.return_value
            doc_repo.get_by_workspace = AsyncMock(return_value=[])

            await service.delete_account(user, "password")

        db.delete.assert_called()
        deleted_objects = [call.args[0] for call in db.delete.call_args_list]
        assert any(getattr(obj, "id", None) == ws_id for obj in deleted_objects)

    async def test_shared_non_owner_membership_removed(self) -> None:
        """Case 2: non-owner member of shared workspace → membership deleted, workspace intact."""
        service, db, _ = _make_service()
        ws_id = uuid.uuid4()
        user = _user()
        membership = _membership(ws_id, WorkspaceMemberRole.editor)

        with (
            patch("app.services.account_service.verify_password", return_value=True),
            patch("app.services.account_service.WorkspaceRepository") as mock_ws_repo_cls,
            patch("app.services.account_service.DocumentRepository"),
        ):
            ws_repo = mock_ws_repo_cls.return_value
            ws_repo.get_memberships_for_user = AsyncMock(return_value=[membership])
            ws_repo.get_members = AsyncMock(
                return_value=[MagicMock(), MagicMock()]  # two members → shared
            )

            await service.delete_account(user, "password")

        deleted_objects = [call.args[0] for call in db.delete.call_args_list]
        assert membership in deleted_objects
        assert not any(getattr(obj, "id", None) == ws_id for obj in deleted_objects)

    async def test_owner_of_shared_workspace_raises_409(self) -> None:
        """Case 3: owner of shared workspace → ConflictError(409) before any deletion."""
        service, db, _ = _make_service()
        ws_id = uuid.uuid4()
        user = _user()

        with (
            patch("app.services.account_service.verify_password", return_value=True),
            patch("app.services.account_service.WorkspaceRepository") as mock_ws_repo_cls,
            patch("app.services.account_service.DocumentRepository"),
        ):
            ws_repo = mock_ws_repo_cls.return_value
            ws_repo.get_memberships_for_user = AsyncMock(
                return_value=[_membership(ws_id, WorkspaceMemberRole.owner)]
            )
            ws_repo.get_members = AsyncMock(
                return_value=[MagicMock(), MagicMock()]  # shared → owner → 409
            )
            ws_repo.get_by_id = AsyncMock(return_value=_workspace(ws_id, "Shared WS"))

            with pytest.raises(ConflictError) as exc_info:
                await service.delete_account(user, "password")

        assert exc_info.value.status_code == 409
        assert "Shared WS" in exc_info.value.detail
        db.delete.assert_not_called()

    async def test_wrong_password_raises_401(self) -> None:
        """Wrong password confirmation → InvalidCredentialsError before touching the DB."""
        service, db, _ = _make_service()
        user = _user()

        with patch("app.services.account_service.verify_password", return_value=False):
            with pytest.raises(InvalidCredentialsError):
                await service.delete_account(user, "wrong")

        db.delete.assert_not_called()


class TestExportDoesNotLeakSensitiveData:
    def test_export_api_key_schema_has_no_key_hash_field(self) -> None:
        """ExportApiKey must never include key_hash — verify at schema level."""
        assert "key_hash" not in ExportApiKey.model_fields

    def test_export_api_key_schema_has_no_raw_key_field(self) -> None:
        """ExportApiKey must not include a raw key field either."""
        assert "key" not in ExportApiKey.model_fields
