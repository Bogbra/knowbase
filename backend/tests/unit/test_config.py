import pytest
from pydantic import ValidationError

from app.core.config import Settings


class TestSettings:
    def test_defaults_are_sane(self) -> None:
        s = Settings()
        assert s.APP_NAME == "Knowbase"
        assert s.ALGORITHM == "HS256"
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_parse_origins_from_string(self) -> None:
        s = Settings(ALLOWED_ORIGINS="http://localhost:3000,http://localhost:3001")
        assert len(s.ALLOWED_ORIGINS) == 2

    def test_is_production_false_by_default(self) -> None:
        s = Settings()
        assert not s.is_production

    def test_is_production_true_when_set(self) -> None:
        s = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            ALLOWED_ORIGINS="https://app.knowbase.dev",
        )
        assert s.is_production

    def test_dev_without_secret_key_auto_generates(self) -> None:
        s = Settings(SECRET_KEY="")
        assert s.SECRET_KEY != ""

    def test_production_without_secret_key_raises(self) -> None:
        with pytest.raises(ValidationError, match="SECRET_KEY"):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="",
                ALLOWED_ORIGINS="https://app.knowbase.dev",
            )

    def test_production_with_secret_key_succeeds(self) -> None:
        s = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            ALLOWED_ORIGINS="https://app.knowbase.dev",
        )
        assert s.SECRET_KEY == "a" * 32

    def test_production_without_allowed_origins_raises(self) -> None:
        with pytest.raises(ValidationError, match="ALLOWED_ORIGINS"):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="a" * 32,
                ALLOWED_ORIGINS=[],
            )

    def test_production_partial_s3_config_raises(self) -> None:
        with pytest.raises(ValidationError, match="S3_ACCESS_KEY_ID"):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="a" * 32,
                ALLOWED_ORIGINS="https://app.knowbase.dev",
                S3_ACCESS_KEY_ID="key-without-secret",
                S3_SECRET_ACCESS_KEY="",
            )

    def test_production_full_s3_config_succeeds(self) -> None:
        s = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            ALLOWED_ORIGINS="https://app.knowbase.dev",
            S3_ACCESS_KEY_ID="key",
            S3_SECRET_ACCESS_KEY="secret",
        )
        assert s.is_production

    def test_production_no_s3_config_succeeds(self) -> None:
        s = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            ALLOWED_ORIGINS="https://app.knowbase.dev",
        )
        assert s.is_production
