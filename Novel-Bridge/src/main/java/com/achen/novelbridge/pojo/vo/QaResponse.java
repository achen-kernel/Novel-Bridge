package com.achen.novelbridge.pojo.vo;

import java.util.List;

/**
 * QA response payload.
 */
public class QaResponse {

    private Long messageId;
    private String role;
    private String content;
    private List<CitationVO> citations;

    public Long getMessageId() {
        return messageId;
    }

    public void setMessageId(Long messageId) {
        this.messageId = messageId;
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

    public List<CitationVO> getCitations() {
        return citations;
    }

    public void setCitations(List<CitationVO> citations) {
        this.citations = citations;
    }
}
