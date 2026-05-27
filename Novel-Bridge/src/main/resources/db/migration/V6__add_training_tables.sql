-- ============================================================
-- V6: Training Sample tables (Stage 2 — Data Flywheel)
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_training_sample (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    chapter_id BIGINT DEFAULT NULL COMMENT '来源章节',
    chunk_id BIGINT DEFAULT NULL COMMENT '来源 chunk',
    agent_run_id BIGINT DEFAULT NULL COMMENT '来源 pipeline run',
    sample_type VARCHAR(30) NOT NULL COMMENT 'CHUNK_EXTRACT | CHAPTER_FACT | QA_PAIR | ALIAS_REVIEW',
    input_data JSON NOT NULL COMMENT '送入模型的 prompt + context',
    model_output JSON NOT NULL COMMENT '模型的原始输出',
    model_provider VARCHAR(50) DEFAULT '' COMMENT 'llama-server | deepseek',
    review_decision VARCHAR(30) DEFAULT 'PENDING' COMMENT 'PENDING | ACCEPT | REVISE | REJECT | MANUAL_REVIEW',
    review_score DOUBLE DEFAULT NULL COMMENT '0.0 - 1.0',
    review_comment TEXT COMMENT '审核备注',
    revised_output JSON DEFAULT NULL COMMENT 'DeepSeek 修正后的输出',
    error_types_json JSON DEFAULT NULL COMMENT '["HALLUCINATION", "OVER_MERGE", ...]',
    evidence_level VARCHAR(30) DEFAULT 'NOT_CHECKED' COMMENT 'EXACT | NORMALIZED | NEAR | UNSUPPORTED',
    sampling_reason VARCHAR(100) DEFAULT '' COMMENT '触发采样的原因',
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
