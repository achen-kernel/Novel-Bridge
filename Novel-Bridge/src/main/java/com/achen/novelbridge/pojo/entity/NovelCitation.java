package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Citation linking a chat message to source evidence.
 *
 * @NB-DATA-WRITE
 * @NB-EVIDENCE
 */
@Data
public class NovelCitation {

    private Long id;

    private Long messageId;

    private Long bookId;

    private String sourceType;

    private Long sourceId;

    private Long chapterId;

    private Long chunkId;

    private Long chapterFactId;

    private String excerpt;

    private Integer startOffset;

    private Integer endOffset;

    private Double relevanceScore;

    private String evidenceLevel;

    private LocalDateTime createdAt;
}
