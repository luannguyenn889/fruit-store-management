import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# Khởi tạo Canvas 4K (3200 x 1800)
fig, ax = plt.subplots(figsize=(32, 18), dpi=150)
ax.set_xlim(0, 3200)
ax.set_ylim(0, 1800)
ax.axis('off')

fig.patch.set_facecolor('#F8FAFC')
ax.set_facecolor('#F8FAFC')

plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'Tahoma']
plt.rcParams['axes.unicode_minus'] = False

def draw_box(x, y, w, h, bg_color, border_color=None, r=16, lw=1.5, zorder=2):
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle=f"round,pad=0,rounding_size={r}",
                         facecolor=bg_color, edgecolor=border_color or bg_color,
                         linewidth=lw, zorder=zorder)
    ax.add_patch(box)
    return box

# ================= 1. HEADER BANNER =================
draw_box(400, 1630, 2400, 120, '#E0F2FE', '#BAE6FD', r=30, lw=2)
ax.text(1600, 1710, "KIẾN TRÚC SOA CỦA DỰ ÁN (SERVICE-ORIENTED ARCHITECTURE)", 
        fontsize=34, fontweight='bold', color='#0369A1', ha='center', va='center')
ax.text(1600, 1662, "HỆ THỐNG QUẢN LÝ CỬA HÀNG TRÁI CÂY - FRUITSTORE (DATABASE-PER-SERVICE)", 
        fontsize=22, fontweight='bold', color='#0284C7', ha='center', va='center')

# ================= 2. ACTORS (NGƯỜI DÙNG) =================
draw_box(50, 480, 260, 1080, '#FFFFFF', '#CBD5E1', r=24, lw=2)
ax.text(180, 1500, "Người dùng", fontsize=24, fontweight='bold', color='#0F172A', ha='center', va='center')
ax.text(180, 1460, "(Actors trong hệ thống)", fontsize=14, color='#64748B', ha='center', va='center')

roles = [
    ("Khách hàng\n(Web Shop Online)", "#F0F9FF", "#0284C7", "#BAE6FD"),
    ("Thu ngân POS\n(Bán hàng tại quầy)", "#F0FDF4", "#16A34A", "#BBF7D0"),
    ("Thủ kho\n(Nhập lô, Quản lý FEFO)", "#FFFBEB", "#D97706", "#FDE68A"),
    ("Chủ cửa hàng / Admin\n(Quản trị & Báo cáo)", "#FEF2F2", "#DC2626", "#FECACA")
]
for idx, (role_name, bg, tc, bc) in enumerate(roles):
    ry = 1300 - idx * 210
    draw_box(70, ry, 220, 130, bg, bc, r=16, lw=1.5)
    ax.text(180, ry + 65, role_name, fontsize=15, fontweight='bold', color=tc, ha='center', va='center', multialignment='center')

# ================= 3. FRONTEND (ANGULAR WEB) =================
draw_box(370, 480, 310, 1080, '#FFF1F2', '#FDA4AF', r=24, lw=2)
ax.text(525, 1500, "Frontend Client", fontsize=24, fontweight='bold', color='#9F1239', ha='center', va='center')

draw_box(475, 1350, 100, 100, '#E11D48', '#BE123C', r=20)
ax.text(525, 1400, "A", fontsize=60, fontweight='bold', color='#FFFFFF', ha='center', va='center')

ax.text(525, 1300, "Angular Web App", fontsize=21, fontweight='bold', color='#9F1239', ha='center', va='center')
ax.text(525, 1260, "http://localhost:4200", fontsize=15, fontweight='bold', color='#E11D48', ha='center', va='center')

fe_modules = [
    ("Shop Online Portal", "Xem hàng, giỏ hàng, đặt đơn"),
    ("Màn hình POS Bán lẻ", "Cân kg, tính tiền, in bill"),
    ("Quản lý Kho & Lô", "Nhập hàng, hạn dùng FEFO"),
    ("Admin Dashboard", "Báo cáo doanh thu & hao hụt")
]
for i, (m_title, m_desc) in enumerate(fe_modules):
    my = 1110 - i * 140
    draw_box(390, my, 270, 100, '#FFFFFF', '#FECDD3', r=14, lw=1.2)
    ax.text(525, my + 65, m_title, fontsize=15, fontweight='bold', color='#9F1239', ha='center', va='center')
    ax.text(525, my + 30, m_desc, fontsize=12, color='#64748B', ha='center', va='center')

# ================= 4. BACKEND CONTAINER =================
outer_box = FancyBboxPatch((740, 260), 1750, 1300,
                           boxstyle="round,pad=0,rounding_size=30",
                           facecolor='#FFFFFF', edgecolor='#94A3B8',
                           linestyle='--', linewidth=2.5, zorder=1)
ax.add_patch(outer_box)
ax.text(1615, 1500, "Backend Services (Kiến trúc Hướng dịch vụ SOA bằng Python FastAPI)", 
        fontsize=24, fontweight='bold', color='#0F172A', ha='center', va='center')

services = [
    {
        "api_name": "AuthApi Service",
        "api_sub": "Quản lý xác thực & phân quyền",
        "api_bg": "#F0FDF4", "api_border": "#BBF7D0",
        "svc_name": "Auth Service",
        "svc_desc": "users, roles, permissions",
        "svc_port": "8001",
        "svc_bg": "#DCFCE7", "svc_border": "#86EFAC",
        "db_name": "fruitstore_auth_db",
        "db_user": "User: auth_user",
        "db_tables": "Bảng: users, roles, user_roles, refresh_tokens",
        "y": 1260
    },
    {
        "api_name": "CatalogApi Service",
        "api_sub": "Quản lý danh mục & trái cây",
        "api_bg": "#FEFCE8", "api_border": "#FEF08A",
        "svc_name": "Catalog Service",
        "svc_desc": "products, categories, prices",
        "svc_port": "8002",
        "svc_bg": "#FEF9C3", "svc_border": "#FDE047",
        "db_name": "fruitstore_catalog_db",
        "db_user": "User: catalog_user",
        "db_tables": "Bảng: categories, products, images, price_history",
        "y": 1020
    },
    {
        "api_name": "InventoryApi Service",
        "api_sub": "Quản lý tồn kho & lô FEFO",
        "api_bg": "#EFF6FF", "api_border": "#BFDBFE",
        "svc_name": "Inventory Service",
        "svc_desc": "stock_lots, reservations, movements",
        "svc_port": "8003",
        "svc_bg": "#DBEAFE", "svc_border": "#93C5FD",
        "db_name": "fruitstore_inventory_db",
        "db_user": "User: inventory_user",
        "db_tables": "Bảng: stock_lots, reservations, stock_movements, suppliers",
        "y": 780
    },
    {
        "api_name": "OrderApi Service",
        "api_sub": "Quản lý đơn hàng POS & Online",
        "api_bg": "#FAF5FF", "api_border": "#E9D5FF",
        "svc_name": "Order Service",
        "svc_desc": "orders, order_items, customers",
        "svc_port": "8004",
        "svc_bg": "#F3E8FF", "svc_border": "#D8B4FE",
        "db_name": "fruitstore_order_db",
        "db_user": "User: order_user",
        "db_tables": "Bảng: orders, order_items, customers, addresses",
        "y": 540
    },
    {
        "api_name": "PaymentApi Service",
        "api_sub": "Quản lý thanh toán & hoàn tiền",
        "api_bg": "#FFF7ED", "api_border": "#FED7AA",
        "svc_name": "Payment Service",
        "svc_desc": "payments, refunds, events",
        "svc_port": "8005",
        "svc_bg": "#FFEDD5", "svc_border": "#FDBA74",
        "db_name": "fruitstore_payment_db",
        "db_user": "User: payment_user",
        "db_tables": "Bảng: payments, refunds, payment_events",
        "y": 300
    }
]

for s in services:
    sy = s["y"]
    
    # 1. Left API Service Box
    draw_box(780, sy, 320, 160, s["api_bg"], s["api_border"], r=18, lw=1.6)
    ax.text(940, sy + 105, s["api_name"], fontsize=19, fontweight='bold', color='#0F172A', ha='center', va='center')
    ax.text(940, sy + 55, s["api_sub"], fontsize=13.5, color='#475569', ha='center', va='center', multialignment='center')

    # Arrow from API Box to FastAPI Service
    ax.annotate('', xy=(1350, sy + 80), xytext=(1100, sy + 80),
                arrowprops=dict(arrowstyle="-|>", color='#0284C7', lw=3, mutation_scale=20))
    
    # Floating tag above arrow
    draw_box(1125, sy + 105, 200, 48, '#FFFFFF', '#BAE6FD', r=10, lw=1.2)
    ax.text(1225, sy + 129, f"HTTP REST :{s['svc_port']}", fontsize=13, fontweight='bold', color='#0369A1', ha='center', va='center')

    # 2. Middle FastAPI Service Box
    draw_box(1350, sy, 360, 160, s["svc_bg"], s["svc_border"], r=18, lw=2)
    ax.text(1530, sy + 110, s["svc_name"], fontsize=20, fontweight='bold', color='#0F172A', ha='center', va='center')
    ax.text(1530, sy + 75, "FastAPI Service", fontsize=15, fontweight='bold', color='#059669', ha='center', va='center')
    ax.text(1530, sy + 40, f"Port: {s['svc_port']}  |  {s['svc_desc']}", fontsize=12, color='#475569', ha='center', va='center')

    # Arrow from FastAPI Service to Database
    ax.annotate('', xy=(2550, sy + 80), xytext=(1710, sy + 80),
                arrowprops=dict(arrowstyle="-|>", color='#334155', lw=3, mutation_scale=20))

    # 3. Right Database Box
    draw_box(2550, sy - 5, 580, 170, '#FFFFFF', '#0284C7', r=20, lw=2)
    
    draw_box(2575, sy + 100, 95, 45, '#0284C7', '#0369A1', r=10)
    ax.text(2622.5, sy + 122.5, "PG 16", fontsize=14, fontweight='bold', color='#FFFFFF', ha='center', va='center')
    
    ax.text(2690, sy + 122.5, "PostgreSQL Database", fontsize=17, fontweight='bold', color='#0F172A', ha='left', va='center')
    ax.text(2580, sy + 70, s["db_name"], fontsize=18, fontweight='bold', color='#0369A1', ha='left', va='center')
    ax.text(2580, sy + 38, s["db_user"], fontsize=14, fontweight='bold', color='#059669', ha='left', va='center')
    ax.text(2580, sy + 12, s["db_tables"], fontsize=12, color='#64748B', ha='left', va='center')

# ================= 5. INTER-SERVICE ARROWS & EXPLANATION =================
# Order Service coordinates with Catalog, Inventory and Payment
# 1. Order -> Catalog
ax.annotate('', xy=(1710, 1100), xytext=(1710, 680),
            arrowprops=dict(arrowstyle="->", color='#DC2626', lw=3.2,
                            connectionstyle="arc3,rad=-0.25", mutation_scale=20))
draw_box(1820, 870, 320, 60, '#FEF2F2', '#FECACA', r=12, lw=1.5)
ax.text(1980, 900, "Kiểm tra giá & SP Catalog", fontsize=14, fontweight='bold', color='#DC2626', ha='center', va='center')

# 2. Order -> Inventory
ax.annotate('', xy=(1710, 860), xytext=(1710, 650),
            arrowprops=dict(arrowstyle="->", color='#D97706', lw=3.2,
                            connectionstyle="arc3,rad=-0.22", mutation_scale=20))
draw_box(1820, 740, 360, 60, '#FFFBEB', '#FDE68A', r=12, lw=1.5)
ax.text(2000, 770, "Giữ tồn lô (FEFO) & Xuất kho", fontsize=14, fontweight='bold', color='#D97706', ha='center', va='center')

# 3. Order -> Payment
ax.annotate('', xy=(1710, 420), xytext=(1710, 580),
            arrowprops=dict(arrowstyle="->", color='#7C3AED', lw=3.2,
                            connectionstyle="arc3,rad=0.22", mutation_scale=20))
draw_box(1820, 480, 330, 60, '#FAF5FF', '#E9D5FF', r=12, lw=1.5)
ax.text(1985, 510, "Khởi tạo thanh toán đơn", fontsize=14, fontweight='bold', color='#7C3AED', ha='center', va='center')

# ================= 6. ARROWS FROM USER -> ANGULAR -> APIS =================
ax.annotate('', xy=(370, 1020), xytext=(310, 1020),
            arrowprops=dict(arrowstyle="-|>", color='#0F172A', lw=4, mutation_scale=24))

for s in services:
    sy = s["y"] + 80
    ax.annotate('', xy=(780, sy), xytext=(680, 1020),
                arrowprops=dict(arrowstyle="-|>", color='#475569', lw=2.5, mutation_scale=18))

# ================= 7. FOOTER: WORKFLOW STEPS =================
draw_box(50, 40, 3100, 175, '#FFFFFF', '#CBD5E1', r=24, lw=1.8)
ax.text(100, 172, "Luồng hoạt động chính trong kiến trúc SOA của FruitStore (Workflow):", fontsize=21, fontweight='bold', color='#0F172A', ha='left', va='center')

steps = [
    {
        "num": "1", "color": "#0284C7",
        "title": "Người dùng truy cập",
        "line1": "Khách hàng chọn trái cây trên Shop Online hoặc Thu ngân",
        "line2": "nhập kg bán hàng tại quầy POS trên Angular (localhost:4200)."
    },
    {
        "num": "2", "color": "#0284C7",
        "title": "Định tuyến Service SOA",
        "line1": "Angular gửi yêu cầu HTTP REST trực tiếp tới từng Service",
        "line2": "riêng biệt theo đúng ranh giới nghiệp vụ (:8001 -> :8005)."
    },
    {
        "num": "3", "color": "#D97706",
        "title": "Tích hợp Inter-Service (SOA)",
        "line1": "Order Service chủ động gọi Catalog (lấy giá), gọi Inventory",
        "line2": "(khóa lô hạn gần nhất theo FEFO) và gọi Payment Service."
    },
    {
        "num": "4", "color": "#16A34A",
        "title": "Database-per-Service (PostgreSQL)",
        "line1": "Mỗi service sở hữu một Database logic riêng với user độc lập,",
        "line2": "không khóa ngoại chéo (Zero Direct Foreign Key Cross-DB)."
    }
]

for i, st in enumerate(steps):
    bx = 90 + i * 760
    draw_box(bx, 60, 725, 90, '#F8FAFC', '#E2E8F0', r=14, lw=1.2)
    
    draw_box(bx + 18, 80, 50, 50, st["color"], st["color"], r=25)
    ax.text(bx + 43, 105, st["num"], fontsize=22, fontweight='bold', color='#FFFFFF', ha='center', va='center')

    ax.text(bx + 85, 122, st["title"], fontsize=15.5, fontweight='bold', color='#0F172A', ha='left', va='center')
    ax.text(bx + 85, 96, st["line1"], fontsize=11.5, color='#475569', ha='left', va='center')
    ax.text(bx + 85, 76, st["line2"], fontsize=11.5, color='#475569', ha='left', va='center')

plt.tight_layout()
plt.savefig('d:/fruit-store-management/kientruc_fruitstore_SOA.png', facecolor=fig.get_facecolor(), edgecolor='none', dpi=150)
print("Standard SOA Architecture Diagram generated successfully!")
