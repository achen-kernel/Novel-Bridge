-- ============================================================
-- V5: Add prior_hint_json and rules_json to novel_book
-- ============================================================

ALTER TABLE novel_book
    ADD COLUMN prior_hint_json JSON DEFAULT NULL COMMENT 'DeepSeek prior hint (梗概) strategy artifact' AFTER error_message,
    ADD COLUMN rules_json JSON DEFAULT NULL COMMENT 'Book-specific extraction rules (generated from prior_hint + manual edits)' AFTER prior_hint_json,
    ADD INDEX idx_book_prior_hint ((CAST(prior_hint_json AS CHAR(1)))) COMMENT 'Index hint for queries checking prior_hint existence';
