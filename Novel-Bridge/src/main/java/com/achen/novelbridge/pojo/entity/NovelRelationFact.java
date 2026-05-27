package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Consolidated relation fact for a book.
 * <p>
 * Aggregates relation mentions into a canonical fact with
 * source/target entity, polarity, strength, and evidence tracking
 * across chapters.
 * </p>
 *
 * @NB-DATA-WRITE
 */
@Data
public class NovelRelationFact {

    private Long id;

    private Long bookId;

    private String relationType;

    private String relationFamily;

    private Long sourceEntityId;

    private Long targetEntityId;

    private String sourceEntityName;

    private String targetEntityName;

    private String polarity;

    private Double confidence;

    private Double strength;

    private String evidenceIdsJson;

    private Long firstChapterId;

    private Long lastChapterId;

    private String status;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
