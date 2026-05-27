package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Consolidated entity profile for a book.
 * <p>
 * Aggregates mentions into a single canonical entity record with
 * aliases, description, and lifecycle tracking across chapters.
 * </p>
 *
 * @NB-DATA-WRITE
 */
@Data
public class NovelEntityProfile {

    private Long id;

    private Long bookId;

    private String canonicalName;

    private String entityType;

    private String description;

    private String aliasesJson;

    private Long firstChapterId;

    private Long lastChapterId;

    private Integer mentionCount;

    private String source;

    private String status;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
