-- ============================================================
-- V4: Narrative Graph tables (Stage 6)
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
