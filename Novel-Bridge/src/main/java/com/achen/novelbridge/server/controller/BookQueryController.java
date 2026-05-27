package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.result.R;
import com.achen.novelbridge.pojo.vo.ChapterVO;
import com.achen.novelbridge.pojo.vo.ChunkVO;
import com.achen.novelbridge.server.service.BookChapterService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * REST controller for book chapter and chunk queries.
 *
 * @NB-ENTRYPOINT
 */
@RestController
@RequestMapping("/api/books")
public class BookQueryController {

    private final BookChapterService bookChapterService;

    public BookQueryController(BookChapterService bookChapterService) {
        this.bookChapterService = bookChapterService;
    }

    /**
     * Get all chapters for a book, ordered by chapter number.
     *
     * @param bookId the book ID
     * @return list of chapter VOs
     */
    @GetMapping("/{bookId}/chapters")
    public R<List<ChapterVO>> getChapters(@PathVariable Long bookId) {
        List<ChapterVO> chapters = bookChapterService.getChaptersByBook(bookId);
        return R.ok(chapters);
    }

    /**
     * Get all chunks for a chapter, ordered by chunk index.
     *
     * @param chapterId the chapter ID
     * @return list of chunk VOs
     */
    @GetMapping("/{bookId}/chapters/{chapterId}/chunks")
    public R<List<ChunkVO>> getChunks(
            @PathVariable Long bookId,
            @PathVariable Long chapterId) {
        List<ChunkVO> chunks = bookChapterService.getChunksByChapter(chapterId);
        return R.ok(chunks);
    }
}
