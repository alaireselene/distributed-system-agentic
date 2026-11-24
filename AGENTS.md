# Làm việc trong repo Authentication

Trước khi sửa code, đọc phần việc được giao trong [tài liệu bàn giao](docs/handoff.md). Đọc [kiến trúc](docs/architecture.md) để nắm hợp đồng HTTP và [hướng dẫn chạy](docs/agent-setup.md) để có kết quả làm mốc. Khi sửa phần liên quan đến Registry hoặc Broker, xem [đối chiếu theo commit](docs/integration-audit.md).

1. Chạy `git status --short --branch`. Nếu đang ở `main` sạch, cập nhật từ `origin/main` bằng fast-forward rồi tạo nhánh làm việc. Nếu có thay đổi của người khác hoặc chưa rõ nhánh nào chứa base, xác định điểm bắt đầu với Trường Sơn trước khi commit.
2. Đặt tên nhánh theo mẫu `codex/<workstream>/<slug>`. Chọn `integrate`, `sdk`, `identity` hoặc `quality` theo phần việc được giao. Khi cần đổi hợp đồng HTTP, đưa thay đổi và các bên bị ảnh hưởng vào nội dung review.
3. Cài thư viện từ `requirements.txt`. Chạy `python -m unittest discover -s tests -v`, `python -m agent_auth.demo` và các ca nghiệm thu của phần mình làm. Dùng loopback hoặc môi trường test được cấp khi gửi tin, tạo bản ghi hoặc cập nhật dữ liệu.
4. Khi được giao đưa thay đổi lên GitHub, mở PR vào `main` theo [mẫu PR](.github/pull_request_template.md). Ghi lệnh chạy, kết quả và điểm cần Trường Sơn xem. Trường Sơn quyết định merge. Nếu phần việc chỉ chạy cục bộ, ghi rõ tên nhánh và tình trạng PR khi bàn giao.

Dùng secret sinh riêng cho test. Giữ secret thật, khóa riêng, Bearer token và nội dung header `Authorization` ngoài repo, log, ảnh chụp và PR.
