package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Event mention extracted from a chunk of text.
 * <p>
 * Stores each observed event occurrence within a chunk,
 * with participants, location, time hint, and trigger.
 * </p>
 *
 * @NB-EVIDENCE
 */
@Data
public class NovelEventMention {

    private Long id;

    private Long bookId;

    private Long chapterId;

    private Long chunkId;

    private String eventType;

    private String summary;

    private String participantsJson;

    private String location;

    private String timeHint;

    private String eventTrigger;

    private String evidenceText;

    private String importance;

    private Double confidence;

    private String status;

    private LocalDateTime createdAt;
}
