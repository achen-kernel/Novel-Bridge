-- ============================================================
-- V3: Entity Governance tables (Stage 5)
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
