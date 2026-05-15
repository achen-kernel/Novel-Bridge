package com.achen.novelbridge.pojo.entity;

import com.achen.novelbridge.common.base.BaseEntity;
import com.achen.novelbridge.common.enums.ChapterStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "novel_chapter",
       uniqueConstraints = @UniqueConstraint(columnNames = {"book_id", "chapter_number"}),
       indexes = @Index(columnList = "book_id"))
public class NovelChapter extends BaseEntity {

    @Column(name = "book_id", nullable = false)
    private Long bookId;

    @Column(name = "chapter_number", nullable = false)
    private Integer chapterNumber;

    @Column(length = 500)
    private String title;

    @Column(name = "raw_content", columnDefinition = "LONGTEXT")
    private String rawContent;

    @Column(name = "cleaned_content", columnDefinition = "LONGTEXT")
    private String cleanedContent;

    @Column(name = "char_count")
    private Integer charCount;

    @Enumerated(EnumType.STRING)
    @Column(length = 20)
    private ChapterStatus status;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;
}
