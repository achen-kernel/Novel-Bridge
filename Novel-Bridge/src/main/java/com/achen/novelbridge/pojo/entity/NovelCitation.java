package com.achen.novelbridge.pojo.entity;

import com.achen.novelbridge.common.base.BaseEntity;
import com.achen.novelbridge.common.enums.SourceType;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class NovelCitation extends BaseEntity {

    private Long messageId;
    private SourceType sourceType;
    private Long sourceId;
    private Long chapterId;
    private Long chunkId;
    private Long factId;
    private Double relevanceScore;
    private String excerpt;
}
