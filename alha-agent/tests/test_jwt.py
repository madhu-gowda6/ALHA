"""Tests for JWT validation logic (_get_rsa_key, _validate_jwt)."""
import pytest
from jose import JWTError

import app as app_module
from app import _get_rsa_key


class TestGetRsaKey:
    def test_returns_key_with_matching_kid(self):
        jwks = {"keys": [{"kid": "abc123", "kty": "RSA", "n": "...", "e": "AQAB"}]}
        # Mock a token header with kid=abc123
        import base64, json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "RS256", "kid": "abc123"}).encode()
        ).rstrip(b"=").decode()
        token = f"{header}.payload.sig"
        key = _get_rsa_key(token, jwks)
        assert key is not None
        assert key["kid"] == "abc123"

    def test_returns_none_when_no_matching_kid(self):
        jwks = {"keys": [{"kid": "other-kid", "kty": "RSA"}]}
        import base64, json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "RS256", "kid": "abc123"}).encode()
        ).rstrip(b"=").decode()
        token = f"{header}.payload.sig"
        result = _get_rsa_key(token, jwks)
        assert result is None

    def test_returns_none_for_empty_keys(self):
        import base64, json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "RS256", "kid": "abc123"}).encode()
        ).rstrip(b"=").decode()
        token = f"{header}.payload.sig"
        result = _get_rsa_key(token, {"keys": []})
        assert result is None


class TestValidateJwt:
    @pytest.mark.asyncio
    async def test_raises_jwt_error_on_no_matching_key(self, monkeypatch):
        async def mock_fetch_jwks():
            return {"keys": []}

        monkeypatch.setattr(app_module, "_fetch_jwks", mock_fetch_jwks)
        monkeypatch.setattr(app_module, "_jwks", None)

        import base64, json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "RS256", "kid": "xyz"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(b"{}").rstrip(b"=").decode()
        token = f"{header}.{payload}.fake-sig"

        with pytest.raises(JWTError):
            await app_module._validate_jwt(token)

    @pytest.mark.asyncio
    async def test_raises_jwt_error_on_invalid_signature(self, monkeypatch):
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        from jose import jwk as jose_jwk

        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        public_key = private_key.public_key()
        jwk_dict = jose_jwk.construct(public_key, algorithm="RS256").to_dict()
        jwk_dict["kid"] = "test-kid"
        jwk_dict["kty"] = "RSA"
        jwks = {"keys": [jwk_dict]}

        async def mock_fetch():
            return jwks

        monkeypatch.setattr(app_module, "_fetch_jwks", mock_fetch)
        monkeypatch.setattr(app_module, "_jwks", None)

        # A token with wrong signature
        import base64, json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "RS256", "kid": "test-kid"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "user", "aud": "test-client-id"}).encode()
        ).rstrip(b"=").decode()
        token = f"{header}.{payload}.badsignature"

        with pytest.raises(JWTError):
            await app_module._validate_jwt(token)
