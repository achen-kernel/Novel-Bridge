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
    prior_hint_json JSON DEFAULT NULL COMMENT 'DeepSeek prior hint strategy artifact',
    rules_json JSON DEFAULT NULL COMMENT 'Book-specific extraction rules',
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

CREATE TABLE IF NOT EXISTS novel_tool_call (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    agent_run_id BIGINT DEFAULT NULL,
    agent_step_id BIGINT DEFAULT NULL,
    tool_name VARCHAR(100) NOT NULL,
    input_json JSON,
    output_json JSON,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    started_at DATETIME DEFAULT NULL,
    finished_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_tool_call_run (agent_run_id),
    KEY idx_tool_call_step (agent_step_id),
    CONSTRAINT fk_tool_call_run FOREIGN KEY (agent_run_id) REFERENCES novel_agent_run(id) ON DELETE SET NULL,
    CONSTRAINT fk_tool_call_step FOREIGN KEY (agent_step_id) REFERENCES novel_agent_step(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 3b. KnowledgePatch
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_knowledge_patch (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    patch_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) DEFAULT NULL,
    target_id BIGINT DEFAULT NULL,
    payload_json JSON,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'medium',
    status VARCHAR(30) NOT NULL DEFAULT 'PROPOSED',
    created_by VARCHAR(100) NOT NULL DEFAULT 'reader_agent',
    run_id BIGINT DEFAULT NULL,
    review_note TEXT,
    reviewed_by VARCHAR(100) DEFAULT NULL,
    reviewed_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_kp_book (book_id),
    KEY idx_kp_status (status),
    KEY idx_kp_type (patch_type),
    KEY idx_kp_run (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_knowledge_patch_evidence (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patch_id BIGINT NOT NULL,
    source_type VARCHAR(30) NOT NULL,
    source_id BIGINT NOT NULL DEFAULT 0,
    chapter_id BIGINT DEFAULT NULL,
    excerpt TEXT,
    evidence_level VARCHAR(20) NOT NULL DEFAULT 'NEAR',
    relevance_score DOUBLE DEFAULT 0.0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_evidence_patch (patch_id),
    CONSTRAINT fk_evidence_patch FOREIGN KEY (patch_id) REFERENCES novel_knowledge_patch(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_patch_review (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patch_id BIGINT NOT NULL,
    action VARCHAR(30) NOT NULL DEFAULT 'REVIEW',
    previous_status VARCHAR(30) NOT NULL,
    new_status VARCHAR(30) NOT NULL,
    review_note TEXT,
    reviewed_by VARCHAR(100) NOT NULL DEFAULT 'human',
    risk_override VARCHAR(20) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_review_patch (patch_id),
    CONSTRAINT fk_review_patch FOREIGN KEY (patch_id) REFERENCES novel_knowledge_patch(id) ON DELETE CASCADE
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

-- ============================================================
-- 5. Entity Governance (Stage 5)
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_entity_mention (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    chapter_id BIGINT NOT NULL,
    chunk_id BIGINT DEFAULT NULL,
    surface_text VARCHAR(200) NOT NULL,
    normalized_name VARCHAR(200) DEFAULT '',
    entity_type VARCHAR(30) DEFAULT 'CHARACTER',
    mention_role VARCHAR(30) DEFAULT 'UNCERTAIN',
    confidence DOUBLE NOT NULL DEFAULT 0.0,
    is_generic TINYINT(1) NOT NULL DEFAULT 0,
    do_not_merge_globally TINYINT(1) NOT NULL DEFAULT 0,
    evidence_text TEXT,
    context_before VARCHAR(300) DEFAULT '',
    context_after VARCHAR(300) DEFAULT '',
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_entity_book (book_id),
    KEY idx_entity_chapter (chapter_id),
    KEY idx_entity_surface (surface_text(50)),
    CONSTRAINT fk_entity_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE,
    CONSTRAINT fk_entity_chapter FOREIGN KEY (chapter_id) REFERENCES novel_chapter(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_entity_profile (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    canonical_name VARCHAR(200) NOT NULL,
    entity_type VARCHAR(30) DEFAULT 'CHARACTER',
    description TEXT,
    aliases_json JSON,
    first_chapter_id BIGINT DEFAULT NULL,
    last_chapter_id BIGINT DEFAULT NULL,
    mention_count INT NOT NULL DEFAULT 0,
    source VARCHAR(50) DEFAULT 'EXTRACTED',
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_profile_book_name (book_id, canonical_name),
    KEY idx_profile_book (book_id),
    CONSTRAINT fk_profile_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_alias_decision (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    entity_a_name VARCHAR(200) NOT NULL,
    entity_b_name VARCHAR(200) NOT NULL,
    decision VARCHAR(30) NOT NULL,
    confidence DOUBLE NOT NULL DEFAULT 0.0,
    reason TEXT,
    risk_types_json JSON,
    reviewer VARCHAR(100) DEFAULT 'RULE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_alias_book (book_id),
    KEY idx_alias_decision (decision),
    CONSTRAINT fk_alias_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 6. Narrative Graph (Stage 6)
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_relation_mention (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    chapter_id BIGINT NOT NULL,
    chunk_id BIGINT DEFAULT NULL,
    source_entity_name VARCHAR(200) NOT NULL,
    target_entity_name VARCHAR(200) NOT NULL,
    relation_type VARCHAR(80) NOT NULL,
    relation_family VARCHAR(30) DEFAULT 'OTHER',
    relation_polarity VARCHAR(20) DEFAULT 'UNKNOWN',
    direction VARCHAR(20) DEFAULT 'UNKNOWN',
    evidence_text TEXT,
    relation_trigger VARCHAR(100) DEFAULT '',
    confidence DOUBLE NOT NULL DEFAULT 0.0,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_relation_book (book_id),
    KEY idx_relation_chapter (chapter_id),
    KEY idx_relation_type (relation_type),
    KEY idx_relation_source (source_entity_name(50)),
    KEY idx_relation_target (target_entity_name(50)),
    CONSTRAINT fk_relation_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE,
    CONSTRAINT fk_relation_chapter FOREIGN KEY (chapter_id) REFERENCES novel_chapter(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_relation_fact (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    relation_type VARCHAR(80) NOT NULL,
    relation_family VARCHAR(30) DEFAULT 'OTHER',
    source_entity_id BIGINT DEFAULT NULL,
    target_entity_id BIGINT DEFAULT NULL,
    source_entity_name VARCHAR(200) NOT NULL,
    target_entity_name VARCHAR(200) NOT NULL,
    polarity VARCHAR(20) DEFAULT 'NEUTRAL',
    confidence DOUBLE NOT NULL DEFAULT 0.0,
    strength INT NOT NULL DEFAULT 1,
    evidence_ids_json JSON,
    first_chapter_id BIGINT DEFAULT NULL,
    last_chapter_id BIGINT DEFAULT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_relation_pair (book_id, source_entity_name(50), target_entity_name(50), relation_type(30)),
    KEY idx_relation_fact_book (book_id),
    KEY idx_relation_fact_source (source_entity_name(50)),
    KEY idx_relation_fact_target (target_entity_name(50)),
    CONSTRAINT fk_relation_fact_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_event_mention (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    chapter_id BIGINT NOT NULL,
    chunk_id BIGINT DEFAULT NULL,
    event_type VARCHAR(50) NOT NULL,
    summary VARCHAR(500) DEFAULT '',
    participants_json JSON,
    location VARCHAR(200) DEFAULT '',
    time_hint VARCHAR(200) DEFAULT '',
    event_trigger VARCHAR(100) DEFAULT '',
    evidence_text TEXT,
    importance VARCHAR(20) DEFAULT 'MEDIUM',
    confidence DOUBLE NOT NULL DEFAULT 0.0,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_event_book (book_id),
    KEY idx_event_chapter (chapter_id),
    KEY idx_event_type (event_type),
    KEY idx_event_importance (importance),
    CONSTRAINT fk_event_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE,
    CONSTRAINT fk_event_chapter FOREIGN KEY (chapter_id) REFERENCES novel_chapter(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_event_fact (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    summary VARCHAR(500) DEFAULT '',
    participants_json JSON,
    location VARCHAR(200) DEFAULT '',
    importance VARCHAR(20) DEFAULT 'MEDIUM',
    evidence_ids_json JSON,
    first_chapter_id BIGINT DEFAULT NULL,
    last_chapter_id BIGINT DEFAULT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_event_fact_book (book_id),
    KEY idx_event_fact_type (event_type),
    CONSTRAINT fk_event_fact_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_plot_stage (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    stage_index INT NOT NULL,
    stage_name VARCHAR(200) NOT NULL,
    summary TEXT,
    start_chapter_id BIGINT DEFAULT NULL,
    end_chapter_id BIGINT DEFAULT NULL,
    key_entities_json JSON,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_plot_stage_book_index (book_id, stage_index),
    KEY idx_plot_stage_book (book_id),
    CONSTRAINT fk_plot_stage_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 7. Audit & Dataset (Stage 7)
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_eval_case (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    question TEXT NOT NULL,
    expected_answer TEXT,
    expected_entities_json JSON,
    category VARCHAR(50) DEFAULT 'QA',
    difficulty VARCHAR(20) DEFAULT 'MEDIUM',
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_eval_case_book (book_id),
    KEY idx_eval_case_category (category),
    CONSTRAINT fk_eval_case_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_eval_run (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    summary_json JSON,
    started_at DATETIME DEFAULT NULL,
    completed_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_eval_run_type (run_type),
    KEY idx_eval_run_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_eval_result (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id BIGINT NOT NULL,
    case_id BIGINT NOT NULL,
    question TEXT NOT NULL,
    actual_answer TEXT,
    citations_json JSON,
    scores_json JSON,
    error_type VARCHAR(100) DEFAULT '',
    error_message TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_eval_result_run (run_id),
    KEY idx_eval_result_status (status),
    CONSTRAINT fk_eval_result_run FOREIGN KEY (run_id) REFERENCES novel_eval_run(id) ON DELETE CASCADE,
    CONSTRAINT fk_eval_result_case FOREIGN KEY (case_id) REFERENCES novel_eval_case(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 8. Training Sample (Stage 2 — Data Flywheel)
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_training_sample (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    chapter_id BIGINT DEFAULT NULL COMMENT 'Source chapter',
    chunk_id BIGINT DEFAULT NULL COMMENT 'Source chunk',
    agent_run_id BIGINT DEFAULT NULL COMMENT 'Source pipeline run',
    sample_type VARCHAR(30) NOT NULL COMMENT 'CHUNK_EXTRACT | CHAPTER_FACT | QA_PAIR | ALIAS_REVIEW',
    input_data JSON NOT NULL COMMENT 'Prompt + context sent to model',
    model_output JSON NOT NULL COMMENT 'Raw model output',
    model_provider VARCHAR(50) DEFAULT '' COMMENT 'llama-server | deepseek',
    review_decision VARCHAR(30) DEFAULT 'PENDING' COMMENT 'PENDING | ACCEPT | REVISE | REJECT | MANUAL_REVIEW',
    review_score DOUBLE DEFAULT NULL COMMENT '0.0 - 1.0',
    review_comment TEXT COMMENT 'Review notes',
    revised_output JSON DEFAULT NULL COMMENT 'DeepSeek corrected output',
    error_types_json JSON DEFAULT NULL COMMENT '["HALLUCINATION", "OVER_MERGE", ...]',
    evidence_level VARCHAR(30) DEFAULT 'NOT_CHECKED' COMMENT 'EXACT | NORMALIZED | NEAR | UNSUPPORTED',
    sampling_reason VARCHAR(100) DEFAULT '' COMMENT 'Why this sample was collected',
    source VARCHAR(30) NOT NULL DEFAULT 'PIPELINE' COMMENT 'PIPELINE | MANUAL | API',
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_training_book (book_id),
    KEY idx_training_chapter (chapter_id),
    KEY idx_training_status (status),
    KEY idx_training_decision (review_decision),
    KEY idx_training_type (sample_type),
    CONSTRAINT fk_training_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE CASCADE,
    CONSTRAINT fk_training_chapter FOREIGN KEY (chapter_id) REFERENCES novel_chapter(id) ON DELETE SET NULL,
    CONSTRAINT fk_training_chunk FOREIGN KEY (chunk_id) REFERENCES novel_chunk(id) ON DELETE SET NULL,
    CONSTRAINT fk_training_run FOREIGN KEY (agent_run_id) REFERENCES novel_agent_run(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 9. Project / Session / Memory (persistent conversations)
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_project (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL DEFAULT '新项目',
    created_at DOUBLE NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_session (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL,
    name VARCHAR(200) NOT NULL DEFAULT '',
    created_at DOUBLE NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_session_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_session_memory (
    session_id BIGINT PRIMARY KEY,
    book_id INT DEFAULT NULL,
    turns_json JSON,
    preferences_json JSON,
    current_target_name VARCHAR(200) DEFAULT '',
    current_target_type VARCHAR(50) DEFAULT '',
    created_at DOUBLE NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
