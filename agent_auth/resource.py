import time
from collections.abc import Callable
from threading import Lock

import httpx
import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class KeyUnavailable(Exception):
    pass


class JwksCache:
    def __init__(self, jwks_url: str, ttl: int = 60, *, clock: Callable[[], float] = time.monotonic):
        self.jwks_url = jwks_url
        self.ttl = ttl
        self._clock = clock
        self._keys: dict[str, jwt.PyJWK] = {}
        self._refresh_at = float("-inf")
        self._unavailable = False
        self._lock = Lock()

    def get(self, kid: str) -> jwt.PyJWK | None:
        with self._lock:
            if self._clock() >= self._refresh_at:
                self._refresh()
            if self._unavailable:
                raise KeyUnavailable
            return self._keys.get(kid)

    def _refresh(self) -> None:
        try:
            response = httpx.get(self.jwks_url, timeout=2, trust_env=False)
            response.raise_for_status()
            keys = {}
            for entry in response.json()["keys"]:
                if entry.get("kty") != "RSA" or entry.get("alg") != "RS256":
                    continue
                if entry.get("use", "sig") != "sig":
                    continue
                kid = entry.get("kid")
                if not isinstance(kid, str) or not kid or kid in keys:
                    raise ValueError("Invalid JWKS key ID")
                keys[kid] = jwt.PyJWK.from_dict(entry, algorithm="RS256")
            if not keys:
                raise ValueError("No compatible signing keys")
        except (httpx.HTTPError, jwt.PyJWTError, KeyError, TypeError, ValueError, AttributeError):
            self._unavailable = True
            self._refresh_at = self._clock() + 2
            return
        self._keys = keys
        self._unavailable = False
        self._refresh_at = self._clock() + self.ttl


class AccessTokenValidator:
    def __init__(self, issuer: str, audience: str, keys: JwksCache):
        self.issuer = issuer
        self.audience = audience
        self.keys = keys

    def validate(self, token: str) -> dict:
        if len(token) > 8192:
            raise jwt.InvalidTokenError("Token exceeds size limit")
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256":
            raise jwt.InvalidTokenError("Unexpected signing algorithm")
        token_type = header.get("typ")
        if not isinstance(token_type, str) or token_type.lower() not in {"at+jwt", "application/at+jwt"}:
            raise jwt.InvalidTokenError("Unexpected token type")
        if {"jku", "jwk", "x5u", "x5c", "crit"} & header.keys():
            raise jwt.InvalidTokenError("Unsupported JOSE header")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid or len(kid) > 128:
            raise jwt.InvalidTokenError("Invalid signing key ID")
        key = self.keys.get(kid)
        if key is None:
            raise jwt.InvalidTokenError("Unknown signing key")
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            issuer=self.issuer,
            audience=self.audience,
            options={
                "require": ["iss", "sub", "aud", "client_id", "iat", "exp", "jti", "scope"],
                "strict_aud": True,
            },
        )
        if any(type(claims[name]) is not int for name in ("iat", "exp")):
            raise jwt.InvalidTokenError("Invalid token timestamps")
        if any(not isinstance(claims[name], str) or not claims[name] for name in ("sub", "client_id", "jti", "scope")):
            raise jwt.InvalidTokenError("Invalid token claims")
        return claims


def create_task_api(validator: AccessTokenValidator) -> FastAPI:
    app = FastAPI(title="Sample Agent Task API")

    @app.post("/tasks")
    def issue_task(request: Request):
        challenge = 'Bearer realm="tasks"'
        authorization = request.headers.get("Authorization")
        if not authorization:
            return JSONResponse(
                {"error": "unauthorized"}, status_code=401,
                headers={"WWW-Authenticate": challenge},
            )
        scheme, _, token = authorization.partition(" ")
        try:
            if scheme.lower() != "bearer" or not token.strip():
                raise jwt.InvalidTokenError("Expected Bearer token")
            claims = validator.validate(token.strip())
        except KeyUnavailable:
            return JSONResponse({"error": "temporarily_unavailable"}, status_code=503)
        except (jwt.PyJWTError, ValueError, TypeError, OverflowError):
            return JSONResponse(
                {"error": "invalid_token"}, status_code=401,
                headers={"WWW-Authenticate": f'{challenge}, error="invalid_token"'},
            )
        if "task:issue" not in claims["scope"].split(" "):
            return JSONResponse(
                {"error": "insufficient_scope"}, status_code=403,
                headers={"WWW-Authenticate": f'{challenge}, error="insufficient_scope", scope="task:issue"'},
            )
        return {"status": "accepted", "actor": claims["sub"]}

    return app
