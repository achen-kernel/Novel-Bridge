-- V9: KnowledgePatch tables — split evidence + review log from single JSON
-- Does not drop evidence_json column from novel_knowledge_patch (backward compat).

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

-- Add action/risk_override columns if table already exists (dev compat)
ALTER TABLE novel_patch_review ADD COLUMN IF NOT EXISTS action VARCHAR(30) NOT NULL DEFAULT 'REVIEW' AFTER patch_id;
ALTER TABLE novel_patch_review ADD COLUMN IF NOT EXISTS risk_override VARCHAR(20) DEFAULT NULL AFTER reviewed_by;
