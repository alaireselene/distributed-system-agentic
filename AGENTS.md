# Hướng dẫn cho AI agent đóng góp vào repo

Đọc [kiến trúc](docs/architecture.md), [setup](docs/agent-setup.md) và phần việc được giao trong [spec bàn giao](docs/handoff.md) trước khi sửa code. Dùng [đối chiếu tích hợp](docs/integration-audit.md) khi làm việc với Registry hoặc Broker.

1. Chạy `git status --short --branch`. Giữ các thay đổi sẵn có. Nếu đang ở `main` sạch, cập nhật từ `origin/main` bằng fast-forward rồi tạo branch cho đúng workstream. Nếu working tree có thay đổi của người khác hoặc base chưa được merge, chủ động xác định đúng base với Trường Sơn trước khi commit.
2. Dùng branch `codex/<workstream>/<slug>`. Workstream hợp lệ là `integrate`, `sdk`, `identity` hoặc `quality`. Chỉ sửa phần được giao và giữ hợp đồng HTTP hiện tại khi chưa có quyết định cập nhật trong spec.
3. Cài dependencies từ `requirements.txt`, chạy `python -m unittest discover -s tests -v`, `python -m agent_auth.demo` và các ca nghiệm thu riêng của phần việc. Dùng loopback hoặc môi trường test được cấp cho các thao tác tạo, sửa hoặc gửi dữ liệu tích hợp.
4. Mở PR vào `main` theo template khi được giao xuất bản thay đổi. Ghi cách tái hiện, kết quả kiểm chứng, thay đổi hợp đồng và điểm cần Trường Sơn review. Trường Sơn quyết định merge. Nếu chỉ được giao triển khai cục bộ, báo tên branch và tình trạng PR lúc bàn giao.

Credential thật, private key, Bearer token và nội dung header `Authorization` phải nằm ngoài repo, log, ảnh chụp và PR. Nếu ca kiểm chứng dùng credential mẫu thì tạo mới ngay trong test.
