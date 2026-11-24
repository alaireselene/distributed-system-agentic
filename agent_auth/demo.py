import argparse
import secrets
import socket
import time
from contextlib import contextmanager
from threading import Thread

import httpx
import uvicorn
from agent_auth.local import IDENTITY_PORT, LOOPBACK, TASK_PORT, local_credentials, local_identity, local_task_api


@contextmanager
def local_listener(port: int = 0):
    with socket.socket() as listener:
        listener.bind((LOOPBACK, port))
        yield listener, f"http://{LOOPBACK}:{listener.getsockname()[1]}"


@contextmanager
def serve(app, listener):
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started:
            if not thread.is_alive() or time.monotonic() >= deadline:
                raise RuntimeError("Demo service failed to start")
            time.sleep(0.01)
        yield
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def expect(label: str, response: httpx.Response, expected_status: int, **fields) -> dict:
    body = response.json()
    if response.status_code != expected_status or any(body.get(key) != value for key, value in fields.items()):
        raise RuntimeError(f"{label}: expected HTTP {expected_status}, received {response.status_code}")
    print(f"{expected_status}  {label}", flush=True)
    return body


def run_demo(issuer, resource, other_resource, credentials):
    with httpx.Client(timeout=4, trust_env=False) as http:
        metadata = expect(
            "Tìm metadata từ issuer đã cấu hình",
            http.get(f"{issuer}/.well-known/oauth-authorization-server"),
            200,
            issuer=issuer,
            token_endpoint=f"{issuer}/oauth/token",
        )
        endpoint = metadata["token_endpoint"]

        def issue(agent, audience, scope, secret=None):
            return http.post(
                endpoint,
                auth=(agent, credentials[agent] if secret is None else secret),
                data={"grant_type": "client_credentials", "resource": audience, "scope": scope},
            )

        def call(token=None, **body):
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            return http.post(f"{resource}/tasks", headers=headers, json=body)

        expect("Client secret sai", issue("student", resource, "task:read", "incorrect"), 401,
               error="invalid_client")
        expect("Student xin scope của Instructor", issue("student", resource, "task:issue"), 400,
               error="invalid_scope")
        expect("Gọi API thiếu token", call(), 401, error="unauthorized")
        expect("Gọi API với token sai định dạng", call("invalid"), 401, error="invalid_token")

        student = expect("Student lấy token", issue("student", resource, "task:read"), 200,
                         token_type="Bearer")
        expect("Student tự khai là Instructor trong message", call(student["access_token"], **{"from": "instructor"}),
               403, error="insufficient_scope")

        other = expect("Instructor lấy token dành cho service khác",
                       issue("instructor", other_resource, "task:issue"), 200)
        expect("API từ chối token sai audience", call(other["access_token"]), 401, error="invalid_token")

        instructor = expect("Instructor lấy token cho Task API", issue("instructor", resource, "task:issue"), 200)
        expect("Instructor gọi Task API", call(instructor["access_token"]), 200,
               status="accepted", actor="instructor")
        time.sleep(instructor["expires_in"])
        expect("API từ chối token hết hạn", call(instructor["access_token"]), 401, error="invalid_token")


def main():
    parser = argparse.ArgumentParser(description="Run the standalone agent authentication demo")
    parser.add_argument("--serve", action="store_true", help="Keep the local services running for manual integration")
    args = parser.parse_args()
    if args.serve:
        try:
            credentials = local_credentials()
        except ValueError as error:
            parser.error(str(error))
    else:
        credentials = {agent: secrets.token_urlsafe(32) for agent in ("student", "instructor")}

    with (
        local_listener(IDENTITY_PORT if args.serve else 0) as (issuer_socket, issuer),
        local_listener(TASK_PORT if args.serve else 0) as (task_socket, resource),
    ):
        other_resource = f"{resource}/other-service"
        identity = local_identity(issuer, resource, credentials, token_lifetime=300 if args.serve else 4)
        with serve(identity, issuer_socket), serve(local_task_api(issuer, resource), task_socket):
            if args.serve:
                print(f"Identity: {issuer}\nTask API: {resource}\nStop with Ctrl+C.", flush=True)
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
            else:
                run_demo(issuer, resource, other_resource, credentials)


if __name__ == "__main__":
    main()
