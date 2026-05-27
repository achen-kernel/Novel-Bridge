package com.achen.novelbridge.server.service;

import com.achen.novelbridge.pojo.vo.ChapterFactVO;

import java.util.List;

/**
 * Service interface for chapter fact queries.
 */
public interface ChapterFactService {

    /**
     * Get a single chapter fact by its ID.
     *
     * @param factId the fact ID
     * @return the chapter fact VO, or null if not found
     */
    ChapterFactVO getChapterFact(Long factId);

    /**
     * Get all chapter facts for a book.
     *
     * @param bookId the book ID
     * @return list of chapter fact VOs
     */
    List<ChapterFactVO> getFactsByBook(Long bookId);

    /**
     * Get all chapter facts for a chapter.
     *
     * @param chapterId the chapter ID
     * @return list of chapter fact VOs
     */
    List<ChapterFactVO> getFactsByChapter(Long chapterId);
}
