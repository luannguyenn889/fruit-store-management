# 07. Cơ Sở Dữ Liệu Dịch Vụ Trợ Lý AI — Chatbot DB (`fruitstore_chatbot_db`)

## 1. Thông tin chung
- **Dịch vụ sở hữu:** `chatbot-service` (Giai đoạn mở rộng — Sprint 5)
- **Tên Database:** `fruitstore_chatbot_db`
- **DB User:** `chatbot_user`
- **Chuỗi kết nối (FastAPI SQLAlchemy Async):**
  ```env
  DATABASE_URL=postgresql+psycopg://chatbot_user:chatbot_pass@postgres:5432/fruitstore_chatbot_db
  ```
- **Trách nhiệm dữ liệu:**
  - Lưu trữ các phiên trò chuyện (`conversations`) của khách hàng hoặc quản lý cửa hàng.
  - Lưu nội dung tin nhắn (`messages`) giữa người dùng và AI.
  - Lưu nhật ký thực thi công cụ (`tool_execution_logs`) khi AI gọi các REST API của `catalog-service`, `inventory-service`, `order-service`, `reporting-service`.
  - Lưu đánh giá chất lượng câu trả lời (`chat_feedback`).

---

## 2. Sơ đồ quan hệ thực thể (ERD)

```mermaid
erDiagram
    conversations ||--o{ messages : "chứa tin nhắn"
    messages ||--o{ tool_execution_logs : "kích hoạt tool"
    messages ||--o| chat_feedback : "nhận đánh giá"

    conversations {
        UUID id PK
        UUID user_id "Logic ref -> Auth DB (NULL nếu khách vãng lai)"
        VARCHAR(100) session_id
        VARCHAR(20) user_role "CUSTOMER | MANAGER | ADMIN"
        VARCHAR(200) title
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    messages {
        UUID id PK
        UUID conversation_id FK
        VARCHAR(20) sender_role "user | assistant | tool"
        TEXT content
        INT prompt_tokens
        INT completion_tokens
        TIMESTAMPTZ created_at
    }
    tool_execution_logs {
        UUID id PK
        UUID message_id FK
        VARCHAR(100) tool_name "search_products | check_stock | get_order_status..."
        VARCHAR(50) target_service "catalog | inventory | order | reporting"
        JSONB arguments
        JSONB response_summary
        INT duration_ms
        VARCHAR(20) status "SUCCESS | ERROR"
        TIMESTAMPTZ created_at
    }
    chat_feedback {
        UUID id PK
        UUID message_id UK, FK
        SMALLINT rating "1 (Hữu ích) | -1 (Chưa tốt)"
        TEXT comment
        TIMESTAMPTZ created_at
    }
```

---

## 3. Mã lệnh DDL chuẩn PostgreSQL 16

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    session_id VARCHAR(100) NOT NULL,
    user_role VARCHAR(20) NOT NULL DEFAULT 'CUSTOMER',
    title VARCHAR(200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_role VARCHAR(20) NOT NULL
        CHECK (sender_role IN ('user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    prompt_tokens INT,
    completion_tokens INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tool_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    target_service VARCHAR(50) NOT NULL,
    arguments JSONB,
    response_summary JSONB,
    duration_ms INT,
    status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS'
        CHECK (status IN ('SUCCESS', 'ERROR')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE chat_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL UNIQUE REFERENCES messages(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON conversations(user_id, updated_at DESC);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at ASC);
```

