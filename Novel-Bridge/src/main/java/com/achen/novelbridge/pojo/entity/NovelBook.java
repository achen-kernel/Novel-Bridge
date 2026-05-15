package com.achen.novelbridge.pojo.entity;

import com.achen.novelbridge.common.base.BaseEntity;
import com.achen.novelbridge.common.enums.BookStatus;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class NovelBook extends BaseEntity {

    private Long projectId;
    private Long folderId;
    private String title;
    private String author;
    private String sourceFilename;
    private String sourcePath;
    private Long fileSize;
    private String fileType;
    private Integer totalChapters;
    private Integer totalChunks;
    private BookStatus status;
    private String errorMessage;
}
