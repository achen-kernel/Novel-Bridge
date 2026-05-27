package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Evaluation test case for QA retrieval quality assessment.
 * <p>
 * Defines a question, expected answer, and expected entities for
 * measuring retrieval and generation quality.
 * </p>
 *
 * @NB-DATA-WRITE
 * @NB-ROADMAP
 */
@Data
public class NovelEvalCase {

    private Long id;

    private Long bookId;

    private String question;

    private String expectedAnswer;

    private String expectedEntitiesJson;

    private String category;

    private String difficulty;

    private String status;

    private LocalDateTime createdAt;
}
