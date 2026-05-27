package com.achen.novelbridge.pojo.vo;

import java.time.LocalDateTime;

/**
 * Chapter fact view object returned in fact query endpoints.
 * <p>
 * factJson and evidenceJson are returned as parsed JSON objects
 * rather than raw strings.
 * </p>
 */
public class ChapterFactVO {

    private Long id;
    private Long bookId;
    private Long chapterId;
    private Object factJson;
    private Object evidenceJson;
    private String summary;
    private String parseStatus;
    private String evidenceStatus;
    private String reviewStatus;
    private String status;
    private String errorMessage;
    private LocalDateTime createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getBookId() {
        return bookId;
    }

    public void setBookId(Long bookId) {
        this.bookId = bookId;
    }

    public Long getChapterId() {
        return chapterId;
    }

    public void setChapterId(Long chapterId) {
        this.chapterId = chapterId;
    }

    public Object getFactJson() {
        return factJson;
    }

    public void setFactJson(Object factJson) {
        this.factJson = factJson;
    }

    public Object getEvidenceJson() {
        return evidenceJson;
    }

    public void setEvidenceJson(Object evidenceJson) {
        this.evidenceJson = evidenceJson;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public String getParseStatus() {
        return parseStatus;
    }

    public void setParseStatus(String parseStatus) {
        this.parseStatus = parseStatus;
    }

    public String getEvidenceStatus() {
        return evidenceStatus;
    }

    public void setEvidenceStatus(String evidenceStatus) {
        this.evidenceStatus = evidenceStatus;
    }

    public String getReviewStatus() {
        return reviewStatus;
    }

    public void setReviewStatus(String reviewStatus) {
        this.reviewStatus = reviewStatus;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
