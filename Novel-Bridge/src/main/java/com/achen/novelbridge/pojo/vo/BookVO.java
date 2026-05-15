package com.achen.novelbridge.pojo.vo;

import com.achen.novelbridge.common.enums.BookStatus;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class BookVO {

    private Long id;
    private String title;
    private String author;
    private String sourceFilename;
    private String fileType;
    private Long fileSize;
    private Integer totalChapters;
    private BookStatus status;
    private String errorMessage;
    private LocalDateTime createdAt;
    private List<ChapterVO> chapters;
}
