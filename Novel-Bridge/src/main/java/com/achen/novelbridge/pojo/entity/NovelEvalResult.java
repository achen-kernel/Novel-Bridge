package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Individual evaluation result for a single case within a run.
 * <p>
 * Stores the actual answer produced, the citations retrieved,
 * scores per metric, and any error information.
 * </p>
 *
 * @NB-DATA-WRITE
 * @NB-ROADMAP
 */
@Data
public class NovelEvalResult {

    private Long id;

    private Long runId;

    private Long caseId;

    private String question;

    private String actualAnswer;

    private String citationsJson;

    private String scoresJson;

    private String errorType;

    private String errorMessage;

    private String status;

    private LocalDateTime createdAt;
}
