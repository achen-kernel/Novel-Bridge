package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Relation mention extracted from a chunk of text.
 * <p>
 * Stores each observed directional relation between two entities
 * within a chunk, with trigger, polarity, and confidence.
 * </p>
 *
 * @NB-EVIDENCE
 */
@Data
public class NovelRelationMention {

    private Long id;

    private Long bookId;

    private Long chapterId;

    private Long chunkId;

    private String sourceEntityName;

    private String targetEntityName;

    private String relationType;

    private String relationFamily;

    private String relationPolarity;

    private String direction;

    private String evidenceText;

    private String relationTrigger;

    private Double confidence;

    private String status;

    private LocalDateTime createdAt;
}
