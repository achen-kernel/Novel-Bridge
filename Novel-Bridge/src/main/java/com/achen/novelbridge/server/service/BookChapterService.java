package com.achen.novelbridge.server.service;

import com.achen.novelbridge.pojo.vo.ChapterVO;
import com.achen.novelbridge.pojo.vo.ChunkVO;

import java.util.List;

/**
 * Service interface for book chapter and chunk queries.
 */
public interface BookChapterService {

    /**
     * Get all chapters for a book, ordered by chapter number.
     */
    List<ChapterVO> getChaptersByBook(Long bookId);

    /**
     * Get all chunks for a chapter, ordered by chunk index.
     * Content is truncated to the first 200 characters.
     */
    List<ChunkVO> getChunksByChapter(Long chapterId);
}
