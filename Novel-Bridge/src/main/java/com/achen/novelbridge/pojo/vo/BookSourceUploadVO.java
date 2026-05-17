package com.achen.novelbridge.pojo.vo;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * Response VO for book source upload + trigger endpoint.
 */
@Data
@Builder
public class BookSourceUploadVO {

    private Long bookSourceId;
    private Long bookId;
    private String title;
    private String author;
    private String sourceFilename;
    private String fileType;
    private Long fileSize;
    private String contentHash;
    private String encoding;
    private String status;
    private String errorMessage;
    private LocalDateTime createdAt;
}
