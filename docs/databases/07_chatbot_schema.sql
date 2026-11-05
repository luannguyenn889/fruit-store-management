-- =============================================================================
-- DATABASE SCHEMA: AI Chatbot Service (fruitstore_chatbot_db - Mở rộng)
-- Description: Lưu trữ phiên hội thoại tư vấn, tin nhắn, nhật ký gọi Function Calling và phản hồi
-- Engine: PostgreSQL 16+
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Bảng Phiên hội thoại (Conversations)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID, -- Tham chiếu logic tới Auth Service nếu khách đã đăng nhập
    session_id VARCHAR(100) NOT NULL,
    user_role VARCHAR(20) NOT NULL DEFAULT 'CUSTOMER',
    title VARCHAR(200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Bảng Tin nhắn (Messages)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_role VARCHAR(20) NOT NULL
        CHECK (sender_role IN ('user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    prompt_tokens INT,
    completion_tokens INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Bảng Nhật ký thực thi Function Calling (Tool Execution Logs)
CREATE TABLE IF NOT EXISTS tool_execution_logs (
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

-- 4. Bảng Đánh giá phản hồi của người dùng (Chat Feedback)
CREATE TABLE IF NOT EXISTS chat_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL UNIQUE REFERENCES messages(id) ON DELETE CASCADE,
    rating SMALLINT CHECK (rating IN (1, -1)), -- 1: Hữu ích, -1: Chưa hài lòng
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes tối ưu truy vấn lịch sử chat
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at ASC);

