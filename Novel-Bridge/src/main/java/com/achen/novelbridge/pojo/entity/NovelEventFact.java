package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Consolidated event fact for a book.
 * <p>
 * Aggregates event mentions into a canonical fact with
 * participants, location, importance, and evidence tracking
 * across chapters.
 * </p>
 *
 * @NB-DATA-WRITE
 */
@Data
public class NovelEventFact {

    private Long id;

    private Long bookId;

    private String eventType;

    private String summary;

    private String participantsJson;

    private String location;

    private String importance;

    private String evidenceIdsJson;

    private Long firstChapterId;

    private Long lastChapterId;

    private String status;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
