# Đối chiếu tích hợp Registry và Broker

Kết quả kiểm tra mã nguồn được ghim theo commit. Phương án ở cột cuối cần review với nhóm sở hữu trước khi áp dụng.

## Registry

Đã đọc commit `872010422e134ba35e0f41c29ce87d0edcf27d11`.

| Phạm vi | Mã đang làm gì | Điểm cần thống nhất |
|---|---|---|
| Đăng ký mới và đăng ký lại | `POST /v1/agents` tạo bản ghi mới khi request không có credential. Registry sinh credential ngẫu nhiên, chỉ lưu hash và trả credential một lần. Đăng ký lại cần credential đúng của card. | Xác định ai được cấp trước `agent_id`. Chọn cách liên kết card hiện có với `sub` và cách chuyển đổi credential. JWT và credential sở hữu hiện dùng cùng header `Authorization`, nên adapter cần một cơ chế chuyển đổi rõ ràng. |
| Đọc | Discovery, lookup, status và health không gọi dependency xác thực. | Xác nhận route đọc nào là công khai. Nếu khóa lookup, xác định scope và workload credential cho Broker hoặc SDK đang gọi Registry. |
| Ghi và lease | PATCH, heartbeat, unregister và DELETE gọi kiểm tra ownership. Heartbeat của lease hết hạn hoặc đã unregister trả `409`, SDK re-register sau `409`. | Kiểm tra ownership sau khi xác thực JWT và giữ hành vi heartbeat, re-register, withdraw và delete. Xác định tình trạng lỗi khi thiếu quyền hoặc ownership không khớp. |

Nguồn theo commit gồm [routes](https://github.com/HPHind110/agent-registry/blob/872010422e134ba35e0f41c29ce87d0edcf27d11/registry/routes.py), [service](https://github.com/HPHind110/agent-registry/blob/872010422e134ba35e0f41c29ce87d0edcf27d11/registry/service.py), [SDK lifecycle](https://github.com/HPHind110/agent-registry/blob/872010422e134ba35e0f41c29ce87d0edcf27d11/agent_registry_client/client.py) và [API contract](https://github.com/HPHind110/agent-registry/blob/872010422e134ba35e0f41c29ce87d0edcf27d11/docs/api_contract.md).

## Broker

Đã đọc commit `5c3ada750d3f0b630e9874abb8e3bb21ee813e4e`. Endpoint Broker trong tài liệu trả HTTP 200 và body `ok` khi gọi `GET /healthz`. Đây là kiểm tra liveness. Các thao tác send, receive và ACK sẽ kiểm tra trên môi trường test với hai agent được cấp riêng. `GET /receive` có thể claim message và cập nhật trạng thái poll.

| Phạm vi | Mã đang làm gì | Điểm cần thống nhất |
|---|---|---|
| `POST /send` | Decode và kiểm tra envelope rồi nhận tin bất đồng bộ. `from` lấy từ envelope. | Xác minh token scope gửi trước khi chấp nhận. Đối chiếu hoặc điền danh tính gửi từ actor đã xác minh, giữ quy ước dedup theo message. |
| `GET /receive` | Lấy `agent_id` từ query. Broker ghi nhận agent đang pull và claim các tin đến hạn cho ID đó. | Ràng buộc mailbox với actor đã xác minh trước khi claim. Xác định cách giữ danh tính sender đã xác minh trong response pull. |
| `POST /messages/{message_id}/ack` và `POST /ack` | So `agent_id` từ body với người nhận của message. | Ràng buộc `agent_id` với actor trước khi ACK, bảo vệ cả hai route gọi chung handler. |
| TLS và health | Go server dùng HTTP listener. Tài liệu client ghi xác thực token ở mục sẽ bổ sung. | Xác định endpoint HTTPS dùng cho token thật. Giữ health ở mức liveness, thống nhất readiness và lỗi xác thực khi tích hợp. |

Nguồn theo commit gồm [HTTP handlers](https://github.com/binhtutotet123-coder/message-broker/blob/5c3ada750d3f0b630e9874abb8e3bb21ee813e4e/api.go), [delivery và poll](https://github.com/binhtutotet123-coder/message-broker/blob/5c3ada750d3f0b630e9874abb8e3bb21ee813e4e/broker/broker.go), [server](https://github.com/binhtutotet123-coder/message-broker/blob/5c3ada750d3f0b630e9874abb8e3bb21ee813e4e/main.go) và [hướng dẫn kết nối](https://github.com/binhtutotet123-coder/message-broker/blob/5c3ada750d3f0b630e9874abb8e3bb21ee813e4e/docs/HUONG-DAN-KET-NOI.md).
