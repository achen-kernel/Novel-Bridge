package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Chat message within a QA session.
 *
 * @NB-DATA-WRITE
 */
@Data
public class NovelChatMessage {

    private Long id;

    private Long sessionId;

    private Long bookId;

    private String role;

    private String content;

    private Integer messageIndex;

    private Long modelCallId;

    private LocalDateTime createdAt;
}
