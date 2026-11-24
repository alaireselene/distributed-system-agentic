# Registry và Broker đang xử lý thế nào?

Ghi nhận dưới đây dựa trên các commit đã đọc. Dùng chúng để đặt câu hỏi với từng nhóm trước khi sửa hợp đồng tích hợp.

## Registry quản lý quyền sở hữu Agent Card

Đã đọc commit `872010422e134ba35e0f41c29ce87d0edcf27d11`.

| Thao tác | Điều thấy trong mã |
|---|---|
| Đăng ký | Với `POST /v1/agents`, Registry cho tạo card mới khi yêu cầu chưa có credential. Registry sinh credential ngẫu nhiên, chỉ lưu giá trị băm và trả credential một lần. Khi đăng ký lại, agent phải dùng credential của card đó. |
| Đọc | Discovery, lookup, status và health không gọi bước xác thực. |
| Cập nhật và giữ lease | PATCH, heartbeat, unregister và DELETE kiểm tra quyền sở hữu. Nếu lease đã hết hạn hoặc agent đã unregister, heartbeat trả `409`. SDK dùng phản hồi này để đăng ký lại. |

Việc đầu tiên cần chốt là ai cấp `agent_id` và cách gắn `sub` với card mới lẫn card đã có. JWT và credential của Registry đều đi qua header `Authorization`, nên hai nhóm cần thống nhất client sẽ chuyển sang cách xác thực mới thế nào. Đồng thời chốt route đọc nào giữ công khai, khi nào trả lỗi thiếu quyền và cách giữ hành vi heartbeat, đăng ký lại, unregister và xóa card. Nếu cần khóa lookup, phải cấp credential và scope cho Broker hoặc SDK đang dùng nó. [Routes](https://github.com/HPHind110/agent-registry/blob/872010422e134ba35e0f41c29ce87d0edcf27d11/registry/routes.py) · [Xử lý Agent Card](https://github.com/HPHind110/agent-registry/blob/872010422e134ba35e0f41c29ce87d0edcf27d11/registry/service.py) · [SDK](https://github.com/HPHind110/agent-registry/blob/872010422e134ba35e0f41c29ce87d0edcf27d11/agent_registry_client/client.py) · [Hợp đồng API](https://github.com/HPHind110/agent-registry/blob/872010422e134ba35e0f41c29ce87d0edcf27d11/docs/api_contract.md)

## Broker nhận, giao và xác nhận tin

Đã đọc commit `5c3ada750d3f0b630e9874abb8e3bb21ee813e4e`. Ở địa chỉ Broker được cung cấp, `GET /healthz` trả `200` với nội dung `ok`. Lần kiểm tra đó chỉ xác nhận dịch vụ phản hồi. Ca gửi, nhận và ACK cần hai agent riêng trên môi trường test. Đặc biệt, `GET /receive` có thể nhận xử lý tin đang chờ và cập nhật trạng thái poll.

| Thao tác | Điều thấy trong mã | Điểm cần chốt với nhóm Broker |
|---|---|---|
| `POST /send` | Broker kiểm tra envelope, tiếp nhận tin để giao sau và lấy `from` từ envelope. | Kiểm tra quyền gửi trước khi nhận tin. Chọn cách đối chiếu hoặc điền người gửi từ token đã xác minh. Giữ quy tắc lọc tin trùng. |
| `GET /receive` | Broker lấy `agent_id` từ query, ghi nhận agent đang pull và lấy các tin đến hạn cho ID đó. | Kiểm tra danh tính trước khi chọn tin và ghi nhận lượt nhận. Chốt cách đưa danh tính người gửi đã xác minh vào phản hồi. |
| `POST /messages/{message_id}/ack` và `POST /ack` | Hai route dùng chung handler. Handler so `agent_id` trong body với người nhận của tin. | Đối chiếu `agent_id` với danh tính đã xác minh trước khi cho ACK ở cả hai route. |
| Kết nối và health | Go server dùng HTTP. Tài liệu client ghi xác thực token ở phần sẽ bổ sung. | Chốt địa chỉ HTTPS để gửi token thật và cách kiểm tra dịch vụ đã sẵn sàng. Thống nhất phản hồi khi xác thực thất bại. |

Trước khi ghép Identity, hỏi nhóm Broker bản đang chạy giao tin thế nào và có thể kiểm tra JWT ở đâu. Bảng trên dùng luồng pull trong mã đã xem để định vị chỗ cần trao đổi. [HTTP handlers](https://github.com/binhtutotet123-coder/message-broker/blob/5c3ada750d3f0b630e9874abb8e3bb21ee813e4e/api.go) · [Giao tin và poll](https://github.com/binhtutotet123-coder/message-broker/blob/5c3ada750d3f0b630e9874abb8e3bb21ee813e4e/broker/broker.go) · [Server](https://github.com/binhtutotet123-coder/message-broker/blob/5c3ada750d3f0b630e9874abb8e3bb21ee813e4e/main.go) · [Hướng dẫn kết nối](https://github.com/binhtutotet123-coder/message-broker/blob/5c3ada750d3f0b630e9874abb8e3bb21ee813e4e/docs/HUONG-DAN-KET-NOI.md)
