# Frontend Design Rules & Guidelines

> Nguồn: `anthropics/skills/frontend-design`  
> Tài liệu quy chuẩn thiết kế giao diện cao cấp, chống rập khuôn mẫu (Anti-template), tối ưu typography, phân cấp thông tin và định hướng thẩm mỹ cho hệ thống FruitStore.

---

## 1. Ground your designs in the subject matter (Bám sát ngữ cảnh thực tế)

Xây dựng thiết kế dựa trên đúng bản chất ngành hàng: **bán lẻ trái cây, quản lý chuỗi kho tươi và vận hành nông sản sạch**.  
- Ngành hàng nông sản tươi đòi hỏi cảm giác: *tươi mới, sạch sẽ, đáng tin cậy, thao tác nhanh*.
- Tránh đưa các yếu tố trang trí xa rời nghiệp vụ vào giao diện quản trị/POS.
- Xây dựng với nội dung và số liệu sát thực tế xuyên suốt (kg, hạn sử dụng theo ngày, bảo quản mát 2-8°C, mã lô, v.v.).

---

## 2. Design principles (Nguyên tắc thiết kế)

### 2.1. Điểm nhấn đầu tiên (Hero / Focal point)
- Đối với giao diện web, điểm nhìn đầu tiên phải là yếu tố đặc trưng nhất của chủ đề: dòng tiêu đề rõ nghĩa, thông số cốt lõi, bảng dữ liệu quan trọng hoặc thao tác nghiệp vụ chính.
- Không lạm dụng số to vô nghĩa hay gradient sặc sỡ làm nền.

### 2.2. Typography mang linh hồn của giao diện
- **Họ font:** Sử dụng 1 họ font nhất quán (Inter) hoặc tối đa 2 họ font phân biệt rõ vai trò (Display vs Body).
- **Phân cấp tỉ lệ chữ (Type scale):** Tuân thủ phân cấp rõ ràng theo *The Elements of Typographic Style*, trọng lượng (font-weight), độ rộng và khoảng cách dòng có chủ đích.
- **Độ dài dòng:** Giữ độ dài dòng dưới 80 ký tự để dễ đọc.
- **Những điều cần tránh:**
  - Không bôi đậm/đổi màu ngẫu hứng chỉ một từ đơn lẻ trong tiêu đề.
  - Không viết hoa toàn bộ (ALL-CAPS) cho các nhãn dài.
  - Không thêm nhãn phụ rườm rà không cần thiết phía trên nội dung.

### 2.3. Cấu trúc thị giác mang giá trị thông tin
- Đường viền (borders), đường phân cách (dividers), đánh số thứ tự chỉ dùng khi bản thân nội dung có tính tuần tự (như quy trình các bước hoặc dòng thời gian). Không gắn số thứ tự (01, 02, 03) làm đồ trang trí.

### 2.4. Tiết chế chuyển động (Motion & Animation)
- Hạn chế các hiệu ứng tự động chạy làm xao nhãng.
- Chuyển động chỉ xuất hiện khi người dùng thao tác (mở dropdown, xác nhận đơn hàng, mở drawer) để phản hồi rõ điều gì vừa thay đổi.

---

## 3. Tránh các "dấu vết" giao diện AI rập khuôn (Anti-clichés)

Cần cảnh giác và loại bỏ 5 kiểu thiết kế rập khuôn thường gặp của AI:
1. **Nền vàng kem nhạt (#F4F1EA) + font có chân tương phản cao + màu cam đất/terracotta (#D97757).**
2. **Nền đen kịt + một màu xanh neon hoặc đỏ chói lọi làm điểm nhấn duy nhất.**
3. **Bố cục kiểu báo giấy với viền mảnh như sợi tóc, bo góc 0px.**
4. **Bộ kit thẻ SaaS lặp đi lặp lại:** Mọi nội dung đều bị nhét vào các card bo tròn giống hệt nhau, cùng một shadow xám nhạt `rgba(0,0,0,0.1)` và dải gradient trang trí vô nghĩa.
5. **Giao diện mẫu chung chung:** Nhãn in hoa cách chữ rộng phía trên mọi tiêu đề; chuỗi metadata nối bằng dấu chấm giữa ('A · B · C'); nhãn dạng 'WORD — fragment' với dấu gạch ngang dài; luôn gắn '→' vào mọi nút bấm.

---

## 4. Quy trình 2 bước: Lập kế hoạch & Phản biện (Plan, Review, Build, Critique)

1. **Bước 1 — Lập kế hoạch Design Tokens:**
   - **Màu sắc (Color):** Xác định bảng màu cốt lõi gồm 4–6 mã hex có tên gọi rõ ràng.
   - **Font chữ (Type):** Vai trò cụ thể của từng cấp chữ.
   - **Bố cục (Layout):** Khái niệm bố cục, căn chỉnh (trái, giữa, hai bên) trước khi code.
2. **Bước 2 — Phản biện (Self-critique):**
   - Đặt câu hỏi: *"Phần này có bị giống một template tạo sẵn bất kỳ không?"* Nếu có, chỉnh sửa ngay để tạo dấu ấn riêng cho thương hiệu Fresh Orchard.

---

## 5. Tiết chế và Tối giản (Restraint)

- **Dồn sự nổi bật vào một vị trí chính:** Hãy để 1 thành phần làm điểm nhấn đáng nhớ, các thành phần xung quanh giữ sự tinh tế, yên tĩnh và kỷ luật.
- **Quy chuẩn chất lượng ngầm định:** Responsive mượt mà trên mobile, bàn phím điều hướng được (visible focus), màu sắc tương phản đạt chuẩn trợ năng (accessibility).

---

## 6. Văn phong và Ngôn ngữ trong thiết kế (Copywriting)

- Từ ngữ xuất hiện trong giao diện chỉ có một mục đích duy nhất: **Giúp người dùng dễ hiểu và thao tác nhanh nhất**.
- **Viết từ góc nhìn người dùng:** Dùng từ ngữ đơn giản, gần gũi với nghiệp vụ bán hàng thực tế (Ví dụ: *"Cân điện tử"*, *"Phiếu nhập kho"*, *"Lô hàng FEFO"*).
- **Dùng thể chủ động:** Nút bấm hành động phải nói rõ điều gì sẽ xảy ra: *"Lưu thay đổi"*, *"In hóa đơn"*, *"Xác nhận nhập kho"*.
- **Thông báo lỗi mang tính hướng dẫn:** Khi xảy ra lỗi, giải thích rõ nguyên nhân và cách khắc phục ngay tại vị trí lỗi, không xin lỗi dài dòng hay thông báo mơ hồ.

