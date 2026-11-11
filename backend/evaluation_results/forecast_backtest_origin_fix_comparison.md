# So sánh backtest trước/sau sửa cộng trùng sự kiện tại origin

Cấu hình: 30 seed (1..30), chuỗi 365 ngày bắt đầu 2026-01-01, lịch sử 60 ngày, horizon 30 ngày, bước nhảy 7 ngày, 40 origin mỗi chuỗi. Cả hai lần chạy dùng cùng cấu hình mặc định; bản trước chỉ đổi thư mục xuất kết quả. Bảng tổng hợp trước sửa đã được đối chiếu trùng hoàn toàn với bản lưu trong repository trước thay đổi.

Số tiền dưới đây là trung bình qua 30 seed, đơn vị đồng, làm tròn đến đồng. A: Mean thô; B: Mean + Winsorization; C: EWMA thô; D: EWMA + Winsorization.

| Kịch bản | Nhánh | MAE_daily trước | MAE_daily sau | MAE_end trước | MAE_end sau |
|---|---|---:|---:|---:|---:|
| Ổn định | A | 908,052 | 84,121 | 952,726 | 131,648 |
| Ổn định | B | 908,060 | 84,133 | 952,700 | 131,632 |
| Ổn định | C | 946,043 | 128,190 | 1,038,278 | 228,095 |
| Ổn định | D | 946,026 | 128,174 | 1,038,232 | 228,049 |
| Xu hướng tăng | A | 1,059,983 | 272,730 | 1,337,416 | 590,172 |
| Xu hướng tăng | B | 1,060,067 | 272,829 | 1,337,585 | 590,366 |
| Xu hướng tăng | C | 947,183 | 132,601 | 1,078,524 | 280,831 |
| Xu hướng tăng | D | 947,197 | 132,632 | 1,078,674 | 281,016 |
| Thất thường/outlier | A | 2,506,323 | 1,800,086 | 4,062,371 | 3,368,992 |
| Thất thường/outlier | B | 1,972,891 | 1,206,384 | 3,115,441 | 2,339,775 |
| Thất thường/outlier | C | 2,440,816 | 2,211,274 | 4,098,526 | 4,331,460 |
| Thất thường/outlier | D | 2,000,534 | 1,431,150 | 3,217,092 | 2,820,205 |

## Origin bị cộng trùng trong lịch mặc định

| Origin | Sự kiện | Sai lệch step 0 trước sửa (đ) | Sai lệch sau sửa (đ) |
|---|---|---:|---:|
| 2026-04-20 | Tiện ích và Internet | -1,200,000 | 0 |
| 2026-07-20 | Tiện ích và Internet | -1,200,000 | 0 |
| 2026-08-10 | Tiền thuê nhà | -6,000,000 | 0 |
| 2026-10-05 | Lương | +25,000,000 | 0 |

Có 4/40 origin mỗi chuỗi bị cộng trùng, tương ứng 1,440/14,400 dòng đánh giá qua 3 kịch bản × 30 seed × 4 nhánh. Các origin khác vẫn đổi MAE_daily/RMSE_daily vì bỏ step 0 khỏi mẫu số; MAE_end không đổi ở các origin này.

Đã đối chiếu toàn bộ 14.400 dòng: signed_err_end sau sửa bằng signed_err_end trước sửa trừ sự kiện origin. Ở origin không có sự kiện, MAE_daily sau bằng MAE_daily trước × 31/30; RMSE_daily sau bằng RMSE_daily trước × sqrt(31/30); abs_err_end giữ nguyên.

Số dư origin là số dư cuối ngày. Chỉ áp dụng sự kiện trong (origin, origin + horizon]; MAE_daily/RMSE_daily dùng step 1..30, còn sai số cuối dùng step 30. simulate_cashflow và chữ ký hàm công khai giữ nguyên.

Hai script backend/scripts/forecast_backtest.py và backend/scripts/plot_forecast_charts.py không chứa bản sao logic đánh giá; không cần sửa. Các CSV V2 và ba biểu đồ đã được sinh lại; các CSV phiên bản cũ không có hậu tố _v2 giữ nguyên.

Giới hạn phạm vi: không sửa ngoại lệ ngày đầu của bộ sinh dữ liệu, bộ đọc CSV thực hoặc các nhận xét thống kê ghi cố định ở mục 6 của bộ sinh báo cáo. Các nhận xét này cần được rà soát riêng trước khi dùng trong luận văn.
