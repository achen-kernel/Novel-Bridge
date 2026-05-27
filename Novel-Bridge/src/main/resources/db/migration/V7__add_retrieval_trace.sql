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
