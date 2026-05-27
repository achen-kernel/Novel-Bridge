package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.result.R;
import com.achen.novelbridge.pojo.vo.ChapterFactVO;
import com.achen.novelbridge.server.service.ChapterFactService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * REST controller for chapter fact queries.
 *
 * @NB-ENTRYPOINT
 * @NB-EVIDENCE
 */
@RestController
@RequestMapping("/api")
public class ChapterFactController {

    private final ChapterFactService chapterFactService;

    public ChapterFactController(ChapterFactService chapterFactService) {
        this.chapterFactService = chapterFactService;
    }

    /**
     * Get a single chapter fact by its ID.
     *
     * @param factId the fact ID
     * @return the chapter fact VO
     */
    @GetMapping("/chapter-facts/{factId}")
    public R<ChapterFactVO> getChapterFact(@PathVariable Long factId) {
        ChapterFactVO fact = chapterFactService.getChapterFact(factId);
        if (fact == null) {
            return R.failed(404, "Chapter fact not found");
        }
        return R.ok(fact);
    }

    /**
     * Get all chapter facts for a book.
     *
     * @param bookId the book ID
     * @return list of chapter fact VOs
     */
    @GetMapping("/books/{bookId}/facts")
    public R<List<ChapterFactVO>> getFactsByBook(@PathVariable Long bookId) {
        List<ChapterFactVO> facts = chapterFactService.getFactsByBook(bookId);
        return R.ok(facts);
    }

    /**
     * Get all chapter facts for a chapter.
     *
     * @param chapterId the chapter ID
     * @return list of chapter fact VOs
     */
    @GetMapping("/chapters/{chapterId}/facts")
    public R<List<ChapterFactVO>> getFactsByChapter(@PathVariable Long chapterId) {
        List<ChapterFactVO> facts = chapterFactService.getFactsByChapter(chapterId);
        return R.ok(facts);
    }
}
