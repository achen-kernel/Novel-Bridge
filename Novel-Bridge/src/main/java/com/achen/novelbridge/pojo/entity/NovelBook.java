package com.achen.novelbridge.pojo.entity;

import com.achen.novelbridge.common.base.BaseEntity;
import com.achen.novelbridge.common.enums.BookStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "novel_book")
public class NovelBook extends BaseEntity {

    @Column(name = "project_id")
    private Long projectId;

    @Column(name = "folder_id")
    private Long folderId;

    @Column(nullable = false, length = 255)
    private String title;

    @Column(length = 100)
    private String author;

    @Column(name = "source_filename", nullable = false, length = 255)
    private String sourceFilename;

    @Column(name = "source_path", nullable = false, length = 500)
    private String sourcePath;

    @Column(name = "file_size")
    private Long fileSize;

    @Column(name = "file_type", length = 10)
    private String fileType;

    @Column(name = "total_chapters")
    private Integer totalChapters;

    @Column(name = "total_chunks")
    private Integer totalChunks;

    @Enumerated(EnumType.STRING)
    @Column(length = 20)
    private BookStatus status;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;
}
