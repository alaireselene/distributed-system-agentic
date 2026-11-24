# Bàn giao cho nhóm Authentication

Mỗi người có một phần việc có thể bắt đầu từ base đang chạy. Trước khi sửa, đọc [kiến trúc](architecture.md), làm theo [hướng dẫn chạy](agent-setup.md), rồi chạy `python -m unittest discover -s tests -v` và `python -m agent_auth.demo` để có kết quả làm mốc. Có thể dùng `agent_auth.local` để chạy riêng từng dịch vụ.

Scope trong bản mẫu dùng cho Task API. Khi nối Registry hoặc Broker, chốt audience và scope với nhóm sở hữu API rồi ghi vào hợp đồng. Khi thử lỗi, phân biệt token thiếu hoặc sai với token hợp lệ nhưng thiếu quyền hoặc sai chủ tài nguyên. Nếu dịch vụ muốn dùng `404` để ẩn sự tồn tại của tài nguyên, ghi rõ tình huống đó trong hợp đồng. [Đối chiếu mã nguồn Registry và Broker](integration-audit.md)

## Trường Sơn phụ trách kiến trúc và tích hợp

Nhánh mẫu `codex/integrate/cross-team-demo`.

Dùng demo độc lập để thống nhất với giảng viên ca nghiệm thu qua Broker và phạm vi ngoài ca demo. Làm việc với các nhóm để chốt danh mục resource và audience, quyền cho từng endpoint, cách gắn `sub` với `agent_id`, cách tiếp tục dùng các Agent Card hiện có và cách Broker xác nhận người gửi. Ghi quyết định và hợp đồng trong `docs/`. Sơn review PR, quyết định merge và điều phối thử nghiệm trên staging trước khi đưa lên IRIS.

- [ ] Mỗi quyết định ghi ai xác nhận, đã chốt đến đâu và ảnh hưởng gì đến SDK.
- [ ] Hai agent thật chạy luồng đã chốt. Có một yêu cầu được phép, một yêu cầu bị từ chối và trace để đối chiếu qua các dịch vụ.
- [ ] Trước khi lên IRIS, chốt issuer HTTPS, nơi giữ khóa và credential, cách kiểm tra dịch vụ, cách quay lại bản trước và lệnh chạy thử sau khi triển khai.

## Nguyễn Hồng Hải phụ trách SDK

Nhánh mẫu `codex/sdk/token-client-and-verifier`.

Tách phần xin token và xác minh JWT thành SDK Python. Bắt đầu từ `AccessTokenValidator` và `JwksCache` trong [resource.py](../agent_auth/resource.py). Hải phụ trách phần xác minh và kiểu lỗi để middleware có thể dùng. Hưng phụ trách gắn SDK vào FastAPI, viết ví dụ và kiểm tra tương thích. Các nhóm dùng Go hoặc ngôn ngữ khác vẫn làm theo hợp đồng HTTP/JSON.

- [ ] SDK dùng issuer đáng tin cậy, kiểm tra issuer trong metadata rồi gửi HTTP Basic tới đúng địa chỉ cấp token. Giữ token theo resource và scope, xin token mới trước khi hết hạn.
- [ ] Trình xác minh kiểm tra loại token, thuật toán, issuer, audience và thời hạn. Đầu vào sai cho ra lỗi đã định nghĩa.
- [ ] Dùng JWKS URL đã cấu hình. Ghi rõ khi nào dùng cache, khi nào tải lại và trả lỗi gì nếu không lấy được khóa. Có test cho từng tình huống.
- [ ] Có ví dụ cho agent gọi và API nhận. Log chỉ ghi thông tin cần thiết để hiểu lỗi. Giữ token và secret ngoài log.

## Doanh Thái phụ trách Identity và vòng đời credential

Nhánh mẫu `codex/identity/credential-lifecycle`.

Bắt đầu từ [identity.py](../agent_auth/identity.py). Bổ sung nơi lưu danh tính, credential và quyền theo resource qua lần khởi động lại. Xây cách cấp, thay và vô hiệu hóa credential cho staging. Tách thao tác quản trị khỏi endpoint cấp token. Thống nhất với Hải thời hạn token, thời gian giữ đồng thời khóa cũ và mới, và hành vi thu hồi. Ghi cách quản lý khóa và bàn giao hướng dẫn vận hành cho Sơn.

- [ ] Mỗi agent có client ID và secret riêng. Phần lưu trữ giữ giá trị băm của secret sinh ngẫu nhiên. Khóa ký riêng chỉ ở Identity.
- [ ] Identity cấp token đúng resource và scope đã cho phép. Credential sai hoặc đã bị vô hiệu hóa không lấy được token mới.
- [ ] Có ca thay credential và kiểm tra token đã cấp trước khi vô hiệu hóa client. Ghi rõ token đó còn dùng được bao lâu theo phương án đã chốt.
- [ ] Công bố khóa công khai mới trước khi ký bằng khóa mới. Giữ khóa cũ đủ thời gian để xác minh token còn hạn. Thử cả lần khởi động lại và thay khóa với SDK của Hải.

## Việt Hưng phụ trách tích hợp SDK và kiểm thử

Nhánh mẫu `codex/quality/integration-contract-tests`.

Viết adapter FastAPI và ví dụ dùng SDK của Hải. Phụ trách bộ ca liên dịch vụ, ca tương thích với runtime khác và smoke trên GitHub Actions. Dùng dịch vụ giả lập ở local trong lúc chờ hợp đồng liên nhóm. Sau khi thống nhất, chạy với agent và dữ liệu dành riêng trên staging.

- [ ] Agent ở tiến trình riêng lấy token và gọi được API theo hướng dẫn.
- [ ] Có ca thiếu token, token sai, hết hạn, sai audience, thiếu scope, sai chủ tài nguyên và JWKS không khả dụng.
- [ ] Ca Broker kiểm tra đúng người gửi, người nhận và quyền ACK, đồng thời giữ hành vi giao lại và lọc tin trùng. Ca Registry kiểm tra đúng chủ Agent Card và giữ hành vi heartbeat, đăng ký lại khi lease hết hạn.
- [ ] Mỗi ca có lệnh chạy, kết quả HTTP, môi trường và trace ID nếu có.

## Trước khi mở PR

- [ ] Nhánh đúng mẫu `codex/<workstream>/<slug>` và chứa phần thay đổi được giao.
- [ ] Hai lệnh kiểm thử ở đầu tài liệu và các ca của phần việc đều đạt. PR ghi kết quả và việc còn chờ nhóm khác.
- [ ] Nếu thay đổi hợp đồng hoặc cách chạy, PR cập nhật cả tài liệu và test liên quan.
- [ ] Diff, log và ảnh đã loại secret, token và khóa riêng.
- [ ] PR mở vào `main`, điền mẫu và gửi Trường Sơn review. Sơn quyết định merge.

Ví dụ cho phần SDK. Chạy từ working tree sạch và đổi tên nhánh cho phù hợp với phần việc.

```bash
git status --short --branch
git switch main
git pull --ff-only origin main
git switch -c codex/sdk/token-client-and-verifier
# Sau khi đã commit và được giao đưa thay đổi lên GitHub
git push -u origin HEAD
gh pr create --base main --fill
```

Sau khi mở PR, điền lệnh, kết quả và điểm cần review theo mẫu trên GitHub. Workflow kiểm tra tên nhánh khi push, nhắc mở PR và chạy test trên Python 3.11, 3.12 khi mở PR vào `main`. Sau khi base vào `main`, Sơn có thể bật yêu cầu review và ba check `Branch convention`, `Authentication checks (Python 3.11)`, `Authentication checks (Python 3.12)`. [Mẫu PR](../.github/pull_request_template.md) · [Workflow](../.github/workflows/contribution.yml) · [GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
