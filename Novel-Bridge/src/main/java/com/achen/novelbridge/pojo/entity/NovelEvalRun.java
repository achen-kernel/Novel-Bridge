package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Evaluation run tracking a batch execution of eval cases.
 * <p>
 * Each run groups results from evaluating one or more test cases
 * against the current retrieval and generation pipeline.
 * </p>
 *
 * @NB-DATA-WRITE
 * @NB-ROADMAP
 */
@Data
public class NovelEvalRun {

    private Long id;

    private String runType;

    private String status;

    private String summaryJson;

    private LocalDateTime startedAt;

    private LocalDateTime completedAt;

    private LocalDateTime createdAt;
}
