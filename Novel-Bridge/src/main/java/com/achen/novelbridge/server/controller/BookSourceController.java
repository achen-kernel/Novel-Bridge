package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.result.Result;
import com.achen.novelbridge.pojo.entity.NovelBookSource;
import com.achen.novelbridge.pojo.vo.BookSourceUploadVO;
import com.achen.novelbridge.server.service.IBookSourceService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * Book source upload and remote trigger API.
 * <p>
 * Demo 5B: Java uploads whole TXT/book to remote MySQL via tunnel,
 * then triggers remote rag-agent POST /build?source_id=X.
 * rag-agent owns all downstream processing (chapter split, chunk, extraction).
 */
@RestController
@RequestMapping("/api/book-sources")
public class BookSourceController {

    private final IBookSourceService bookSourceService;

    public BookSourceController(IBookSourceService bookSourceService) {
        this.bookSourceService = bookSourceService;
    }

    /**
     * Upload a book TXT file and trigger remote build.
     * <p>
     * Flow:
     * 1. Save file content + metadata to novel_book_source + novel_book (remote MySQL via tunnel)
     * 2. Create AgentRun/AgentStep for tracking
     * 3. Call remote rag-agent POST /build?source_id={id}
     * <p>
     * If trigger fails, AgentStep is marked FAILED with error_message,
     * book_source.status = "TRIGGER_FAILED", user can retry later.
     */
    @PostMapping("/upload")
    public Result<BookSourceUploadVO> uploadAndTrigger(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "title", required = false) String title,
            @RequestParam(value = "author", required = false) String author,
            @RequestParam(value = "encoding", required = false) String encoding) {

        if (file.isEmpty()) {
            return Result.error("Uploaded file is empty");
        }

        NovelBookSource source = bookSourceService.uploadAndTrigger(file, title, author, encoding);

        BookSourceUploadVO vo = BookSourceUploadVO.builder()
                .bookSourceId(source.getId())
                .bookId(source.getBookId())
                .title(source.getTitle())
                .author(source.getAuthor())
                .sourceFilename(source.getSourceFilename())
                .fileType(source.getFileType())
                .fileSize(source.getFileSize())
                .contentHash(source.getContentHash())
                .encoding(source.getEncoding())
                .status(source.getStatus())
                .errorMessage(source.getErrorMessage())
                .createdAt(source.getCreatedAt())
                .build();

        if ("TRIGGER_FAILED".equals(source.getStatus())) {
            return Result.error("Upload succeeded but trigger failed: " + source.getErrorMessage());
        }
        return Result.success(vo);
    }
}
