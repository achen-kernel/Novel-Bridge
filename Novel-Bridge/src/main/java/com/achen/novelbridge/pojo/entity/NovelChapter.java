package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Book chapter after splitting.
 *
 * @NB-DATA-WRITE
 */
@Data
public class NovelChapter {

    private Long id;

    private Long bookId;

    private Integer chapterNumber;

    private String title;

    private String rawContent;

    private Integer startOffset;

    private Integer endOffset;

    private Integer charCount;

    private String splitStrategy;

    private Double splitConfidence;

    private String status;

    private String errorMessage;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
