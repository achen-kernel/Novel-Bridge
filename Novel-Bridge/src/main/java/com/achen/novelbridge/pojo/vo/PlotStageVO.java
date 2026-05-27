package com.achen.novelbridge.pojo.vo;

import java.util.List;

/**
 * View object for plot stage query results.
 */
public class PlotStageVO {

    private Long id;
    private Integer stageIndex;
    private String stageName;
    private String summary;
    private Integer startChapterId;
    private Integer endChapterId;
    private List<String> keyEntities;
    private String status;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Integer getStageIndex() {
        return stageIndex;
    }

    public void setStageIndex(Integer stageIndex) {
        this.stageIndex = stageIndex;
    }

    public String getStageName() {
        return stageName;
    }

    public void setStageName(String stageName) {
        this.stageName = stageName;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public Integer getStartChapterId() {
        return startChapterId;
    }

    public void setStartChapterId(Integer startChapterId) {
        this.startChapterId = startChapterId;
    }

    public Integer getEndChapterId() {
        return endChapterId;
    }

    public void setEndChapterId(Integer endChapterId) {
        this.endChapterId = endChapterId;
    }

    public List<String> getKeyEntities() {
        return keyEntities;
    }

    public void setKeyEntities(List<String> keyEntities) {
        this.keyEntities = keyEntities;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
