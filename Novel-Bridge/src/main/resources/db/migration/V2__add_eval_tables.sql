-- ============================================================
-- NovelBridge schema v2 — Stage 7: Java Eval Backend
-- ============================================================

CREATE TABLE IF NOT EXISTS novel_eval_case (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    question TEXT NOT NULL,
    expected_answer TEXT,
    expected_entities_json JSON,
    category VARCHAR(50) DEFAULT '',
    difficulty VARCHAR(20) DEFAULT 'MEDIUM',
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_eval_case_book (book_id),
    KEY idx_eval_case_category (category),
    KEY idx_eval_case_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_eval_run (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL DEFAULT 'FULL',
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
    KEY idx_eval_result_case (case_id),
    KEY idx_eval_result_status (status),
    CONSTRAINT fk_eval_result_run FOREIGN KEY (run_id) REFERENCES novel_eval_run(id) ON DELETE CASCADE,
    CONSTRAINT fk_eval_result_case FOREIGN KEY (case_id) REFERENCES novel_eval_case(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
