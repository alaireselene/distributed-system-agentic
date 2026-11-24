# Spec bàn giao base Authentication

Đọc [kiến trúc](architecture.md), chạy [setup](agent-setup.md), rồi dùng phần việc dưới đây làm phạm vi cho contributor hoặc AI agent. Khi cần đối chiếu hành vi của team khác, dùng [audit theo commit](integration-audit.md).

## Quy ước trước khi sửa

- Chạy `python -m unittest discover -s tests -v` và `python -m agent_auth.demo` làm mốc. Dùng `agent_auth.local` để chạy riêng từng dịch vụ khi làm việc. Giữ ổn định HTTP contract trong [kiến trúc](architecture.md) cho đến khi Trường Sơn review thay đổi.
- Dùng repo này và dịch vụ mẫu cho ca local. Các tên scope trong prototype chỉ áp dụng cho Task API. Audience và scope của Registry/Broker sẽ đi vào spec sau khi các nhóm đồng ý.
- Với JWT sai hoặc thiếu, kiểm tra lỗi xác thực. Với JWT hợp lệ nhưng sai scope hoặc sai owner, kiểm tra lỗi phân quyền. Định nghĩa chính sách ẩn tài nguyên bằng `404` trong hợp đồng từng service nếu nhóm sở hữu chọn hành vi đó.

## Trường Sơn · Architect + Integrate

**Branch mẫu** `codex/integrate/cross-team-demo`.

**Đầu ra.** Giữ kiến trúc, bảng quyết định và hợp đồng liên nhóm trong `docs/`. Trình bày demo độc lập, ghi nhận lựa chọn của Instructor và xác nhận từng adapter với team sở hữu. Chốt danh mục resource/audience, mapping `sub` → `agent_id`, ma trận endpoint/action/resource, cách xử lý Registry credential, cách Broker xác nhận sender và trường trace chung. Điều phối một luồng staging với hai Agent thật. Chủ trì review PR, merge và nghiệm thu IRIS.

- [ ] Mỗi quyết định có trạng thái, người xác nhận và ảnh hưởng tới SDK.
- [ ] Hai agent thật chạy đúng luồng đã chốt. Kịch bản chứng minh thành công và từ chối có trace đối chiếu từ các thành phần.
- [ ] Trước IRIS, chốt issuer HTTPS ổn định, nơi lưu key/credential, cấu hình triển khai, health, cách rollback và smoke sau deploy.

## Nguyễn Hồng Hải · SDK

**Branch mẫu** `codex/sdk/token-client-and-verifier`.

**Đầu ra.** Tách client lấy token và verifier dùng chung vào SDK Python. Dùng `AccessTokenValidator` và `JwksCache` trong `agent_auth/resource.py` làm điểm xuất phát. Giữ HTTP/JSON làm hợp đồng tích hợp cho Go và các runtime khác. Sở hữu logic xác thực JWT, chuyển lỗi thành kiểu có thể dùng ở middleware và tài liệu API của SDK. Việt Hưng phụ trách adapter framework, ví dụ và kiểm chứng tương thích.

- [ ] Client lấy token theo issuer đã tin cậy, kiểm tra metadata issuer, gửi HTTP Basic qua URL đúng, cache theo resource và scope, làm mới trước hạn.
- [ ] Verifier kiểm tra token type, thuật toán, issuer, audience và thời hạn. JWT hoặc lỗi đầu vào không làm server trả traceback.
- [ ] Verifier nhận public key qua JWKS URL cấu hình. Có hành vi cache, refresh và lỗi được ghi rõ, có ca kiểm thử cho key đã cache và gián đoạn lấy JWKS.
- [ ] Đi kèm ví dụ cho client gọi và resource server. Ví dụ có kiểu lỗi rõ, không log token hay credential.

## Doanh Thái · Identity + Credential Lifecycle

**Branch mẫu** `codex/identity/credential-lifecycle`.

**Đầu ra.** Phát triển từ `agent_auth/identity.py`. Thêm cấu hình và lớp lưu client identity, credential và quyền theo resource qua restart. Xây luồng cấp/rotate/disable credential cho demo staging, tách thao tác admin khỏi đường cấp token. Định nghĩa hợp đồng quản lý khóa ký và bàn giao cho Sơn runbook vận hành. Thống nhất key overlap, TTL và cơ chế revoke với Hải.

- [ ] Một workload dùng client ID và secret riêng. Dữ liệu lưu của client secret dùng digest phù hợp với credential ngẫu nhiên. Private signing key chỉ nằm ở Identity.
- [ ] Cấp token đúng resource/scope theo policy, từ chối credential sai hoặc bị disable và từ chối scope vượt quyền.
- [ ] Chứng minh rotate credential và hành vi token đã cấp trước khi disable. Ghi rõ thời gian còn hiệu lực theo policy đã chốt.
- [ ] Công bố khóa mới trước khi ký bằng khóa mới, duy trì khóa cũ trong thời gian cần thiết. Có ca kiểm chứng restart và chuyển khóa với validator của Hải.

## Việt Hưng · SDK + Quality

**Branch mẫu** `codex/quality/integration-contract-tests`.

**Đầu ra.** Viết adapter FastAPI và ví dụ dùng API SDK của Hải. Sở hữu test liên dịch vụ và bộ ca tương thích cho các runtime khác. Mock hợp đồng nhóm khác ở local trước, chuyển sang môi trường staging sau khi hai bên chốt contract. Duy trì smoke trong GitHub Actions.

- [ ] Chứng minh agent ngoài tiến trình lấy token và gọi API theo hướng dẫn setup.
- [ ] Test matrix có token thiếu, sai, hết hạn, sai audience, scope sai, actor không sở hữu tài nguyên và tình huống JWKS không khả dụng.
- [ ] Staging có ca Broker xác thực đúng sender, receiver, ACK, giữ retry/dedup. Registry kiểm tra đúng chủ card và giữ heartbeat/re-register sau lease hết hạn. Dùng agent và dữ liệu dành riêng cho test.
- [ ] Báo cáo từng ca gồm lệnh chạy, kết quả HTTP, trace ID khi có và môi trường đã kiểm chứng.

## Checklist chung trước khi đưa PR cho Sơn review

- [ ] Tạo branch đúng workstream. Kiểm tra working tree và chọn scope nhỏ đủ review.
- [ ] Các lệnh test và smoke ở trên chạy đạt. Lưu lệnh và kết quả cho ca mới. Ghi rõ phần đang chờ nhóm khác.
- [ ] Với thay đổi contract, cập nhật kiến trúc, setup và test liên quan cùng PR.
- [ ] Kiểm tra diff và log. Credential, token và key không đi vào PR.
- [ ] Mở PR đến `main`, điền template, chọn Trường Sơn làm reviewer và chờ Sơn merge.

```bash
git status --short --branch
git switch main
git pull --ff-only origin main
git switch -c codex/sdk/token-client-and-verifier
# Sau khi đã commit và được giao xuất bản PR
git push -u origin HEAD
gh pr create --base main --fill
```

Dùng branch mẫu phù hợp với phần việc. Sau khi mở PR bằng CLI, điền [template](../.github/pull_request_template.md) và chọn Trường Sơn trong giao diện GitHub. [Workflow](../.github/workflows/contribution.yml) kiểm tra tên branch khi push, nhắc mở hoặc cập nhật PR trong Actions và chạy test cùng smoke trên Python 3.11 và 3.12 cho PR vào `main`. Sau khi base vào `main`, Sơn có thể bật yêu cầu review và ba check `Branch convention`, `Authentication checks (Python 3.11)`, `Authentication checks (Python 3.12)` trong ruleset. [GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
