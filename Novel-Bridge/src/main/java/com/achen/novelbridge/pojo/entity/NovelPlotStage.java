package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Plot stage for a book.
 * <p>
 * Defines a named narrative stage spanning a range of chapters,
 * with associated key entities and summary.
 * </p>
 */
@Data
public class NovelPlotStage {

    private Long id;

    private Long bookId;

    private Integer stageIndex;

    private String stageName;

    private String summary;

    private Long startChapterId;

    private Long endChapterId;

    private String keyEntitiesJson;

    private String status;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
