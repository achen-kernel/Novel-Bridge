package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.common.enums.BookStatus;
import com.achen.novelbridge.common.enums.ChapterStatus;
import com.achen.novelbridge.common.enums.RunType;
import com.achen.novelbridge.common.enums.StepType;
import com.achen.novelbridge.common.properties.BooksProperties;
import com.achen.novelbridge.common.util.ChapterSplitter;
import com.achen.novelbridge.server.mapper.BookMapper;
import com.achen.novelbridge.server.mapper.ChapterMapper;
import com.achen.novelbridge.pojo.entity.NovelAgentRun;
import com.achen.novelbridge.pojo.entity.NovelAgentStep;
import com.achen.novelbridge.pojo.entity.NovelBook;
import com.achen.novelbridge.pojo.entity.NovelChapter;
import com.achen.novelbridge.server.service.IBookService;
import com.achen.novelbridge.server.service.IAgentRunService;
import lombok.extern.slf4j.Slf4j;
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
public class BookServiceImpl implements IBookService {

    private final BookMapper bookMapper;
    private final ChapterMapper chapterMapper;
    private final IAgentRunService agentRunService;
    private final BooksProperties booksProperties;

    public BookServiceImpl(BookMapper bookMapper,
                           ChapterMapper chapterMapper,
                           IAgentRunService agentRunService,
                           BooksProperties booksProperties) {
        this.bookMapper = bookMapper;
        this.chapterMapper = chapterMapper;
        this.agentRunService = agentRunService;
        this.booksProperties = booksProperties;
    }

    @Override
    @Transactional
    public NovelBook createBook(String relativePath) {
        Path filePath = booksProperties.getBaseDirPath().resolve(relativePath).normalize();

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
        bookMapper.insert(book);
        return book;
    }

    @Override
    @Transactional
    // @VTL-PRACTICE version=demo-2 name=buildBook
    // goal=用 AgentRun/AgentStep 包裹业务流程实现可追踪
    // prerequisites=理解 NovelBook/NovelChapter/NovelAgentRun 的实体关系
    // inputs=bookId
    // outputs=NovelBook with status=READY_FOR_QA or BUILD_FAILED
    // pitfalls=事务边界在哪里？catch 里的保存会不会被回滚？
    // hints=每个步骤先 startStep → 执行业务 → completeStep/failStep
    public NovelBook buildBook(Long bookId) {
        NovelBook book = bookMapper.findById(bookId);
        if (book == null) {
            throw new IllegalArgumentException("Book not found: " + bookId);
        }

        book.setStatus(BookStatus.BUILDING);
        bookMapper.update(book);

        // Create AgentRun — tracks the entire build process
        NovelAgentRun run = agentRunService.createRun(RunType.BOOK_BUILD, bookId);
        int order = 0;

        try {
            // --- Step 0: validate file ---
            NovelAgentStep step0 = agentRunService.startStep(run, StepType.VALIDATE_FILE, order++);
            Path filePath = Paths.get(book.getSourcePath());
            if (!Files.isRegularFile(filePath)) {
                throw new IllegalStateException("File not found: " + filePath);
            }
            agentRunService.completeStep(step0);

            // --- Step 1: read file ---
            NovelAgentStep step1 = agentRunService.startStep(run, StepType.READ_FILE, order++);
            String content = Files.readString(filePath, Charset.forName("GB18030"));
            agentRunService.completeStep(step1);

            // --- Step 2: split chapters ---
            NovelAgentStep step2 = agentRunService.startStep(run, StepType.SPLIT_CHAPTERS, order++);
            List<ChapterSplitter.ChapterSegment> segments = ChapterSplitter.split(content);
            if (segments.isEmpty()) {
                throw new IllegalStateException("No chapter markers found. Expected pattern: 第X回");
            }
            agentRunService.completeStep(step2);

            // --- Step 3: save chapters ---
            NovelAgentStep step3 = agentRunService.startStep(run, StepType.SAVE_CHAPTERS, order++);
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
                chapterMapper.insert(ch);
            }
            agentRunService.completeStep(step3);

            // --- Step 4: update book status ---
            NovelAgentStep step4 = agentRunService.startStep(run, StepType.UPDATE_BOOK_STATUS, order);
            book.setTotalChapters(chapters.size());
            book.setStatus(BookStatus.READY_FOR_QA);
            bookMapper.update(book);
            agentRunService.completeStep(step4);

            // Complete run
            agentRunService.completeRun(run);
            log.info("Book '{}' built: {} chapters", book.getTitle(), chapters.size());
            return book;

        } catch (Exception e) {
            log.error("Build failed for book {}", bookId, e);
            agentRunService.failRun(run, e.getMessage());
            book.setStatus(BookStatus.BUILD_FAILED);
            book.setErrorMessage(e.getMessage());
            bookMapper.update(book);
            return book;
        }
    }

    private String clean(String raw) {
        if (raw == null) return null;
        return raw.trim().replaceAll("\\n{3,}", "\n\n");
    }
}
