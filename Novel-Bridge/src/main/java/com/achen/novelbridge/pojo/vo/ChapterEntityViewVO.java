package com.achen.novelbridge.pojo.vo;

import java.util.List;

/**
 * Chapter entity view VO — deduplicated entities visible in a single chapter.
 */
public class ChapterEntityViewVO {

    private Long chapterId;
    private List<ChapterEntityItem> entities;

    public Long getChapterId() {
        return chapterId;
    }

    public void setChapterId(Long chapterId) {
        this.chapterId = chapterId;
    }

    public List<ChapterEntityItem> getEntities() {
        return entities;
    }

    public void setEntities(List<ChapterEntityItem> entities) {
        this.entities = entities;
    }

    public static class ChapterEntityItem {
        private String displayName;
        private List<String> surfaceTexts;
        private String entityType;
        private Boolean isGeneric;
        private Boolean doNotMergeGlobally;
        private Integer mentionCount;

        public String getDisplayName() {
            return displayName;
        }

        public void setDisplayName(String displayName) {
            this.displayName = displayName;
        }

        public List<String> getSurfaceTexts() {
            return surfaceTexts;
        }

        public void setSurfaceTexts(List<String> surfaceTexts) {
            this.surfaceTexts = surfaceTexts;
        }

        public String getEntityType() {
            return entityType;
        }

        public void setEntityType(String entityType) {
            this.entityType = entityType;
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

        public Integer getMentionCount() {
            return mentionCount;
        }

        public void setMentionCount(Integer mentionCount) {
            this.mentionCount = mentionCount;
        }
    }
}
