package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Book chunk after chapter splitting.
 *
 * @NB-DATA-WRITE
 */
@Data
public class NovelChunk {

    private Long id;

    private Long bookId;

    private Long chapterId;

    private Integer chunkIndex;

    private String content;

    private Integer startOffset;

    private Integer endOffset;

    private Integer charCount;

    private Integer tokenCount;

    private String contentHash;

    private String embeddingRef;

    private String status;

    private String errorMessage;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
