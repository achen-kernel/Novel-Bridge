package com.achen.novelbridge.pojo.entity;

import com.achen.novelbridge.common.base.BaseEntity;
import lombok.Getter;
import lombok.Setter;

/**
 * Book source upload record.
 * <p>
 * This is the Java ↔ rag-agent contract table.
 * Java uploads and writes the full book text here.
 * Remote rag-agent reads from this table to build chapter/chunk/extraction artifacts.
 * <p>
 * content_hash (SHA-256) is used for dedup and integrity tracking.
 */
@Getter
@Setter
public class NovelBookSource extends BaseEntity {

    private Long bookId;
    private String title;
    private String author;
    private String sourceFilename;
    private String fileType;
    private Long fileSize;
    private String contentHash;
    private String rawText;
    private String encoding;
    private String status;
    private String errorMessage;
}
