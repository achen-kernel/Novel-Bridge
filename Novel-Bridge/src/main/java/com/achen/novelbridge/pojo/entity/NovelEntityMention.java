package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Entity mention extracted from a chunk of text.
 * <p>
 * Stores each occurrence of a named entity within a chunk,
 * along with surrounding context, role, and merge governance flags.
 * </p>
 *
 * @NB-EVIDENCE
 */
@Data
public class NovelEntityMention {

    private Long id;

    private Long bookId;

    private Long chapterId;

    private Long chunkId;

    private String surfaceText;

    private String normalizedName;

    private String entityType;

    private String mentionRole;

    private Double confidence;

    private Boolean isGeneric;

    private Boolean doNotMergeGlobally;

    private String evidenceText;

    private String contextBefore;

    private String contextAfter;

    private String status;

    private LocalDateTime createdAt;
}
