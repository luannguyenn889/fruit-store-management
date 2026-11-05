# FruitStore Management System — UI/UX Design Rules

> **Mục đích:** Tài liệu quy chuẩn dùng chung cho mọi prompt thiết kế UI, công cụ AI sinh giao diện, frontend Angular và quá trình review UI/UX của dự án FruitStore Management System.
>
> **Công nghệ dự án:** Angular + TypeScript, FastAPI REST API, PostgreSQL, Docker.
>
> **Ngôn ngữ giao diện mặc định:** Tiếng Việt.  
> **Phong cách tổng thể:** Hiện đại, sạch sẽ, thân thiện với thực phẩm tươi, chuyên nghiệp và ưu tiên hiệu quả thao tác.

---

## 1. Vai trò và nguyên tắc nền tảng

Thiết kế UI/UX cho **FruitStore Management System**, một hệ thống quản lý cửa hàng trái cây gồm bán hàng tại quầy (POS), quản trị cửa hàng, kho hàng theo lô/hạn sử dụng, nhập hàng, đơn hàng, thanh toán và cửa hàng trực tuyến.

Mọi thiết kế phải tuân thủ các nguyên tắc:

1. **Business-first:** Giao diện phục vụ nghiệp vụ thật, không chỉ để đẹp.
2. **Consistent:** Mọi trang dùng chung hệ thống màu sắc, typography, spacing, component và cách phản hồi.
3. **Clear hierarchy:** Người dùng nhìn vào là biết tiêu đề, thông tin quan trọng, hành động chính và trạng thái.
4. **Fast to operate:** Giảm số bước, giảm nhập liệu lặp lại, tối ưu tác vụ thường xuyên.
5. **Accessible:** Chữ dễ đọc, tương phản đủ, không chỉ dùng màu để truyền đạt trạng thái.
6. **Responsive:** Dùng tốt trên desktop, tablet và mobile; ưu tiên desktop cho dashboard/POS, mobile-first cho khách hàng.
7. **Data integrity:** Không tạo cảm giác một thao tác đã thành công trước khi hệ thống xác nhận; xác nhận các thao tác quan trọng.
8. **Realistic:** Dùng nội dung, dữ liệu mẫu và trạng thái phù hợp nghiệp vụ cửa hàng trái cây.
9. **Maintainable:** Ưu tiên component tái sử dụng, token thiết kế và cấu trúc Angular rõ ràng.
10. **Honest UI:** Không hiển thị số liệu, giao dịch, cảnh báo hay dữ liệu “thời gian thực” giả như dữ liệu thật. Dữ liệu demo phải được nhận diện là demo.

---

## 2. Định hướng phong cách thiết kế

### 2.1. Từ khóa phong cách

- Fresh, natural, modern, clean, approachable.
- Professional retail dashboard.
- White-first layout, nền sáng, nhiều khoảng trắng.
- Màu xanh lá làm màu thương hiệu; màu trái cây chỉ dùng làm điểm nhấn có kiểm soát.
- Bố cục gọn, phân cấp rõ, hạn chế trang trí không phục vụ nghiệp vụ.
- Bo góc vừa phải, đường viền nhẹ, bóng đổ tinh tế.
- Icon đơn giản, đồng nhất về nét và kích thước.

### 2.2. Không sử dụng

- Không dùng gradient rực rỡ làm nền chính.
- Không dùng quá nhiều màu bão hòa hoặc mỗi card một màu khác nhau.
- Không dùng glassmorphism, hiệu ứng phát sáng, 3D hoặc animation phô trương.
- Không đặt ảnh trái cây trang trí lớn trong màn hình quản trị nếu làm giảm diện tích làm việc.
- Không lạm dụng card lồng trong card, đường viền dày, shadow nặng hoặc góc bo quá tròn.
- Không dùng emoji làm icon nghiệp vụ chính.
- Không tạo dashboard chỉ gồm nhiều biểu đồ đẹp nhưng thiếu thông tin và thao tác hữu ích.
- Không dùng Lorem ipsum hoặc nhãn chung chung như “Item 1”, “Product Name” trong bản demo cuối.

---

## 3. Design tokens

Dùng token tập trung, không rải mã màu, khoảng cách hoặc radius tùy ý trong từng component.

### 3.1. Bảng màu đề xuất

| Token | Giá trị | Cách dùng |
|---|---|---|
| `color-brand-700` | `#246B45` | Nút chính, liên kết quan trọng, trạng thái đang chọn |
| `color-brand-600` | `#2F855A` | Màu thương hiệu chính |
| `color-brand-100` | `#E8F5EC` | Nền nhẹ cho khu vực được chọn |
| `color-brand-50` | `#F4FAF5` | Nền phụ rất nhẹ |
| `color-bg` | `#F7F9F7` | Nền ứng dụng |
| `color-surface` | `#FFFFFF` | Card, bảng, form |
| `color-text-primary` | `#1F2933` | Tiêu đề và nội dung chính |
| `color-text-secondary` | `#5F6B66` | Mô tả, metadata |
| `color-border` | `#DDE5DF` | Viền input, bảng, phân cách |
| `color-success` | `#237A45` | Thành công, đã hoàn tất |
| `color-warning` | `#A86400` | Sắp hết hạn, cần chú ý |
| `color-danger` | `#B42318` | Lỗi, hết hạn, hủy hoặc thao tác nguy hiểm |
| `color-info` | `#175CD3` | Thông tin trung tính |

**Quy tắc màu:**
- Nền chính là trắng hoặc xám xanh rất nhạt.
- Màu thương hiệu dùng có chủ đích, không tô xanh mọi thành phần.
- Màu trạng thái phải đi cùng nhãn chữ và/hoặc icon.
- Đảm bảo tương phản văn bản; không đặt chữ nhỏ màu nhạt trên nền sáng.
- Không dùng màu đỏ chỉ để trang trí.
- Với biểu đồ, dùng bảng màu có phân biệt rõ và nhãn trực tiếp khi phù hợp.

### 3.2. Typography

- Font ưu tiên: `Inter`, nếu không có thì dùng font sans-serif hệ thống.
- Nội dung giao diện dùng tiếng Việt có dấu đầy đủ.
- Cỡ chữ tham khảo:
  - Page title: 24–30 px, weight 600–700.
  - Section title: 18–20 px, weight 600.
  - Body: 14–16 px.
  - Label/input: 14 px.
  - Helper text: tối thiểu 12 px, chỉ dùng cho nội dung phụ.
  - Table data: 13–14 px, ưu tiên khả năng đọc.
- Dùng tối đa 2–3 mức weight trong một vùng giao diện.
- Không dùng chữ in hoa toàn bộ cho tiêu đề dài.
- Không cắt cụt thông tin quan trọng như tên sản phẩm, số lượng, giá hoặc trạng thái đơn.

### 3.3. Spacing, kích thước và hình dạng

Dùng thang spacing dựa trên bội số 4 px:

`4, 8, 12, 16, 20, 24, 32, 40, 48, 64 px`

- Padding trang desktop: 24–32 px.
- Khoảng cách giữa section: 24–32 px.
- Padding card: 16–24 px.
- Khoảng cách giữa label và input: 6–8 px.
- Chiều cao input/nút tiêu chuẩn: 40–44 px.
- Vùng bấm tối thiểu trên mobile: khoảng 44 × 44 px.
- Radius input/nút: 8–10 px.
- Radius card: 12 px.
- Viền thường: 1 px.
- Shadow nhẹ và chỉ dùng khi giúp phân tầng bề mặt.

### 3.4. Iconography

- Dùng một bộ icon nhất quán, ví dụ Lucide hoặc Angular Material Icons.
- Icon có cùng phong cách nét, kích thước chuẩn 16/20/24 px.
- Nút chỉ có icon phải có tooltip hoặc accessible label.
- Không dùng icon khó hiểu thay cho nhãn trong các thao tác quan trọng.
- Dùng icon cộng với chữ cho các hành động chính như “Thêm sản phẩm”, “Tạo phiếu nhập”.

---

## 4. Layout và điều hướng

### 4.1. Khu vực quản trị

Dùng bố cục dashboard nhất quán:

- Sidebar bên trái có thể thu gọn.
- Header trên cùng gồm breadcrumb hoặc tên trang, thông báo, hồ sơ người dùng.
- Khu vực nội dung chính có tiêu đề, mô tả ngắn khi cần và hành động chính.
- Bộ lọc đặt gần bảng dữ liệu.
- Không để sidebar chiếm quá nhiều chiều ngang.
- Trên màn hình nhỏ, sidebar chuyển thành drawer/menu.

Menu gợi ý:

- Tổng quan
- Sản phẩm
- Danh mục
- Kho hàng
- Phiếu nhập
- Đơn hàng
- Bán hàng tại quầy (POS)
- Khách hàng
- Nhà cung cấp
- Báo cáo
- Người dùng & phân quyền
- Cài đặt

Chỉ hiển thị mục menu phù hợp với vai trò. Tuy nhiên, ẩn menu không thay thế cho kiểm tra phân quyền ở backend.

### 4.2. Khu vực khách hàng

- Header rõ ràng, logo/tên cửa hàng, tìm kiếm, giỏ hàng, đăng nhập/tài khoản.
- Trang danh sách sản phẩm có tìm kiếm, lọc danh mục, khoảng giá và sắp xếp.
- Card sản phẩm ưu tiên ảnh, tên, giá/kg hoặc đơn vị bán, trạng thái còn hàng và hành động.
- Chi tiết sản phẩm thể hiện nguồn gốc, mô tả, đơn vị, giá và tình trạng còn hàng.
- Giỏ hàng và checkout phải làm rõ số lượng, đơn giá, tạm tính, giảm giá, phí giao hàng nếu có và tổng thanh toán.
- Không tự thêm phí, khuyến mãi hoặc cam kết giao hàng khi backend chưa cung cấp.
- Thiết kế tốt trên màn hình điện thoại.

### 4.3. Màn hình POS

POS ưu tiên tốc độ và độ chính xác:

- Tìm kiếm sản phẩm nhanh, hỗ trợ tìm theo tên/mã.
- Khu vực giỏ hóa đơn dễ nhìn, các dòng hàng dễ chỉnh sửa.
- Đơn vị kg phải được thể hiện rõ; hỗ trợ số thập phân hợp lý, ví dụ `2,5 kg`.
- Hiển thị đơn giá theo đơn vị và thành tiền theo dòng.
- Tổng tiền nổi bật nhưng không lấn át thông tin giỏ hàng.
- Nút thanh toán rõ ràng; thao tác hủy/xóa giỏ cần xác nhận khi có nguy cơ mất dữ liệu.
- Có trạng thái đang xử lý để tránh gửi thanh toán nhiều lần.
- Tối ưu thao tác bằng bàn phím nếu phù hợp.
- Không để nhân viên nhầm “số lượng” với “khối lượng kg”.

---

## 5. Quy tắc theo loại trang

### 5.1. Dashboard

Chỉ đưa vào các chỉ số hỗ trợ quyết định:
- Doanh thu theo khoảng thời gian được chọn.
- Số đơn hàng.
- Giá trị đơn trung bình nếu có dữ liệu phù hợp.
- Sản phẩm bán chạy.
- Lô sắp hết hạn.
- Tồn kho thấp.
- Hao hụt/hàng hỏng.

Quy tắc:
- Mỗi KPI có nhãn rõ, đơn vị, kỳ báo cáo và cách tính nhất quán.
- Bộ lọc ngày ảnh hưởng đồng bộ tới những thành phần liên quan.
- Biểu đồ phải có tiêu đề, đơn vị, chú giải và trạng thái không có dữ liệu.
- Không hiển thị phần trăm tăng/giảm nếu không có kỳ so sánh hợp lệ.
- Không bịa dữ liệu để làm dashboard trông đầy đặn.
- Cảnh báo gần hết hạn phải dẫn tới danh sách lô liên quan.

### 5.2. Danh sách và bảng dữ liệu

Bảng là thành phần chính cho màn hình quản trị:

- Cột quan trọng đặt về bên trái.
- Căn trái cho chữ; căn phải cho số tiền và số lượng khi phù hợp.
- Tiêu đề cột rõ nghĩa và thống nhất.
- Hỗ trợ tìm kiếm, lọc, sắp xếp và phân trang khi số lượng dữ liệu lớn.
- Giữ lại bộ lọc khi người dùng mở chi tiết rồi quay lại, nếu khả thi.
- Không dùng màu nền khác nhau cho từng dòng nếu không có lý do nghiệp vụ.
- Thao tác từng dòng đặt ở cột cuối hoặc menu hành động.
- Trên mobile, cho phép cuộn ngang có chủ đích hoặc chuyển thành danh sách/card; không ép toàn bộ cột vào màn hình hẹp.
- Có trạng thái loading, empty, error và retry.
- Phân biệt “không có dữ liệu” với “chưa tải được dữ liệu”.

Cột dữ liệu gợi ý:
- Sản phẩm: ảnh thu nhỏ, tên, mã, danh mục, đơn vị, giá bán, trạng thái.
- Lô hàng: mã lô, sản phẩm, ngày nhập, hạn sử dụng, số lượng ban đầu, số lượng còn, trạng thái.
- Đơn hàng: mã đơn, khách hàng, thời gian, tổng tiền, trạng thái đơn, trạng thái thanh toán.
- Phiếu nhập: mã phiếu, nhà cung cấp, ngày nhập, tổng tiền, trạng thái.

### 5.3. Form và nhập liệu

- Mỗi input phải có label hiển thị; không chỉ dựa vào placeholder.
- Dùng loại input phù hợp: email, số điện thoại, ngày, số, tiền.
- Nhóm trường theo chủ đề, sắp xếp theo trình tự công việc.
- Trường bắt buộc được đánh dấu rõ.
- Thông báo lỗi đặt gần trường liên quan, viết dễ hiểu và nêu cách sửa.
- Giữ dữ liệu đã nhập nếu submit thất bại.
- Không xóa form sau lỗi mạng hoặc lỗi validation.
- Nút chính có trạng thái loading/disabled trong lúc gửi.
- Phân biệt nút “Lưu”, “Lưu và tiếp tục”, “Hủy”.
- Cảnh báo trước khi rời form có thay đổi chưa lưu nếu phù hợp.
- Validation frontend giúp trải nghiệm; backend vẫn phải xác thực toàn bộ dữ liệu.

### 5.4. Modal, drawer và xác nhận

Dùng modal cho tác vụ ngắn, tập trung; không đặt form dài hoặc quy trình nhiều bước vào modal nếu một trang riêng dễ dùng hơn.

Xác nhận trước khi:
- Xóa dữ liệu.
- Hủy đơn đã xử lý.
- Ghi nhận hủy/hỏng hàng.
- Điều chỉnh tồn kho thủ công.
- Hoàn tiền hoặc thực hiện thao tác khó đảo ngược.

Nội dung xác nhận phải nêu rõ đối tượng và hậu quả. Tránh thông báo mơ hồ như “Bạn có chắc không?”.

### 5.5. Trạng thái và phản hồi hệ thống

Mọi thao tác bất đồng bộ phải có phản hồi rõ ràng:
- Loading: đang tải hoặc đang xử lý.
- Success: thao tác đã được server xác nhận.
- Validation error: dữ liệu chưa hợp lệ.
- Permission error: không đủ quyền.
- Not found: dữ liệu không tồn tại hoặc không còn khả dụng.
- Network/server error: thao tác chưa xác nhận thành công; cho phép thử lại khi an toàn.
- Empty state: hướng dẫn hành động tiếp theo.
- Disabled state: giải thích lý do nếu không hiển nhiên.

Không dùng toast thành công trước khi API trả kết quả thành công. Với thanh toán, không tự động retry một yêu cầu có thể tạo giao dịch mới nếu chưa có cơ chế idempotency.

---

## 6. Quy tắc nghiệp vụ phải phản ánh đúng trên UI

### 6.1. Sản phẩm và đơn vị bán

- Mỗi sản phẩm phải thể hiện đơn vị bán rõ ràng: kg, quả, hộp hoặc đơn vị được cấu hình.
- Với hàng bán theo cân nặng, cho nhập số thập phân và hiển thị đơn vị ở cạnh trường.
- Giá phải thể hiện theo đơn vị, ví dụ `65.000 ₫/kg`.
- Không giả định mọi sản phẩm đều bán theo kg.
- Sản phẩm ngừng kinh doanh không được đưa vào đơn mới; cần hiển thị trạng thái rõ ràng.

### 6.2. Lô hàng, hạn sử dụng và FEFO

- Tồn kho phải có thể xem theo sản phẩm và theo lô.
- Hiển thị ngày nhập, hạn sử dụng, số lượng còn và trạng thái lô.
- Cảnh báo hạn sử dụng theo cấu hình nghiệp vụ; không tự suy diễn ngưỡng nếu chưa thống nhất.
- Phân biệt rõ: còn hạn, sắp hết hạn, hết hạn, đã hết hàng, đã hủy.
- Lô hết hạn không được đề xuất để bán hoặc giữ hàng.
- Giao diện không tự tính tồn khả dụng khác với kết quả backend.
- FEFO (First Expired, First Out) cần được xử lý ở backend; UI có thể giải thích lô được chọn nhưng không tự quyết định tồn kho cuối cùng.

### 6.3. Hao hụt và hàng hỏng

- Không chỉ cho phép sửa số lượng tồn mà không có lý do.
- Ghi nhận loại điều chỉnh, số lượng, lô, lý do, người thực hiện và thời gian.
- Phân biệt hàng hỏng, hết hạn, thất thoát và điều chỉnh kiểm kê nếu nghiệp vụ cần.
- Trước khi xác nhận hủy hàng, cho người dùng xem lại số lượng và ảnh hưởng tồn kho.
- Báo cáo hao hụt phải dựa trên các giao dịch được ghi nhận.

### 6.4. Đơn hàng và thanh toán

- Phân biệt trạng thái đơn hàng với trạng thái thanh toán.
- Trạng thái đơn gợi ý: Chờ thanh toán, Đã xác nhận, Đang chuẩn bị, Hoàn tất, Đã hủy; chỉ dùng trạng thái mà backend hỗ trợ.
- Trạng thái thanh toán gợi ý: Chưa thanh toán, Đang xử lý, Thành công, Thất bại, Đã hoàn tiền.
- Không cho UI tự ý chuyển trạng thái vượt quy tắc nghiệp vụ.
- Hiển thị mã đơn, thời gian, các dòng hàng, đơn giá tại thời điểm mua và tổng tiền.
- Khi hủy đơn, nêu rõ liệu hàng đã được giải phóng/hoàn kho hay đang chờ xử lý.
- Nếu trạng thái chưa chắc chắn do timeout, hiển thị “Đang xác minh” hoặc thông báo tương đương thay vì khẳng định thất bại.
- Ngăn double-click gửi nhiều lần bằng trạng thái loading; backend vẫn phải xử lý idempotency.

### 6.5. Phân quyền

- Menu, nút và hành động nhạy cảm hiển thị theo vai trò/quyền.
- Không xem việc ẩn nút là biện pháp bảo mật.
- Khi backend trả 401, hướng dẫn đăng nhập lại; khi 403, thông báo không đủ quyền.
- Không hiển thị dữ liệu riêng tư hoặc dữ liệu ngoài phạm vi quyền người dùng.
- Tránh tiết lộ chi tiết kỹ thuật hoặc thông tin nhạy cảm trong thông báo lỗi.

---

## 7. Ảnh sản phẩm

- Ưu tiên ảnh thật, sáng, sạch, thể hiện đúng loại trái cây.
- Dùng tỷ lệ ảnh nhất quán trong danh sách, ví dụ 1:1.
- Ảnh phải có `alt` mô tả sản phẩm.
- Dùng ảnh thay thế khi chưa có ảnh; không để broken image.
- Cắt ảnh bằng `object-fit: cover` khi phù hợp, không kéo méo ảnh.
- Giữ kích thước ảnh thumbnail hợp lý để bảng tải nhanh.
- Upload ảnh phải có trạng thái tải lên, lỗi, xem trước và xóa/thay ảnh.
- UI chỉ gửi/hiển thị URL hoặc mã file theo hợp đồng API; không giả định ảnh phải lưu trực tiếp dạng binary trong bảng PostgreSQL.
- Không dùng ảnh minh họa sai sản phẩm hoặc ảnh có watermark không phù hợp.

---

## 8. Responsive design

### Desktop (≥ 1200 px)
- Dashboard và bảng dữ liệu dùng bố cục nhiều cột khi có lợi.
- Sidebar cố định hoặc thu gọn.
- POS tận dụng không gian rộng để hiển thị danh sách hàng và giỏ hàng song song.

### Tablet (768–1199 px)
- Giảm số cột KPI.
- Sidebar có thể thu gọn.
- Form và bảng điều chỉnh chiều rộng hợp lý.
- POS giữ các hành động chính luôn dễ truy cập.

### Mobile (< 768 px)
- Khách hàng: ưu tiên trải nghiệm mua hàng trên điện thoại.
- Quản trị: ưu tiên tác vụ nhanh, không cố nhồi toàn bộ dashboard desktop.
- Chuyển sidebar thành drawer.
- Nút chính dễ chạm; input không quá nhỏ.
- Không để nội dung tràn ngang ngoài những bảng cần cuộn có chủ đích.
- Modal phải vừa màn hình hoặc chuyển thành bottom sheet/trang riêng.
- Giỏ hàng, checkout và trạng thái đơn phải dễ đọc trên màn hình hẹp.

Không thiết kế riêng desktop rồi chỉ thu nhỏ tỷ lệ. Cần xác định nội dung nào ưu tiên, ẩn, xếp lại hoặc chuyển dạng ở từng breakpoint.

---

## 9. Accessibility và khả năng sử dụng

- Dùng HTML semantic phù hợp.
- Mọi trường nhập liệu có label liên kết.
- Có thể điều hướng bằng bàn phím; focus state nhìn thấy rõ.
- Không dùng màu làm dấu hiệu duy nhất cho trạng thái.
- Nút và liên kết có tên dễ hiểu.
- Ảnh có alt phù hợp; ảnh trang trí có alt rỗng.
- Heading theo thứ bậc hợp lý.
- Đảm bảo tương phản đủ, đặc biệt với chữ nhỏ và trạng thái.
- Không tự động chuyển trang hoặc đóng thông báo quá nhanh.
- Lỗi form nên được thông báo dễ tiếp cận và tập trung vào trường lỗi khi phù hợp.
- Biểu đồ phải có phần tóm tắt dạng văn bản hoặc dữ liệu thay thế khi cần.

---

## 10. Microcopy và ngôn ngữ giao diện

- Mặc định dùng tiếng Việt tự nhiên, ngắn gọn và nhất quán.
- Ưu tiên động từ rõ ràng: “Thêm sản phẩm”, “Tạo phiếu nhập”, “Xác nhận thanh toán”.
- Tránh nhãn chung chung: “Submit”, “OK”, “Click here”, trừ khi có lý do.
- Dùng định dạng tiền Việt Nam nhất quán, ví dụ `65.000 ₫/kg`.
- Dùng định dạng ngày giờ thống nhất, ví dụ `22/10/2026 15:30`.
- Dùng dấu phẩy cho phần thập phân trong nội dung tiếng Việt nếu toàn hệ thống thống nhất, ví dụ `2,5 kg`.
- Thông báo lỗi cần nói điều gì xảy ra và người dùng có thể làm gì tiếp theo.
- Tránh đổ lỗi cho người dùng.
- Không dùng nội dung giả gây hiểu nhầm rằng thanh toán hoặc đơn hàng đã hoàn tất.

Ví dụ:
- Tốt: “Không thể nhập kho vì số lượng phải lớn hơn 0.”
- Tốt: “Lô LOT-001 đã hết hạn và không thể dùng cho đơn hàng mới.”
- Tốt: “Chưa thể xác nhận trạng thái thanh toán. Vui lòng kiểm tra lại đơn trước khi thử lại.”
- Tránh: “Error 500!!!”, “Something went wrong”, “Thành công!” khi server chưa xác nhận.

---

## 11. Quy ước Angular UI

### 11.1. Kiến trúc giao diện

Tổ chức theo feature và tái sử dụng component:

```text
src/app/
├── core/
│   ├── auth/
│   ├── guards/
│   ├── interceptors/
│   ├── layout/
│   └── services/
├── shared/
│   ├── components/
│   ├── directives/
│   ├── pipes/
│   └── ui/
├── features/
│   ├── auth/
│   ├── shop/
│   ├── products/
│   ├── inventory/
│   ├── procurement/
│   ├── orders/
│   ├── payments/
│   ├── pos/
│   ├── customers/
│   ├── reports/
│   └── users/
└── app.routes.ts
```

Điều chỉnh cấu trúc này theo service boundary và quy mô thực tế; không tạo abstraction quá mức.

### 11.2. Component và trạng thái

- Dùng shared components cho Button, FormField, StatusBadge, DataTable, ConfirmDialog, EmptyState, LoadingState, ErrorState, PageHeader và FilterBar.
- Không sao chép cùng một kiểu bảng hoặc form ở nhiều feature.
- Trạng thái loading/error/empty/success phải được thiết kế thống nhất.
- Ưu tiên Reactive Forms cho form nghiệp vụ phức tạp.
- Dùng Angular Router và lazy loading theo feature khi phù hợp.
- Route guard chỉ phục vụ điều hướng UX; backend là nơi quyết định quyền truy cập.
- Dùng `HttpClient` qua lớp service/data-access; component không nên chứa trực tiếp logic gọi API phức tạp.
- Không hard-code URL API, vai trò, trạng thái hoặc giá trị nghiệp vụ ở nhiều nơi.
- Dùng environment/configuration phù hợp cho URL API.
- Tránh dùng `any` tùy tiện; định nghĩa TypeScript interfaces/types cho DTO.
- Dọn subscription và quản lý lifecycle theo cách phù hợp với phiên bản Angular đang dùng.

### 11.3. Quy tắc tích hợp API

- Tuân theo API contract đã thống nhất với FastAPI.
- Phân biệt lỗi validation, xác thực, phân quyền, không tìm thấy, xung đột và lỗi server.
- Không giả lập dữ liệu thành công khi API thật thất bại, trừ khi đang ở chế độ demo được ghi rõ.
- Chuẩn hóa cách hiển thị lỗi và thông báo.
- Không để component tự sửa dữ liệu backend trả về theo cách làm sai lệch nghiệp vụ.
- Có xử lý timeout/mất mạng và nút thử lại khi an toàn.
- Với thao tác tạo đơn/thanh toán/điều chỉnh kho, tránh gửi trùng và phản ánh trạng thái chờ xử lý.

---

## 12. Quy tắc nội dung và dữ liệu mẫu

Dữ liệu demo nên gần với nghiệp vụ Việt Nam, ví dụ:

- Xoài cát Hòa Lộc — `65.000 ₫/kg`
- Táo Fuji — `85.000 ₫/kg`
- Cam sành — `32.000 ₫/kg`
- Chuối — `25.000 ₫/kg`

Đây chỉ là **dữ liệu minh họa**, không phải giá thị trường hay giá cố định của hệ thống.

- Dùng tên, mã sản phẩm, mã lô và mã đơn nhất quán trong toàn bộ luồng demo.
- Thể hiện đúng đơn vị, ngày nhập, hạn sử dụng và số lượng.
- Không dùng dữ liệu cá nhân thật trong demo.
- Nếu dữ liệu được mock, phải ghi rõ trong tài liệu hoặc giao diện demo.
- Không để các số liệu dashboard mâu thuẫn với danh sách đơn và giao dịch mẫu.

---

## 13. Animation và tương tác

- Chỉ dùng animation ngắn, có mục đích: mở menu, chuyển trạng thái, phản hồi thao tác.
- Ưu tiên chuyển động tinh tế khoảng 150–250 ms khi phù hợp.
- Không dùng animation làm chậm các thao tác thường xuyên.
- Tôn trọng cài đặt giảm chuyển động của hệ điều hành khi có thể.
- Hover không phải cách duy nhất để truy cập chức năng.
- Nút phải có trạng thái hover, focus, active, disabled và loading phù hợp.
- Không thêm tương tác giả cho các thành phần chỉ mang tính trang trí.

---

## 14. Bảo mật và quyền riêng tư trong UI

- Không hiển thị mật khẩu, token JWT hoặc secret trong giao diện.
- Không đưa token, mật khẩu hay thông tin nhạy cảm vào log frontend.
- Không hiển thị stack trace, SQL, nội dung exception nội bộ hoặc thông tin cấu hình nhạy cảm cho người dùng.
- Che bớt dữ liệu nhạy cảm khi nghiệp vụ yêu cầu.
- Xác nhận các hành động nguy hiểm và thông báo rõ kết quả.
- Không xem frontend là lớp bảo vệ duy nhất; backend phải xác thực và phân quyền.
- Không lưu thông tin thanh toán nhạy cảm nếu không cần thiết.

---

## 15. Prompt nền dùng cho AI thiết kế UI

Sao chép prompt này vào đầu mỗi yêu cầu thiết kế màn hình hoặc giao diện:

> Bạn là Senior Product Designer và Senior Angular UI Engineer, chịu trách nhiệm thiết kế UI/UX cho **FruitStore Management System**, hệ thống quản lý cửa hàng trái cây dùng Angular + TypeScript ở frontend và FastAPI REST API ở backend.
>
> Tuân thủ tuyệt đối tài liệu `UI_UX_DESIGN_RULES.md`. Thiết kế phải hiện đại, sạch, chuyên nghiệp, white-first, thân thiện với thực phẩm tươi; dùng xanh lá làm màu thương hiệu, typography dễ đọc, spacing nhất quán và component có thể tái sử dụng. Giao diện mặc định bằng tiếng Việt.
>
> Hãy thiết kế theo nghiệp vụ thực tế, không chỉ tạo mockup đẹp. Phải có hierarchy rõ ràng, responsive, accessibility cơ bản và các trạng thái loading, empty, error, success, disabled, validation. Dùng dữ liệu mẫu tiếng Việt hợp lý và không giả vờ rằng dữ liệu demo là dữ liệu thật.
>
> Với nghiệp vụ trái cây, thể hiện chính xác đơn vị kg/đơn vị bán, giá theo đơn vị, tồn kho theo lô, hạn sử dụng, FEFO, hao hụt, trạng thái đơn và trạng thái thanh toán. Không tự suy diễn quy tắc nghiệp vụ chưa được cung cấp. Không để UI quyết định thay backend các nghiệp vụ quan trọng như tồn kho, giá cuối cùng, phân quyền hoặc thanh toán.
>
> Với Angular, ưu tiên feature-based structure, shared components, Reactive Forms khi phù hợp, Angular Router, HttpClient qua service/data-access layer, type-safe DTO và tách biệt UI khỏi business logic. Không hard-code API URL hoặc lặp lại design tokens.
>
> Trước khi hoàn thành, tự rà soát theo checklist: nhất quán design system, dễ thao tác, responsive, accessibility, trạng thái lỗi/loading/empty, đúng nghiệp vụ, không có dữ liệu giả gây hiểu nhầm, và không có nút/đường dẫn không hoạt động.
>
> **Màn hình/chức năng cần thiết kế:** [MÔ TẢ MÀN HÌNH]
>
> **Vai trò người dùng:** [ADMIN / MANAGER / STAFF / WAREHOUSE STAFF / CUSTOMER]
>
> **Tác vụ chính:** [MÔ TẢ TÁC VỤ]
>
> **Dữ liệu/API liên quan:** [API CONTRACT HOẶC DTO NẾU ĐÃ CÓ]
>
> **Đầu ra mong muốn:** [WIREFRAME / MOCKUP / ANGULAR COMPONENT / HTML-CSS / DESIGN SPEC]

---

## 16. Prompt riêng theo nhóm màn hình

### 16.1. Admin Dashboard

> Thiết kế Admin Dashboard cho FruitStore Management System theo `UI_UX_DESIGN_RULES.md`. Dùng sidebar, header và vùng nội dung nhất quán. Hiển thị KPI doanh thu, số đơn, lô sắp hết hạn, tồn kho thấp và hao hụt; có bộ lọc ngày/kỳ báo cáo. Biểu đồ phải có đơn vị, chú giải và trạng thái không có dữ liệu. Mỗi cảnh báo cần dẫn đến danh sách dữ liệu liên quan. Không tạo số liệu tăng trưởng nếu không có dữ liệu kỳ so sánh. Thiết kế responsive và dùng tiếng Việt.

### 16.2. Quản lý sản phẩm

> Thiết kế trang quản lý sản phẩm cho Manager. Có tìm kiếm, lọc danh mục/trạng thái, phân trang, bảng sản phẩm, ảnh thumbnail, mã, tên, danh mục, đơn vị bán, giá, trạng thái và thao tác. Form thêm/sửa cần label, validation, preview ảnh, đơn vị bán rõ ràng và thông báo lỗi gần trường. Không mặc định tất cả sản phẩm đều tính theo kg. Có loading, empty, error và success state.

### 16.3. Quản lý kho theo lô

> Thiết kế trang Inventory cho Warehouse Staff/Manager. Cho xem tồn kho theo sản phẩm và lô; hiển thị mã lô, ngày nhập, hạn sử dụng, số lượng nhập, số lượng còn, số lượng đang giữ và trạng thái. Có bộ lọc theo sản phẩm, tình trạng và hạn sử dụng. Làm nổi bật lô sắp hết hạn/hết hạn bằng nhãn chữ và màu trạng thái. Hỗ trợ xem lịch sử biến động và thao tác nhập kho/điều chỉnh/hủy hàng theo quyền. Không cho phép sửa tồn kho âm hoặc bỏ qua lý do điều chỉnh.

### 16.4. Phiếu nhập hàng

> Thiết kế quy trình tạo phiếu nhập hàng. Cho chọn nhà cung cấp, ngày nhập, sản phẩm, số lượng theo đơn vị, giá nhập, mã lô và hạn sử dụng. Hỗ trợ nhiều dòng sản phẩm, tự tính thành tiền từ dữ liệu nhập hợp lệ và hiển thị tổng tiền. Phân biệt lưu nháp và xác nhận nhập kho nếu backend hỗ trợ. Xác nhận trước khi ghi nhận nhập kho; tránh gửi trùng khi người dùng bấm nhiều lần. Thể hiện lỗi theo từng dòng và giữ dữ liệu khi có lỗi.

### 16.5. POS bán hàng tại quầy

> Thiết kế màn hình POS desktop-first cho Staff. Bố cục gồm tìm kiếm sản phẩm, danh sách/kết quả sản phẩm và giỏ hóa đơn. Cho nhập khối lượng thập phân như `2,5 kg`, hiển thị đơn giá theo kg và thành tiền mỗi dòng. Tổng tiền, phương thức thanh toán và nút xác nhận phải rõ ràng. Có thể xóa/sửa dòng hàng dễ dàng; xác nhận khi hủy hóa đơn. Trong lúc thanh toán, khóa thao tác gửi lặp và hiển thị trạng thái xử lý. Không tự khẳng định thanh toán thành công trước phản hồi từ backend.

### 16.6. Cửa hàng trực tuyến

> Thiết kế storefront cho khách hàng trên mobile và desktop. Có header, tìm kiếm, danh mục, danh sách sản phẩm, ảnh thật, giá theo đơn vị, tình trạng còn hàng, giỏ hàng và checkout. Checkout phải minh bạch tạm tính, giảm giá, phí giao hàng nếu có và tổng tiền. Không thêm khoản phí hoặc cam kết chưa được backend cung cấp. Có trạng thái hết hàng, loading, empty cart, lỗi tải dữ liệu và xác nhận đặt hàng. Ngôn ngữ tiếng Việt tự nhiên.

### 16.7. Chi tiết đơn hàng

> Thiết kế trang chi tiết đơn hàng cho Staff/Manager/Customer tùy quyền. Hiển thị mã đơn, thời gian, khách hàng phù hợp quyền, danh sách sản phẩm, số lượng/khối lượng, đơn giá tại thời điểm mua, tổng tiền, trạng thái đơn riêng biệt với trạng thái thanh toán và lịch sử trạng thái nếu có. Chỉ hiển thị hành động hợp lệ theo trạng thái và quyền. Nếu trạng thái thanh toán chưa xác định, thể hiện rõ đang xác minh; không tự đổi sang thất bại.

### 16.8. Báo cáo

> Thiết kế trang báo cáo cho Manager. Có bộ lọc thời gian và các báo cáo doanh thu, số đơn, sản phẩm bán chạy, tồn kho, lô sắp hết hạn và hao hụt. Mỗi báo cáo phải có đơn vị, phạm vi thời gian và trạng thái không có dữ liệu. Không cộng doanh thu từ đơn chưa thanh toán nếu quy tắc báo cáo không cho phép. Cho phép xuất file chỉ khi backend cung cấp chức năng. Ưu tiên khả năng đọc và quyết định, không trang trí quá mức.

### 16.9. Đăng nhập và phân quyền

> Thiết kế màn hình đăng nhập sạch, dễ dùng và phù hợp nhận diện FruitStore. Có email/tên đăng nhập, mật khẩu, hiện/ẩn mật khẩu, validation, loading và lỗi xác thực dễ hiểu. Không hiển thị token hoặc chi tiết lỗi backend. Sau đăng nhập, điều hướng theo quyền được backend xác định. Không coi việc ẩn route hoặc nút ở frontend là biện pháp bảo mật.

---

## 17. Checklist review UI/UX trước khi merge

Đánh dấu từng mục trước khi xem một màn hình là hoàn thành:

### Visual design
- [ ] Đúng palette, typography, spacing, radius và icon style.
- [ ] Có phân cấp thị giác rõ ràng.
- [ ] Không có trang trí dư thừa hoặc shadow/gradient quá mức.
- [ ] Nội dung tiếng Việt có dấu, nhất quán.

### Usability
- [ ] Người dùng biết trang này dùng để làm gì.
- [ ] Hành động chính nổi bật và dễ tìm.
- [ ] Bộ lọc và thao tác phù hợp công việc thực tế.
- [ ] Form có label, validation và giữ dữ liệu khi lỗi.
- [ ] Thao tác nguy hiểm có xác nhận.

### States
- [ ] Loading.
- [ ] Empty.
- [ ] Error và retry khi phù hợp.
- [ ] Success sau khi server xác nhận.
- [ ] Disabled/permission state.
- [ ] Trạng thái bất định khi timeout được xử lý trung thực.

### Business correctness
- [ ] Đúng đơn vị và định dạng giá.
- [ ] Lô hàng/hạn sử dụng/trạng thái hiển thị rõ.
- [ ] Trạng thái đơn và thanh toán không bị gộp nhầm.
- [ ] UI không tự quyết định tồn kho, giá cuối cùng hoặc quyền.
- [ ] Không gửi thao tác trùng dễ gây ảnh hưởng dữ liệu.

### Responsive/accessibility
- [ ] Dùng được ở desktop, tablet và mobile theo vai trò.
- [ ] Có keyboard focus rõ.
- [ ] Có label/accessible name và alt ảnh phù hợp.
- [ ] Không chỉ dùng màu để biểu đạt trạng thái.
- [ ] Nội dung không tràn hoặc bị cắt mất thông tin quan trọng.

### Engineering
- [ ] Component tái sử dụng hợp lý.
- [ ] Design tokens không bị hard-code rải rác.
- [ ] API access nằm trong lớp service/data-access phù hợp.
- [ ] DTO có kiểu dữ liệu rõ.
- [ ] Không có nút/đường dẫn giả hoặc dữ liệu demo gây hiểu nhầm.

---

## 18. Quy tắc ưu tiên khi có xung đột

Nếu các yêu cầu mâu thuẫn, ưu tiên theo thứ tự:

1. Tính đúng đắn nghiệp vụ và an toàn dữ liệu.
2. Khả năng sử dụng và accessibility.
3. Nhất quán design system.
4. Responsive và hiệu năng.
5. Tính thẩm mỹ và hiệu ứng trang trí.

Không được hy sinh độ chính xác của tồn kho, thanh toán, phân quyền hoặc trạng thái đơn hàng chỉ để làm giao diện đơn giản hơn.

---

## 19. Quy tắc cập nhật tài liệu

- Khi quyết định đổi màu, font, spacing hoặc component dùng chung, cập nhật token/quy tắc tại file này trước khi áp dụng diện rộng.
- Khi API hoặc nghiệp vụ thay đổi, cập nhật prompt và màn hình liên quan.
- Không thêm quy tắc riêng cho một trang nếu có thể giải quyết bằng quy tắc chung.
- Mọi ngoại lệ phải có lý do rõ ràng.
- Dùng file này làm nguồn chuẩn chung cho designer, frontend developer và công cụ AI.

**Phiên bản:** 1.0  
**Dự án:** FruitStore Management System  
**Phạm vi:** UI/UX, Angular frontend, prompt thiết kế và review giao diện
