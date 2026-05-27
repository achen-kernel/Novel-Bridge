package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Chapter fact extracted by the rag-agent pipeline.
 * <p>
 * Stores the structured fact and evidence for a single chapter,
 * along with parsing, evidence, and review status tracking.
 * </p>
 *
 * @NB-DATA-WRITE
 */
@Data
public class NovelChapterFact {

    private Long id;

    private Long bookId;

    private Long chapterId;

    private Long modelCallId;

    private String factJson;

    private String evidenceJson;

    private String summary;

    private String parseStatus;

    private String evidenceStatus;

    private String reviewStatus;

    private String qualityFlagsJson;

    private String status;

    private String errorMessage;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
