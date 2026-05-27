package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Alias merge or block decision between two entity names.
 * <p>
 * Records the decision (MERGE, BLOCK, UNCERTAIN, MANUAL_REVIEW)
 * along with confidence, reasoning, and risk types for auditability.
 * </p>
 */
@Data
public class NovelAliasDecision {

    private Long id;

    private Long bookId;

    private String entityAName;

    private String entityBName;

    private String decision;

    private Double confidence;

    private String reason;

    private String riskTypesJson;

    private String reviewer;

    private LocalDateTime createdAt;
}
