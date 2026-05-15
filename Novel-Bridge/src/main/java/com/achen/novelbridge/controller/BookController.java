package com.achen.novelbridge.controller;

import com.achen.novelbridge.pojo.dto.CreateBookRequest;
import com.achen.novelbridge.pojo.entity.NovelBook;
import com.achen.novelbridge.pojo.entity.NovelChapter;
import com.achen.novelbridge.pojo.vo.BookVO;
import com.achen.novelbridge.pojo.vo.ChapterVO;
import com.achen.novelbridge.server.repository.BookRepository;
import com.achen.novelbridge.server.repository.ChapterRepository;
import com.achen.novelbridge.server.service.BookService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
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

    private final BookService bookService;
    private final BookRepository bookRepository;
    private final ChapterRepository chapterRepository;

    public BookController(BookService bookService, BookRepository bookRepository,
                          ChapterRepository chapterRepository) {
        this.bookService = bookService;
        this.bookRepository = bookRepository;
        this.chapterRepository = chapterRepository;
    }

    /**
     * Step 1: Create a Book record. The file is NOT split yet.
     * Status = IMPORTED.
     */
    @PostMapping
    public ResponseEntity<BookVO> createBook(@Valid @RequestBody CreateBookRequest request) {
        NovelBook book = bookService.createBook(request.getFilePath());
        return ResponseEntity.ok(toVO(book));
    }

    /**
     * Step 2: Split the book file into chapters and save them.
     * Status: BUILDING -> READY_FOR_QA (or BUILD_FAILED).
     */
    @PostMapping("/{bookId}/build")
    public ResponseEntity<BookVO> buildBook(@PathVariable Long bookId) {
        NovelBook book = bookService.buildBook(bookId);
        List<NovelChapter> chapters = chapterRepository.findByBookIdOrderByChapterNumber(bookId);
        return ResponseEntity.ok(toVO(book, chapters));
    }

    /**
     * View a book with its chapters.
     */
    @GetMapping("/{bookId}")
    public ResponseEntity<BookVO> getBook(@PathVariable Long bookId) {
        NovelBook book = bookRepository.findById(bookId)
                .orElseThrow(() -> new IllegalArgumentException("Book not found: " + bookId));
        List<NovelChapter> chapters = chapterRepository.findByBookIdOrderByChapterNumber(bookId);
        return ResponseEntity.ok(toVO(book, chapters));
    }

    // -- helper --

    private BookVO toVO(NovelBook book) {
        List<NovelChapter> chapters = chapterRepository.findByBookIdOrderByChapterNumber(book.getId());
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
}
