package com.achen.novelbridge.pojo.entity;

import com.achen.novelbridge.common.base.BaseEntity;
import com.achen.novelbridge.common.enums.ChapterStatus;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class NovelChapter extends BaseEntity {

    private Long bookId;
    private Integer chapterNumber;
    private String title;
    private String rawContent;
    private String cleanedContent;
    private Integer charCount;
    private ChapterStatus status;
    private String errorMessage;
}
