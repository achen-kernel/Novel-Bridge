package com.achen.novelbridge.pojo.vo;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class ChapterVO {

    private Long id;
    private Integer chapterNumber;
    private String title;
    private Integer charCount;
}
