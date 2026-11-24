import base64
import binascii
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote_plus
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from jwt.algorithms import RSAAlgorithm


@dataclass(frozen=True)
class Client:
    secret_digest: bytes
    scopes_by_resource: dict[str, frozenset[str]]


def digest_secret(secret: str) -> bytes:
    return hashlib.sha256(secret.encode()).digest()


def basic_credentials(header: str) -> tuple[str, str]:
    scheme, _, encoded = header.partition(" ")
    if scheme.lower() != "basic" or not encoded:
        raise ValueError("Expected HTTP Basic credentials")
    decoded = base64.b64decode(encoded, validate=True).decode()
    client_id, separator, secret = decoded.partition(":")
    if not separator or not client_id or not secret:
        raise ValueError("Expected client ID and secret")
    return unquote_plus(client_id), unquote_plus(secret)


def token_response(body: dict, status: int = 200) -> JSONResponse:
    headers = {"Cache-Control": "no-store", "Pragma": "no-cache"}
    if status == 401:
        headers["WWW-Authenticate"] = 'Basic realm="identity"'
    return JSONResponse(body, status_code=status, headers=headers)


def create_identity(
    issuer: str,
    private_key: rsa.RSAPrivateKey,
    key_id: str,
    clients: dict[str, Client],
    token_lifetime: int = 300,
) -> FastAPI:
    app = FastAPI(title="Agent Identity")
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": key_id, "use": "sig", "alg": "RS256"})
    resources = {resource for client in clients.values() for resource in client.scopes_by_resource}

    @app.get("/.well-known/oauth-authorization-server")
    def metadata():
        return {
            "issuer": issuer,
            "token_endpoint": f"{issuer}/oauth/token",
            "jwks_uri": f"{issuer}/.well-known/jwks.json",
            "grant_types_supported": ["client_credentials"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic"],
            "response_types_supported": [],
        }

    @app.get("/.well-known/jwks.json")
    def jwks():
        return {"keys": [public_jwk]}

    @app.post("/oauth/token")
    async def issue_token(request: Request):
        try:
            client_id, secret = basic_credentials(request.headers.get("Authorization", ""))
        except (ValueError, binascii.Error):
            return token_response({"error": "invalid_client"}, 401)
        client = clients.get(client_id)
        expected_digest = client.secret_digest if client else digest_secret("")
        if not hmac.compare_digest(digest_secret(secret), expected_digest) or client is None:
            return token_response({"error": "invalid_client"}, 401)

        content_type = request.headers.get("Content-Type", "").partition(";")[0].strip().lower()
        if content_type != "application/x-www-form-urlencoded":
            return token_response({"error": "invalid_request"}, 400)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 4096:
                return token_response({"error": "invalid_request"}, 400)
            body.extend(chunk)
        try:
            fields = parse_qs(body.decode(), keep_blank_values=True, max_num_fields=8)
        except ValueError:
            return token_response({"error": "invalid_request"}, 400)
        if set(fields) - {"grant_type", "resource", "scope"} or any(
            len(values) != 1 or not values[0] for values in fields.values()
        ):
            return token_response({"error": "invalid_request"}, 400)
        if "grant_type" not in fields:
            return token_response({"error": "invalid_request"}, 400)
        if fields["grant_type"] != ["client_credentials"]:
            return token_response({"error": "unsupported_grant_type"}, 400)

        resource = fields.get("resource", [""])[0]
        if resource not in resources:
            return token_response({"error": "invalid_target"}, 400)
        allowed_scopes = client.scopes_by_resource.get(resource, frozenset())
        scope = fields.get("scope", [""])[0]
        requested_scopes = set(scope.split(" "))
        if "" in requested_scopes or not requested_scopes <= allowed_scopes:
            return token_response({"error": "invalid_scope"}, 400)

        now = int(time.time())
        granted_scope = " ".join(sorted(requested_scopes))
        token = jwt.encode(
            {
                "iss": issuer,
                "sub": client_id,
                "aud": resource,
                "client_id": client_id,
                "scope": granted_scope,
                "iat": now,
                "exp": now + token_lifetime,
                "jti": uuid4().hex,
            },
            private_key,
            algorithm="RS256",
            headers={"typ": "at+jwt", "kid": key_id},
        )
        return token_response({
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": token_lifetime,
            "scope": granted_scope,
        })

    return app
