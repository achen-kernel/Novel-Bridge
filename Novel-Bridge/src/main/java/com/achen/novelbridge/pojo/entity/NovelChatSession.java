package com.achen.novelbridge.pojo.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * Chat session for reading QA.
 *
 * @NB-DATA-WRITE
 */
@Data
public class NovelChatSession {

    private Long id;

    private Long bookId;

    private String title;

    private String status;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
