package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Agent runtime trace — tracks a single run (e.g. BOOK_BUILD, CHAPTER_EXTRACT).
 *
 * @NB-AGENT-STEP
 */
@Data
public class NovelAgentRun {

    private Long id;

    private String runType;

    private Long bookId;

    private String status;

    private String inputJson;

    private String outputJson;

    private String errorType;

    private String errorMessage;

    private LocalDateTime startedAt;

    private LocalDateTime completedAt;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
