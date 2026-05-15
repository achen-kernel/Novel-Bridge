package com.achen.novelbridge.pojo.vo;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class CitationVO {

    private Long id;
    private String sourceType;
    private Long sourceId;
    private Long chapterId;
    private Double relevanceScore;
    private String excerpt;
}
