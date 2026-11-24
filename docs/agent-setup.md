# Setup cho thành viên và agent tích hợp

## Chuẩn bị

Từ thư mục gốc repo, dùng Python 3.11 trở lên. Các lệnh dưới đây dùng Bash, bao gồm Git Bash hoặc WSL trên Windows.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m agent_auth.demo
```

Lệnh cuối thực hiện 12 bước qua hai listener HTTP cục bộ. Exit code 0 nghĩa là tất cả bước đều đạt. Dùng chế độ này cho CI và kiểm tra trước khi sửa.

## Chạy Identity và Task API để gắn agent riêng

Ở terminal 1, tạo hai secret demo một lần trong `.env.local`. Git bỏ qua file này. Nếu file đã có credential đang dùng, giữ lại và chạy từ lệnh `set -a`.

```bash
(
  umask 077
  set -C
  python - <<'PY' > .env.local
import secrets

for agent in ("STUDENT", "INSTRUCTOR"):
    print(f"AGENT_AUTH_{agent}_SECRET={secrets.token_urlsafe(32)}")
PY
)
set -a
source .env.local
set +a
python -m agent_auth.local identity
```

Ở terminal 2, kích hoạt môi trường Python rồi chạy Task API.

```bash
source .venv/bin/activate
python -m agent_auth.local tasks
```

Hai tiến trình chạy trên loopback. Nếu cổng đang bận, truyền cùng cặp `--identity-port` và `--task-port` cho cả hai lệnh rồi sửa URL trong ví dụ client. Có thể dùng `python -m agent_auth.demo --serve` để chạy cả hai dịch vụ bằng một lệnh.

| Cấu hình | Giá trị local |
|---|---|
| Issuer | `http://127.0.0.1:8001` |
| Token endpoint | `http://127.0.0.1:8001/oauth/token` |
| JWKS | `http://127.0.0.1:8001/.well-known/jwks.json` |
| Task API | `http://127.0.0.1:8002/tasks` |
| Resource và audience của Task API | `http://127.0.0.1:8002` |
| Student | Client ID `student`, scope `task:read` |
| Instructor | Client ID `instructor`, scope `task:issue` |

Chế độ chạy cục bộ dùng token 300 giây. Identity tạo khóa ký mới khi khởi động. Task API giữ cache JWKS 60 giây, nên sau khi khởi động lại Identity, có thể đợi cache hết hạn hoặc khởi động lại Task API để lấy khóa mới. Dùng Ctrl+C để dừng.

Ở terminal 3, thử bằng một client bên ngoài. Đoạn mẫu chỉ in kết quả và actor.

```bash
source .venv/bin/activate
set -a
source .env.local
set +a
python - <<'PY'
import os
import httpx

issuer = "http://127.0.0.1:8001"
resource = "http://127.0.0.1:8002"

with httpx.Client(timeout=4, trust_env=False) as client:
    metadata_response = client.get(f"{issuer}/.well-known/oauth-authorization-server")
    metadata_response.raise_for_status()
    metadata = metadata_response.json()
    if metadata["issuer"] != issuer or metadata["token_endpoint"] != f"{issuer}/oauth/token":
        raise RuntimeError("Unexpected issuer metadata")

    for agent, scope, expected in (
        ("instructor", "task:issue", 200),
        ("student", "task:read", 403),
    ):
        response = client.post(
            metadata["token_endpoint"],
            auth=(agent, os.environ[f"AGENT_AUTH_{agent.upper()}_SECRET"]),
            data={"grant_type": "client_credentials", "resource": resource, "scope": scope},
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        response = client.post(
            f"{resource}/tasks",
            headers={"Authorization": f"Bearer {token}"},
            json={"from": "instructor"},
        )
        assert response.status_code == expected, response.status_code
        print(agent, response.status_code, response.json())
PY
```

Kỳ vọng `instructor 200` với actor `instructor` và `student 403` với `insufficient_scope`.

## Tích hợp agent của nhóm

1. Với agent gọi, lấy bộ cấu hình issuer, client ID, credential, resource và scope từ chủ môi trường. Dùng ví dụ HTTP ở trên cho bất kỳ ngôn ngữ nào có HTTP client. Giữ token theo cặp resource và scope. Với lời gọi sang resource khác, xin token khác.
2. Với agent nhận, định cấu hình issuer, JWKS URL và audience của chính API. Đọc [resource.py](../agent_auth/resource.py) để dùng `AccessTokenValidator` trong handler mẫu. Sau xác thực JWT, kiểm tra scope cho action và quyền trên đối tượng trước khi xử lý nghiệp vụ.
3. Kiểm tra `401` cho token thiếu, sai hoặc hết hạn, và `403` cho token đúng nhưng thiếu quyền. Khi dịch vụ đích đã tích hợp, kiểm tra cả happy path lẫn request quyền sai theo [checklist bàn giao](handoff.md).

`401 invalid_client` ở token endpoint yêu cầu kiểm tra client ID và credential. `400 invalid_target` yêu cầu kiểm tra resource. `400 invalid_scope` yêu cầu kiểm tra policy của client. `503` ở Task API yêu cầu kiểm tra đường tới JWKS. Khi ra ngoài loopback, cấu hình HTTPS và dùng bộ credential riêng của môi trường đó.
