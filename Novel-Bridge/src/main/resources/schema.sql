-- NovelBridge database schema (MyBatis)
-- 7 tables for Demo 1-3
-- Created by Spring SQL init on startup

CREATE TABLE IF NOT EXISTS novel_book (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT,
    folder_id BIGINT,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(100),
    source_filename VARCHAR(255) NOT NULL,
    source_path VARCHAR(500) NOT NULL,
    file_size BIGINT,
    file_type VARCHAR(10),
    total_chapters INT,
    total_chunks INT,
    status VARCHAR(20),
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS novel_chapter (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    chapter_number INT NOT NULL,
    title VARCHAR(500),
    raw_content LONGTEXT,
    cleaned_content LONGTEXT,
    char_count INT,
    status VARCHAR(20),
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    UNIQUE KEY uk_book_chapter (book_id, chapter_number),
    INDEX idx_chapter_book (book_id)
);

CREATE TABLE IF NOT EXISTS novel_chunk (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    chapter_id BIGINT NOT NULL,
    book_id BIGINT NOT NULL,
    chunk_index INT NOT NULL,
    content LONGTEXT NOT NULL,
    char_count INT,
    embedding_id VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    INDEX idx_chunk_chapter (chapter_id),
    INDEX idx_chunk_book (book_id)
);

CREATE TABLE IF NOT EXISTS novel_chapter_fact (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    chapter_id BIGINT NOT NULL,
    book_id BIGINT NOT NULL,
    fact_type VARCHAR(50),
    fact_content TEXT NOT NULL,
    fact_json JSON,
    model_run_id BIGINT,
    evidence_text TEXT,
    raw_output_ref VARCHAR(500),
    confidence DOUBLE DEFAULT 1.0,
    status VARCHAR(20) DEFAULT 'AUTO_EXTRACTED',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    INDEX idx_fact_chapter (chapter_id),
    INDEX idx_fact_book (book_id)
);

CREATE TABLE IF NOT EXISTS novel_agent_run (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,
    book_id BIGINT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    started_at DATETIME,
    completed_at DATETIME,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    INDEX idx_run_book (book_id)
);

CREATE TABLE IF NOT EXISTS novel_agent_step (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    agent_run_id BIGINT NOT NULL,
    step_type VARCHAR(50) NOT NULL,
    step_order INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'WAITING',
    started_at DATETIME,
    completed_at DATETIME,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    INDEX idx_step_run (agent_run_id)
);

CREATE TABLE IF NOT EXISTS novel_entity_profile (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    entity_name VARCHAR(200) NOT NULL,
    entity_type VARCHAR(50),
    aliases TEXT,
    description TEXT,
    significance VARCHAR(20) DEFAULT 'MINOR',
    first_chapter_id BIGINT,
    last_chapter_id BIGINT,
    source_fact_ids_json JSON,
    status VARCHAR(20) DEFAULT 'AUTO_EXTRACTED',
    error_message TEXT,
    profile_json JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    INDEX idx_profile_book (book_id)
);

CREATE TABLE IF NOT EXISTS novel_chat_session (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    user_id BIGINT,
    title VARCHAR(255),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    INDEX idx_session_book (book_id)
);

CREATE TABLE IF NOT EXISTS novel_chat_message (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    role VARCHAR(20) NOT NULL,
    content LONGTEXT NOT NULL,
    message_index INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    INDEX idx_message_session (session_id)
);

CREATE TABLE IF NOT EXISTS novel_citation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id BIGINT NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    source_id BIGINT NOT NULL,
    chapter_id BIGINT,
    chunk_id BIGINT,
    fact_id BIGINT,
    relevance_score DOUBLE,
    excerpt TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    INDEX idx_citation_message (message_id)
);
