# Authentication cho Multi-Agent

Demo chạy hai dịch vụ HTTP độc lập trên máy cục bộ. Identity Service cấp JWT cho agent qua OAuth 2.0 Client Credentials. Task API lấy khóa công khai từ JWKS, xác minh token và chỉ cho agent có scope `task:issue` tạo task mẫu.

- [Kiến trúc và các quyết định cần review](docs/architecture.md)
- [Setup cho agent kết nối từ tiến trình riêng](docs/agent-setup.md)
- [Spec bàn giao và checklist theo thành viên](docs/handoff.md)
- [Audit mã nguồn Registry và Broker](docs/integration-audit.md)
- [Hướng dẫn làm việc cho AI agent trong repo](AGENTS.md)

## Chạy demo

Yêu cầu Python 3.11 trở lên. Từ thư mục gốc của repo:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m agent_auth.demo
```

Lệnh cuối khởi động hai dịch vụ trên hai cổng loopback ngẫu nhiên, chạy các ca kiểm chứng qua HTTP rồi dừng. Credential và khóa ký sinh riêng mỗi lần chạy. Token demo sống 4 giây để có thể thấy ca hết hạn ngay trong buổi trình bày.

Khi phát triển từng phần, chạy `python -m agent_auth.local identity` và `python -m agent_auth.local tasks` ở hai terminal. Xem [hướng dẫn tạo credential và thử bằng client riêng](docs/agent-setup.md).

| Tình huống | Kết quả |
|---|---|
| Client secret sai | `401 invalid_client` |
| Student xin quyền `task:issue` | `400 invalid_scope` |
| Thiếu token, token sai định dạng, sai audience hoặc hết hạn tại Task API | `401` |
| Student có token hợp lệ nhưng thiếu scope, kể cả khi gửi `from: instructor` | `403 insufficient_scope` |
| Instructor có token đúng audience và scope | `200`, actor lấy từ token đã xác minh |

## Hợp đồng của prototype

| Thành phần | Endpoint | Hành vi |
|---|---|---|
| Identity | `GET /.well-known/oauth-authorization-server` | Công bố issuer, token endpoint, JWKS URI và phương thức xác thực client |
| Identity | `GET /.well-known/jwks.json` | Công bố RSA public key cùng `kid` |
| Identity | `POST /oauth/token` | HTTP Basic, form `grant_type=client_credentials`, một `resource` và một chuỗi `scope` |
| Agent mẫu | `POST /tasks` | Bearer JWT access token ký RS256. Kiểm tra issuer, audience, thời hạn và scope |

Demo cấu hình sẵn issuer, audience và JWKS URL. Task API giữ JWKS trong 60 giây và trả `503` nếu đến hạn làm mới mà không tải được khóa. Python, FastAPI và PyJWT là lựa chọn cho prototype. Hợp đồng HTTP cho phép các nhóm tích hợp bằng ngôn ngữ của họ. Hai dịch vụ sử dụng HTTP loopback khi chạy demo. Môi trường chia sẻ cần HTTPS, cấu hình issuer ổn định và lưu credential, khóa ký ngoài tiến trình demo.

Tham chiếu gồm [OAuth 2.0 Client Credentials](https://www.rfc-editor.org/rfc/rfc6749.html#section-4.4), [Bearer Token](https://www.rfc-editor.org/rfc/rfc6750.html#section-3), [Authorization Server Metadata](https://www.rfc-editor.org/rfc/rfc8414.html), [Resource Indicators](https://www.rfc-editor.org/rfc/rfc8707.html#section-2.2) và [JWT Access Token Profile](https://www.rfc-editor.org/rfc/rfc9068.html#section-4).

## Điểm cần thống nhất sau demo

| Đầu mối | Nội dung cần thống nhất |
|---|---|
| Instructor | Xác nhận ca nghiệm thu qua Broker và phạm vi áp dụng cho các yêu cầu ngoài ca demo. |
| Broker | Xác minh danh tính ở send, receive và ACK. Thống nhất cách gắn sender đã xác minh vào envelope khi giao tin và cách triển khai HTTPS. |
| Registry | Ánh xạ danh tính đã xác minh tới `agent_id` và chủ Agent Card. Chốt các API được bảo vệ và cách chuyển tiếp từ credential Registry hiện tại. |
| Application Agents | Chọn một agent thật để thử SDK và chạy luồng end-to-end, chốt audience và scope ở endpoint tích hợp. |
| Observability | Thống nhất cách liên kết quyết định xác thực với `trace_id` và `message_id`, cùng quy tắc loại token và secret khỏi log. |
