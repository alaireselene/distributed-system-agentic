# Chạy Identity và thử từ agent của bạn

## 1. Cài thư viện và chạy kiểm tra

Dùng Python 3.11 trở lên. Chạy các lệnh ở thư mục gốc của repo bằng Bash. Trên Windows, có thể dùng Git Bash hoặc WSL.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m agent_auth.demo
```

Lệnh cuối chạy 12 bước qua HTTP rồi tự dừng. Nếu cả hai lệnh kiểm thử kết thúc với mã 0, bạn đã có kết quả làm mốc trước khi sửa.

## 2. Để hai dịch vụ chạy trong lúc làm việc

Mở terminal 1 để chạy Identity. Nếu đây là lần đầu, tạo hai secret demo trong `.env.local`. Git bỏ qua tệp này. Nếu đã có tệp, chạy từ dòng `set -a` để dùng lại secret.

```bash
source .venv/bin/activate
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

Mở terminal 2 để chạy Task API. Task API dùng issuer, audience và địa chỉ JWKS đã cấu hình.

```bash
source .venv/bin/activate
python -m agent_auth.local tasks
```

Mặc định Identity dùng cổng 8001 và Task API dùng cổng 8002 trên loopback. Nếu cổng đang bận, truyền cùng một cặp `--identity-port` và `--task-port` cho cả hai lệnh rồi sửa URL ở ví dụ bên dưới. Nếu chỉ cần thử nhanh, có thể dùng `python -m agent_auth.demo --serve` để mở cả hai dịch vụ.

| Client cần biết gì? | Giá trị mặc định |
|---|---|
| Issuer | `http://127.0.0.1:8001` |
| Token endpoint | `http://127.0.0.1:8001/oauth/token` |
| JWKS | `http://127.0.0.1:8001/.well-known/jwks.json` |
| Task API | `http://127.0.0.1:8002/tasks` |
| Resource và audience của Task API | `http://127.0.0.1:8002` |
| Student | Client ID `student`, scope `task:read` |
| Instructor | Client ID `instructor`, scope `task:issue` |

Token ở chế độ này có hạn 300 giây. Identity tạo khóa ký mới mỗi lần khởi động, còn Task API giữ tập khóa đã tải trong 60 giây. Nếu vừa khởi động lại Identity và token mới bị từ chối, đợi Task API tải lại JWKS hoặc khởi động lại Task API để xóa cache. Dùng Ctrl+C để dừng từng dịch vụ.

## 3. Gọi thử từ tiến trình khác

Mở terminal 3. Đoạn mã dưới đây lấy token cho Instructor và Student rồi gọi cùng một API. Kết quả chỉ in mã HTTP và nội dung API trả về.

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

Instructor nhận `200` với actor `instructor`. Student nhận `403 insufficient_scope` dù nội dung yêu cầu cũng ghi `from: instructor`.

## 4. Đưa cách gọi này vào agent của nhóm

**Nếu agent gọi dịch vụ khác**, lấy issuer, client ID, secret, resource và scope từ người quản lý môi trường. Agent có thể dùng bất kỳ thư viện HTTP nào để gửi cùng các trường trong ví dụ. Giữ token theo resource và scope. Khi đổi dịch vụ đích, xin token cho resource mới.

**Nếu agent cung cấp API**, cấu hình issuer, JWKS URL và audience của API. Dùng `AccessTokenValidator` để kiểm tra JWT, rồi kiểm tra scope cho thao tác và quyền trên đối tượng trước khi xử lý. Thử cả yêu cầu được phép và yêu cầu thiếu quyền. [API mẫu](../agent_auth/resource.py) · [Checklist bàn giao](handoff.md)

| Nếu thấy | Kiểm tra |
|---|---|
| Identity trả `401 invalid_client` | Client ID và secret |
| Identity trả `400 invalid_target` | Giá trị `resource` |
| Identity trả `400 invalid_scope` | Các quyền đã cấp cho client ở resource đó |
| Task API trả `401` | Token có mặt, còn hạn và có đúng issuer, audience hay không |
| Task API trả `403` | Token hợp lệ có đủ quyền thao tác hay không |
| Task API trả `503` | Đường từ Task API đến JWKS và tập khóa có dùng được hay không |

Khi dùng môi trường chung, cấu hình HTTPS và dùng secret riêng của môi trường đó.
