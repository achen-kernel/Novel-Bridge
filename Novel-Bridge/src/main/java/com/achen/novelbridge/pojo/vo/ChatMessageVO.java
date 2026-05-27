package com.achen.novelbridge.pojo.vo;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Chat message view object with optional citations.
 */
public class ChatMessageVO {

    private Long id;
    private Long sessionId;
    private String role;
    private String content;
    private Integer messageIndex;
    private List<CitationVO> citations;
    private LocalDateTime createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getSessionId() {
        return sessionId;
    }

    public void setSessionId(Long sessionId) {
        this.sessionId = sessionId;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public Integer getMessageIndex() {
        return messageIndex;
    }

    public void setMessageIndex(Integer messageIndex) {
        this.messageIndex = messageIndex;
    }

    public List<CitationVO> getCitations() {
        return citations;
    }

    public void setCitations(List<CitationVO> citations) {
        this.citations = citations;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
