package com.achen.novelbridge.pojo.vo;

import java.time.LocalDateTime;
import java.util.List;

/**
 * View object for alias decision query results.
 */
public class AliasDecisionVO {

    private Long id;
    private String entityAName;
    private String entityBName;
    private String decision;
    private Double confidence;
    private String reason;
    private List<String> riskTypes;
    private String reviewer;
    private LocalDateTime createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getEntityAName() {
        return entityAName;
    }

    public void setEntityAName(String entityAName) {
        this.entityAName = entityAName;
    }

    public String getEntityBName() {
        return entityBName;
    }

    public void setEntityBName(String entityBName) {
        this.entityBName = entityBName;
    }

    public String getDecision() {
        return decision;
    }

    public void setDecision(String decision) {
        this.decision = decision;
    }

    public Double getConfidence() {
        return confidence;
    }

    public void setConfidence(Double confidence) {
        this.confidence = confidence;
    }

    public String getReason() {
        return reason;
    }

    public void setReason(String reason) {
        this.reason = reason;
    }

    public List<String> getRiskTypes() {
        return riskTypes;
    }

    public void setRiskTypes(List<String> riskTypes) {
        this.riskTypes = riskTypes;
    }

    public String getReviewer() {
        return reviewer;
    }

    public void setReviewer(String reviewer) {
        this.reviewer = reviewer;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
