-- ============================================================
-- NovelBridge schema v1
-- API-first novel reading and authoring analysis agent
-- Source of truth copy. Keep deploy/remote/schema.sql in sync.
-- ============================================================

CREATE DATABASE IF NOT EXISTS novel_bridge
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE novel_bridge;

-- ============================================================
-- 1. Book source layer
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_book (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    author VARCHAR(200) DEFAULT NULL,
    language VARCHAR(20) NOT NULL DEFAULT 'zh',
    source_file_name VARCHAR(500) DEFAULT '',
    source_encoding VARCHAR(50) DEFAULT 'UTF-8',
    source_hash CHAR(64) NOT NULL,
    raw_text LONGTEXT NOT NULL,
    char_count INT NOT NULL DEFAULT 0,
    chapter_count INT NOT NULL DEFAULT 0,
    chunk_count INT NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'IMPORTED',
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_book_source_hash (source_hash),
    KEY idx_book_status (status),
    KEY idx_book_title (title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_chapter (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    chapter_number INT NOT NULL,
    title VARCHAR(500) NOT NULL DEFAULT '',
    raw_content LONGTEXT NOT NULL,
    start_offset INT NOT NULL DEFAULT 0,
    end_offset INT NOT NULL DEFAULT 0,
    char_count INT NOT NULL DEFAULT 0,
    split_strategy VARCHAR(100) NOT NULL DEFAULT '',
    split_confidence DOUBLE NOT NULL DEFAULT 1.0,
    status VARCHAR(30) NOT NULL DEFAULT 'CREATED',
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_chapter_book_number (book_id, chapter_number),
    KEY idx_chapter_book (book_id),
    CONSTRAINT fk_chapter_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_chunk (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    chapter_id BIGINT NOT NULL,
    chunk_index INT NOT NULL,
    content LONGTEXT NOT NULL,
    start_offset INT NOT NULL DEFAULT 0,
    end_offset INT NOT NULL DEFAULT 0,
    char_count INT NOT NULL DEFAULT 0,
    token_count INT NOT NULL DEFAULT 0,
    content_hash CHAR(64) NOT NULL,
    embedding_ref VARCHAR(200) DEFAULT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'CREATED',
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_chunk_chapter_index (chapter_id, chunk_index),
    KEY idx_chunk_book (book_id),
    KEY idx_chunk_chapter (chapter_id),
    KEY idx_chunk_hash (content_hash),
    CONSTRAINT fk_chunk_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE,
    CONSTRAINT fk_chunk_chapter FOREIGN KEY (chapter_id) REFERENCES novel_chapter(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 2. ChapterFact layer
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_chapter_fact (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    chapter_id BIGINT NOT NULL,
    model_call_id BIGINT DEFAULT NULL,
    fact_json JSON NOT NULL,
    evidence_json JSON NOT NULL,
    summary TEXT,
    parse_status VARCHAR(30) NOT NULL DEFAULT 'NOT_CHECKED',
    evidence_status VARCHAR(30) NOT NULL DEFAULT 'NOT_CHECKED',
    review_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    quality_flags_json JSON,
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_chapter_fact_chapter (chapter_id),
    KEY idx_chapter_fact_book (book_id),
    KEY idx_chapter_fact_review (review_status),
    CONSTRAINT fk_chapter_fact_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE,
    CONSTRAINT fk_chapter_fact_chapter FOREIGN KEY (chapter_id) REFERENCES novel_chapter(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 3. Agent runtime trace
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_agent_run (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,
    book_id BIGINT DEFAULT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    input_json JSON,
    output_json JSON,
    error_type VARCHAR(100) DEFAULT '',
    error_message TEXT,
    started_at DATETIME DEFAULT NULL,
    completed_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_agent_run_book (book_id),
    KEY idx_agent_run_status (status),
    KEY idx_agent_run_type (run_type),
    CONSTRAINT fk_agent_run_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_agent_step (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    agent_run_id BIGINT NOT NULL,
    step_type VARCHAR(80) NOT NULL,
    step_order INT NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    input_json JSON,
    output_json JSON,
    error_type VARCHAR(100) DEFAULT '',
    error_message TEXT,
    started_at DATETIME DEFAULT NULL,
    completed_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_agent_step_run (agent_run_id),
    KEY idx_agent_step_status (status),
    CONSTRAINT fk_agent_step_run FOREIGN KEY (agent_run_id) REFERENCES novel_agent_run(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_model_call (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    agent_run_id BIGINT DEFAULT NULL,
    agent_step_id BIGINT DEFAULT NULL,
    book_id BIGINT DEFAULT NULL,
    chapter_id BIGINT DEFAULT NULL,
    chunk_id BIGINT DEFAULT NULL,
    task_type VARCHAR(80) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(200) NOT NULL,
    prompt_name VARCHAR(100) NOT NULL DEFAULT '',
    prompt_revision VARCHAR(50) NOT NULL DEFAULT '',
    schema_revision VARCHAR(50) NOT NULL DEFAULT '',
    temperature DOUBLE DEFAULT NULL,
    max_tokens INT DEFAULT NULL,
    input_text LONGTEXT,
    output_text LONGTEXT,
    request_json JSON,
    response_json JSON,
    parse_status VARCHAR(30) NOT NULL DEFAULT 'NOT_CHECKED',
    evidence_status VARCHAR(30) NOT NULL DEFAULT 'NOT_CHECKED',
    retry_count INT NOT NULL DEFAULT 0,
    duration_ms BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    error_type VARCHAR(100) DEFAULT '',
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_model_call_run (agent_run_id),
    KEY idx_model_call_step (agent_step_id),
    KEY idx_model_call_book (book_id),
    KEY idx_model_call_chapter (chapter_id),
    KEY idx_model_call_chunk (chunk_id),
    KEY idx_model_call_task (task_type),
    KEY idx_model_call_status (status),
    CONSTRAINT fk_model_call_run FOREIGN KEY (agent_run_id) REFERENCES novel_agent_run(id) ON DELETE SET NULL,
    CONSTRAINT fk_model_call_step FOREIGN KEY (agent_step_id) REFERENCES novel_agent_step(id) ON DELETE SET NULL,
    CONSTRAINT fk_model_call_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE SET NULL,
    CONSTRAINT fk_model_call_chapter FOREIGN KEY (chapter_id) REFERENCES novel_chapter(id) ON DELETE SET NULL,
    CONSTRAINT fk_model_call_chunk FOREIGN KEY (chunk_id) REFERENCES novel_chunk(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_retrieval_trace (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id BIGINT DEFAULT NULL,
    query_text TEXT NOT NULL,
    book_id BIGINT DEFAULT NULL,
    items_json JSON,
    started_at DATETIME DEFAULT NULL,
    completed_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_retrieval_trace_run (run_id),
    KEY idx_retrieval_trace_book (book_id),
    CONSTRAINT fk_retrieval_trace_run FOREIGN KEY (run_id) REFERENCES novel_agent_run(id) ON DELETE SET NULL,
    CONSTRAINT fk_retrieval_trace_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 4. Reading QA
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_chat_session (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    title VARCHAR(500) DEFAULT '',
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_chat_session_book (book_id),
    KEY idx_chat_session_status (status),
    CONSTRAINT fk_chat_session_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_chat_message (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    book_id BIGINT NOT NULL,
    role VARCHAR(30) NOT NULL,
    content LONGTEXT NOT NULL,
    message_index INT NOT NULL DEFAULT 0,
    model_call_id BIGINT DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_chat_message_session (session_id),
    KEY idx_chat_message_book (book_id),
    CONSTRAINT fk_chat_message_session FOREIGN KEY (session_id) REFERENCES novel_chat_session(id) ON DELETE CASCADE,
    CONSTRAINT fk_chat_message_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE,
    CONSTRAINT fk_chat_message_model_call FOREIGN KEY (model_call_id) REFERENCES novel_model_call(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_citation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id BIGINT NOT NULL,
    book_id BIGINT NOT NULL,
    source_type VARCHAR(30) NOT NULL,
    source_id BIGINT NOT NULL,
    chapter_id BIGINT DEFAULT NULL,
    chunk_id BIGINT DEFAULT NULL,
    chapter_fact_id BIGINT DEFAULT NULL,
    excerpt TEXT NOT NULL,
    start_offset INT DEFAULT NULL,
    end_offset INT DEFAULT NULL,
    relevance_score DOUBLE DEFAULT NULL,
    evidence_level VARCHAR(30) NOT NULL DEFAULT 'NOT_CHECKED',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_citation_message (message_id),
    KEY idx_citation_book (book_id),
    KEY idx_citation_chapter (chapter_id),
    KEY idx_citation_chunk (chunk_id),
    CONSTRAINT fk_citation_message FOREIGN KEY (message_id) REFERENCES novel_chat_message(id) ON DELETE CASCADE,
    CONSTRAINT fk_citation_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE,
    CONSTRAINT fk_citation_chapter FOREIGN KEY (chapter_id) REFERENCES novel_chapter(id) ON DELETE SET NULL,
    CONSTRAINT fk_citation_chunk FOREIGN KEY (chunk_id) REFERENCES novel_chunk(id) ON DELETE SET NULL,
    CONSTRAINT fk_citation_chapter_fact FOREIGN KEY (chapter_fact_id) REFERENCES novel_chapter_fact(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
