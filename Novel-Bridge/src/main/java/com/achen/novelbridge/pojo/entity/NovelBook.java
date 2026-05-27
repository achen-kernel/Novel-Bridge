package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Novel book source record.
 * <p>
 * Stores uploaded book raw text and processing state.
 * </p>
 *
 * @NB-DATA-WRITE
 */
@Data
public class NovelBook {

    private Long id;

    private String title;

    private String author;

    private String language;

    private String sourceFileName;

    private String sourceEncoding;

    private String sourceHash;

    private String rawText;

    private Integer charCount;

    private Integer chapterCount;

    private Integer chunkCount;

    private String status;

    private String errorMessage;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
