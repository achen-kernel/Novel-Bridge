package com.achen.novelbridge.server.service;

import com.achen.novelbridge.common.enums.BookStatus;
import com.achen.novelbridge.common.enums.ChapterStatus;
import com.achen.novelbridge.pojo.entity.NovelBook;
import com.achen.novelbridge.pojo.entity.NovelChapter;
import com.achen.novelbridge.server.repository.BookRepository;
import com.achen.novelbridge.server.repository.ChapterRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

/**
 * Handles book import and chapter splitting.
 * <p>
 * MOCK/DEBT: Uses simple regex splitting. Default user/project (no auth yet).
 * File encoding is hardcoded to GB18030 for Chinese txt files.
 */
@Slf4j
@Service
public class BookService {

    private final BookRepository bookRepository;
    private final ChapterRepository chapterRepository;
    private final Path booksBaseDir;

    public BookService(BookRepository bookRepository,
                       ChapterRepository chapterRepository,
                       @Value("${novel-bridge.books.base-dir}") String baseDir) {
        this.bookRepository = bookRepository;
        this.chapterRepository = chapterRepository;
        this.booksBaseDir = Paths.get(baseDir).toAbsolutePath().normalize();
    }

    /**
     * Step 1: Create a Book record from a file path (relative to base-dir).
     * Status = IMPORTED.
     */
    @Transactional
    public NovelBook createBook(String relativePath) {
        Path filePath = booksBaseDir.resolve(relativePath).normalize();

        if (!Files.isRegularFile(filePath)) {
            throw new IllegalArgumentException("File not found: " + filePath);
        }

        String filename = filePath.getFileName().toString();
        String title = filename;
        String ext = "";

        int dot = filename.lastIndexOf('.');
        if (dot > 0) {
            title = filename.substring(0, dot);
            ext = filename.substring(dot + 1).toLowerCase();
        }

        NovelBook book = new NovelBook();
        book.setTitle(title);
        book.setAuthor("吴承恩"); // MOCK: hardcoded for demo
        book.setSourceFilename(filename);
        book.setSourcePath(filePath.toString());
        book.setFileType(ext);
        book.setStatus(BookStatus.IMPORTED);
        book.setProjectId(1L);    // MOCK: default project
        book.setFolderId(null);

        try {
            book.setFileSize(Files.size(filePath));
        } catch (IOException e) {
            log.warn("Could not read file size for {}", filePath, e);
        }

        book.setCreatedBy("SYSTEM");
        return bookRepository.save(book);
    }

    /**
     * Step 2: Split the book's source file into chapters and persist them.
     * Status: BUILDING -> READY_FOR_QA, or BUILD_FAILED on error.
     */
    @Transactional
    public NovelBook buildBook(Long bookId) {
        NovelBook book = bookRepository.findById(bookId)
                .orElseThrow(() -> new IllegalArgumentException("Book not found: " + bookId));

        book.setStatus(BookStatus.BUILDING);
        bookRepository.save(book);

        try {
            String content = Files.readString(Paths.get(book.getSourcePath()),
                    Charset.forName("GB18030"));

            List<ChapterSplitter.ChapterSegment> segments = ChapterSplitter.split(content);

            if (segments.isEmpty()) {
                throw new IllegalStateException(
                        "No chapter markers found. Expected pattern: 第X回");
            }

            List<NovelChapter> chapters = new ArrayList<>(segments.size());
            for (ChapterSplitter.ChapterSegment seg : segments) {
                NovelChapter ch = new NovelChapter();
                ch.setBookId(book.getId());
                ch.setChapterNumber(seg.getNumber());
                ch.setTitle(seg.getTitle());
                ch.setRawContent(seg.getRawContent());
                ch.setCleanedContent(clean(seg.getRawContent()));
                ch.setCharCount(seg.getRawContent().length());
                ch.setStatus(ChapterStatus.CREATED);
                ch.setCreatedBy("SYSTEM");
                chapters.add(ch);
            }

            chapterRepository.saveAll(chapters);

            book.setTotalChapters(chapters.size());
            book.setStatus(BookStatus.READY_FOR_QA);
            bookRepository.save(book);

            log.info("Book '{}' built: {} chapters", book.getTitle(), chapters.size());
            return book;

        } catch (Exception e) {
            log.error("Build failed for book {}", bookId, e);
            book.setStatus(BookStatus.BUILD_FAILED);
            book.setErrorMessage(e.getMessage());
            bookRepository.save(book);
            return book;
        }
    }

    /**
     * Minimal text cleaning: trim, collapse blank lines.
     */
    private String clean(String raw) {
        if (raw == null) return null;
        return raw.trim().replaceAll("\\n{3,}", "\n\n");
    }
}
