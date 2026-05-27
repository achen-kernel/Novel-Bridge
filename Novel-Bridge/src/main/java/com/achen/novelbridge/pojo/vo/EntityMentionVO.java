package com.achen.novelbridge.pojo.vo;

import java.time.LocalDateTime;

/**
 * View object for entity mention query results.
 */
public class EntityMentionVO {

    private Long id;
    private Long chapterId;
    private Long chunkId;
    private String surfaceText;
    private String normalizedName;
    private String entityType;
    private String mentionRole;
    private Double confidence;
    private Boolean isGeneric;
    private Boolean doNotMergeGlobally;
    private String evidenceText;
    private String status;
    private LocalDateTime createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getChapterId() {
        return chapterId;
    }

    public void setChapterId(Long chapterId) {
        this.chapterId = chapterId;
    }

    public Long getChunkId() {
        return chunkId;
    }

    public void setChunkId(Long chunkId) {
        this.chunkId = chunkId;
    }

    public String getSurfaceText() {
        return surfaceText;
    }

    public void setSurfaceText(String surfaceText) {
        this.surfaceText = surfaceText;
    }

    public String getNormalizedName() {
        return normalizedName;
    }

    public void setNormalizedName(String normalizedName) {
        this.normalizedName = normalizedName;
    }

    public String getEntityType() {
        return entityType;
    }

    public void setEntityType(String entityType) {
        this.entityType = entityType;
    }

    public String getMentionRole() {
        return mentionRole;
    }

    public void setMentionRole(String mentionRole) {
        this.mentionRole = mentionRole;
    }

    public Double getConfidence() {
        return confidence;
    }

    public void setConfidence(Double confidence) {
        this.confidence = confidence;
    }

    public Boolean getIsGeneric() {
        return isGeneric;
    }

    public void setIsGeneric(Boolean isGeneric) {
        this.isGeneric = isGeneric;
    }

    public Boolean getDoNotMergeGlobally() {
        return doNotMergeGlobally;
    }

    public void setDoNotMergeGlobally(Boolean doNotMergeGlobally) {
        this.doNotMergeGlobally = doNotMergeGlobally;
    }

    public String getEvidenceText() {
        return evidenceText;
    }

    public void setEvidenceText(String evidenceText) {
        this.evidenceText = evidenceText;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
