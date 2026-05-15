package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.exception.BaseException;
import com.achen.novelbridge.common.result.Result;
import com.achen.novelbridge.server.mapper.BookMapper;
import com.achen.novelbridge.server.mapper.ChapterMapper;
import com.achen.novelbridge.pojo.dto.CreateBookRequest;
import com.achen.novelbridge.pojo.entity.NovelAgentRun;
import com.achen.novelbridge.pojo.entity.NovelAgentStep;
import com.achen.novelbridge.pojo.entity.NovelBook;
import com.achen.novelbridge.pojo.entity.NovelChapter;
import com.achen.novelbridge.pojo.vo.AgentRunVO;
import com.achen.novelbridge.pojo.vo.AgentStepVO;
import com.achen.novelbridge.pojo.vo.BookVO;
import com.achen.novelbridge.pojo.vo.ChapterVO;
import com.achen.novelbridge.server.service.IBookService;
import com.achen.novelbridge.server.service.IAgentRunService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/books")
public class BookController {

    private final IBookService bookService;
    private final BookMapper bookMapper;
    private final ChapterMapper chapterMapper;
    private final IAgentRunService agentRunService;

    public BookController(IBookService bookService, BookMapper bookMapper,
                          ChapterMapper chapterMapper, IAgentRunService agentRunService) {
        this.bookService = bookService;
        this.bookMapper = bookMapper;
        this.chapterMapper = chapterMapper;
        this.agentRunService = agentRunService;
    }

    /**
     * Step 1: Create a Book record. The file is NOT split yet.
     * Status = IMPORTED.
     */
    @PostMapping
    public Result<BookVO> createBook(@Valid @RequestBody CreateBookRequest request) {
        NovelBook book = bookService.createBook(request.getFilePath());
        return Result.success(toVO(book));
    }

    /**
     * Step 2: Split the book file into chapters and save them.
     * Status: BUILDING -> READY_FOR_QA (or BUILD_FAILED).
     */
    @PostMapping("/{bookId}/build")
    public Result<BookVO> buildBook(@PathVariable Long bookId) {
        NovelBook book = bookService.buildBook(bookId);
        List<NovelChapter> chapters = chapterMapper.findByBookIdOrderByChapterNumber(bookId);
        return Result.success(toVO(book, chapters));
    }

    /**
     * View a book with its chapters.
     */
    @GetMapping("/{bookId}")
    public Result<BookVO> getBook(@PathVariable Long bookId) {
        NovelBook book = bookMapper.findById(bookId);
        if (book == null) {
            throw new BaseException("Book not found: " + bookId);
        }
        List<NovelChapter> chapters = chapterMapper.findByBookIdOrderByChapterNumber(bookId);
        return Result.success(toVO(book, chapters));
    }

    /**
     * List all books (for the frontend sidebar).
     */
    @GetMapping
    public Result<List<BookVO>> listBooks() {
        List<NovelBook> books = bookService.listBooks();
        List<BookVO> result = books.stream()
                .map(b -> BookVO.builder()
                        .id(b.getId())
                        .title(b.getTitle())
                        .status(b.getStatus())
                        .totalChapters(b.getTotalChapters())
                        .errorMessage(b.getErrorMessage())
                        .createdAt(b.getCreatedAt())
                        .build())
                .toList();
        return Result.success(result);
    }

    /**
     * Delete a book and all related data.
     */
    @DeleteMapping("/{bookId}")
    public Result<Void> deleteBook(@PathVariable Long bookId) {
        bookService.deleteBook(bookId);
        return Result.success();
    }

    /**
     * View all build runs for a book (with step details).
     */
    @GetMapping("/{bookId}/runs")
    public Result<List<AgentRunVO>> getRuns(@PathVariable Long bookId) {
        List<NovelAgentRun> runs = agentRunService.getRunsByBookId(bookId);
        List<AgentRunVO> result = runs.stream().map(this::toRunVO).toList();
        return Result.success(result);
    }

    // -- helper --

    private BookVO toVO(NovelBook book) {
        List<NovelChapter> chapters = chapterMapper.findByBookIdOrderByChapterNumber(book.getId());
        return toVO(book, chapters);
    }

    private BookVO toVO(NovelBook book, List<NovelChapter> chapters) {
        return BookVO.builder()
                .id(book.getId())
                .title(book.getTitle())
                .author(book.getAuthor())
                .sourceFilename(book.getSourceFilename())
                .fileType(book.getFileType())
                .fileSize(book.getFileSize())
                .totalChapters(book.getTotalChapters())
                .status(book.getStatus())
                .errorMessage(book.getErrorMessage())
                .createdAt(book.getCreatedAt())
                .chapters(chapters.stream().map(this::toChapterVO).toList())
                .build();
    }

    private ChapterVO toChapterVO(NovelChapter ch) {
        return ChapterVO.builder()
                .id(ch.getId())
                .chapterNumber(ch.getChapterNumber())
                .title(ch.getTitle())
                .charCount(ch.getCharCount())
                .build();
    }

    private AgentRunVO toRunVO(NovelAgentRun run) {
        List<NovelAgentStep> steps = agentRunService.getStepsByRunId(run.getId());
        return AgentRunVO.builder()
                .id(run.getId())
                .runType(run.getRunType())
                .bookId(run.getBookId())
                .status(run.getStatus())
                .startedAt(run.getStartedAt())
                .completedAt(run.getCompletedAt())
                .errorMessage(run.getErrorMessage())
                .steps(steps.stream().map(this::toStepVO).toList())
                .build();
    }

    private AgentStepVO toStepVO(NovelAgentStep step) {
        return AgentStepVO.builder()
                .id(step.getId())
                .stepType(step.getStepType())
                .stepOrder(step.getStepOrder())
                .status(step.getStatus())
                .startedAt(step.getStartedAt())
                .completedAt(step.getCompletedAt())
                .errorMessage(step.getErrorMessage())
                .build();
    }
}
