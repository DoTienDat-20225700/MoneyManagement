# Hợp đồng API xác thực bằng cookie

## Đăng ký

`POST /api/register/` nhận JSON `firstName`, `lastName`, `email`, `password`.
Thành công trả `201` với `{"message": "Tạo tài khoản thành công!"}`.
Lỗi kiểm tra dữ liệu trả `400` với `{"success": false, "message": "..."}`.
Frontend chấp nhận mọi phản hồi 2xx và hiển thị thông báo lỗi do server trả về.

## Đăng nhập

`POST /api/token/` nhận JSON `email`, `password`.
Thành công trả `200` với `{"access": "<access JWT>"}` và đặt refresh token
trong cookie HttpOnly. Refresh token không có trong JSON.

## Làm mới phiên

`POST /api/token/refresh/` không cần refresh token trong body; client gửi `{}`
và phải gửi kèm cookie (`withCredentials: true` khi dùng Axios).
Thành công trả `200` với **chỉ** `{"access_token": "<access JWT>"}`.

Server dùng rotation của SimpleJWT: blacklist refresh token cũ, phát hành token
mới và thay cookie HttpOnly. Trường `refresh_token` trong JSON đã bị loại bỏ.
Frontend chỉ lưu access token trong bộ nhớ.

Thiếu cookie, token hỏng/hết hạn hoặc đã blacklist: `403` với `error`.
Người dùng đã bị xóa hoặc vô hiệu hóa: `401` với `error`.
Refresh token trong body không thay thế được cookie.

## Đăng xuất

`POST /api/logout/` gửi kèm cookie, không cần bearer access token.
Server blacklist refresh token hợp lệ và xóa cookie; trả **204, body rỗng**.
Gọi lặp lại, không có cookie, token hỏng/hết hạn/đã blacklist đều vẫn trả 204.

Tên, path, domain và SameSite của cookie đặt/xóa lấy từ cùng cấu hình
`SIMPLE_JWT.AUTH_COOKIE*`. Cookie mới giữ HttpOnly/Secure theo cấu hình.
`ROTATE_REFRESH_TOKENS` và `BLACKLIST_AFTER_ROTATION` đã bật; ứng dụng
`rest_framework_simplejwt.token_blacklist` và các migration đã có sẵn.

Frontend gọi logout trước, sau đó luôn xóa state xác thực và cache React Query,
kể cả khi request thất bại. Không xóa tùy chọn giao diện trong localStorage;
không có token xác thực được lưu trong localStorage/sessionStorage hiện tại.

Nếu logout thất bại do mạng/server, frontend vẫn dọn trạng thái cục bộ, nhưng
không thể tự xóa cookie HttpOnly hoặc bảo đảm thu hồi token ở server. Access JWT
đã phát hành vẫn có hiệu lực đến khi hết hạn (hiện 5 phút); logout thu hồi refresh
token, không đưa access token vào blacklist.
