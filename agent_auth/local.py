"""Loopback-only service entry points for local development."""

import argparse
import os
import secrets

import uvicorn
from cryptography.hazmat.primitives.asymmetric import rsa

from agent_auth.identity import Client, create_identity, digest_secret
from agent_auth.resource import AccessTokenValidator, JwksCache, create_task_api


LOOPBACK = "127.0.0.1"
IDENTITY_PORT = 8001
TASK_PORT = 8002


def local_credentials() -> dict[str, str]:
    credentials = {
        agent: os.environ.get(f"AGENT_AUTH_{agent.upper()}_SECRET", "")
        for agent in ("student", "instructor")
    }
    if not all(credentials.values()) or len(set(credentials.values())) != len(credentials):
        raise ValueError("Set distinct AGENT_AUTH_STUDENT_SECRET and AGENT_AUTH_INSTRUCTOR_SECRET")
    return credentials


def local_identity(issuer: str, resource: str, credentials: dict[str, str], token_lifetime: int = 300):
    clients = {
        "student": Client(digest_secret(credentials["student"]), {resource: frozenset({"task:read"})}),
        "instructor": Client(
            digest_secret(credentials["instructor"]),
            {resource: frozenset({"task:issue"}), f"{resource}/other-service": frozenset({"task:issue"})},
        ),
    }
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return create_identity(issuer, key, secrets.token_urlsafe(12), clients, token_lifetime)


def local_task_api(issuer: str, resource: str):
    validator = AccessTokenValidator(issuer, resource, JwksCache(f"{issuer}/.well-known/jwks.json"))
    return create_task_api(validator)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=("identity", "tasks"))
    parser.add_argument("--identity-port", type=int, default=IDENTITY_PORT)
    parser.add_argument("--task-port", type=int, default=TASK_PORT)
    args = parser.parse_args()
    if not all(1 <= port <= 65535 for port in (args.identity_port, args.task_port)):
        parser.error("Ports must be between 1 and 65535")
    if args.identity_port == args.task_port:
        parser.error("Identity and Task API must use different ports")

    issuer = f"http://{LOOPBACK}:{args.identity_port}"
    resource = f"http://{LOOPBACK}:{args.task_port}"
    if args.service == "identity":
        try:
            credentials = local_credentials()
        except ValueError as error:
            parser.error(str(error))
        app = local_identity(issuer, resource, credentials)
        port = args.identity_port
    else:
        app = local_task_api(issuer, resource)
        port = args.task_port
    uvicorn.run(app, host=LOOPBACK, port=port, access_log=False)


if __name__ == "__main__":
    main()
