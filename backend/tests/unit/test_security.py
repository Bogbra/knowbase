import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self) -> None:
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", hashed)

    def test_wrong_password_rejected(self) -> None:
        hashed = hash_password("original")
        assert not verify_password("wrong", hashed)


class TestJWT:
    def test_access_token_roundtrip(self) -> None:
        token = create_access_token("user-abc")
        payload = decode_token(token)
        assert payload["sub"] == "user-abc"
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self) -> None:
        token, jti = create_refresh_token("user-xyz")
        payload = decode_token(token)
        assert payload["sub"] == "user-xyz"
        assert payload["type"] == "refresh"
        assert payload["jti"] == jti

    def test_invalid_token_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token("not.a.real.token")

    def test_tampered_token_raises_value_error(self) -> None:
        token = create_access_token("user-abc")
        tampered = token[:-4] + "xxxx"
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token(tampered)
