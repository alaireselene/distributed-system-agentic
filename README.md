# Xác thực và phân quyền cho hệ thống multi-agent

Khi một agent gửi `from: instructor`, API cần biết agent đó là ai và có quyền giao việc hay không. Trong bản mẫu, Identity xác thực agent và cấp token. Task API kiểm tra token rồi mới xét quyền `task:issue`. Danh tính trả về lấy từ `sub` đã xác minh.

## Chạy thử trên máy

Dùng Python 3.11 trở lên. Chạy các lệnh sau ở thư mục gốc của repo bằng Bash.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m agent_auth.demo
```

Lệnh demo mở hai cổng HTTP trên loopback, chạy 12 bước rồi tự dừng. Mỗi lần chạy, demo tạo secret và khóa ký mới. Token có hạn 4 giây để xem được ca hết hạn ngay trong buổi trình bày.

| Tình huống | Kết quả mong đợi |
|---|---|
| Agent dùng sai client secret | Identity trả `401 invalid_client` |
| Student xin quyền `task:issue` | Identity trả `400 invalid_scope` |
| Agent gọi Task API với token thiếu, sai định dạng, sai audience hoặc hết hạn | Task API trả `401` |
| Student có token hợp lệ nhưng thiếu `task:issue`, dù gửi `from: instructor` | Task API trả `403 insufficient_scope` |
| Instructor có token dành cho Task API và có `task:issue` | Task API trả `200` và lấy danh tính từ token |

Khi cần chạy hai dịch vụ ở hai tiến trình riêng, dùng `python -m agent_auth.local identity` và `python -m agent_auth.local tasks`. Xem cách tạo secret và gọi thử từ tiến trình thứ ba trong [hướng dẫn chạy trên máy](docs/agent-setup.md).

## Đọc tiếp theo phần việc

| Nếu cần | Đọc |
|---|---|
| Hiểu agent xin token thế nào, API trả lỗi gì và điều gì xảy ra khi Identity ngừng chạy | [Kiến trúc và hợp đồng HTTP](docs/architecture.md) |
| Tìm nơi bắt đầu trong code, xem phần việc của từng người và checklist mở PR | [Bàn giao cho nhóm](docs/handoff.md) |
| Biết Registry và Broker đang xử lý những gì ở bản mã đã đọc | [Đối chiếu mã nguồn hai nhóm](docs/integration-audit.md) |
| Giao một phần việc trong repo cho AI agent | [Hướng dẫn đóng góp](AGENTS.md) |

Ca nghiệm thu đề xuất là gửi công việc qua Broker. Nhóm cần xác nhận cách giao tin với Broker, cách gắn danh tính với Agent Card với Registry và cách nối `trace_id` / `message_id` với Observability. Trước khi thử chung, thống nhất issuer HTTPS, cách giao secret và nơi giữ khóa ký. [Chi tiết tích hợp](docs/architecture.md)
