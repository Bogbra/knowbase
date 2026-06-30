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
        s = Settings(ENVIRONMENT="production")
        assert s.is_production
