package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.pojo.entity.NovelChapter;
import com.achen.novelbridge.pojo.entity.NovelChunk;
import com.achen.novelbridge.pojo.vo.ChapterVO;
import com.achen.novelbridge.pojo.vo.ChunkVO;
import com.achen.novelbridge.server.mapper.ChapterMapper;
import com.achen.novelbridge.server.mapper.ChunkMapper;
import com.achen.novelbridge.server.service.BookChapterService;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Implementation of BookChapterService.
 */
@Service
public class BookChapterServiceImpl implements BookChapterService {

    private final ChapterMapper chapterMapper;
    private final ChunkMapper chunkMapper;

    public BookChapterServiceImpl(ChapterMapper chapterMapper, ChunkMapper chunkMapper) {
        this.chapterMapper = chapterMapper;
        this.chunkMapper = chunkMapper;
    }

    @Override
    public List<ChapterVO> getChaptersByBook(Long bookId) {
        List<NovelChapter> chapters = chapterMapper.findByBookId(bookId);
        if (chapters == null || chapters.isEmpty()) {
            return Collections.emptyList();
        }
        return chapters.stream().map(this::toChapterVO).collect(Collectors.toList());
    }

    @Override
    public List<ChunkVO> getChunksByChapter(Long chapterId) {
        List<NovelChunk> chunks = chunkMapper.findByChapterId(chapterId);
        if (chunks == null || chunks.isEmpty()) {
            return Collections.emptyList();
        }
        return chunks.stream().map(this::toChunkVO).collect(Collectors.toList());
    }

    private ChapterVO toChapterVO(NovelChapter chapter) {
        ChapterVO vo = new ChapterVO();
        vo.setId(chapter.getId());
        vo.setBookId(chapter.getBookId());
        vo.setChapterNumber(chapter.getChapterNumber());
        vo.setTitle(chapter.getTitle());
        vo.setCharCount(chapter.getCharCount());
        vo.setStatus(chapter.getStatus());
        vo.setCreatedAt(chapter.getCreatedAt());
        return vo;
    }

    private ChunkVO toChunkVO(NovelChunk chunk) {
        ChunkVO vo = new ChunkVO();
        vo.setId(chunk.getId());
        vo.setBookId(chunk.getBookId());
        vo.setChapterId(chunk.getChapterId());
        vo.setChunkIndex(chunk.getChunkIndex());
        vo.setCharCount(chunk.getCharCount());
        // Truncate content to first 200 characters
        String content = chunk.getContent();
        if (content != null && content.length() > 200) {
            content = content.substring(0, 200);
        }
        vo.setContent(content);
        vo.setStatus(chunk.getStatus());
        vo.setCreatedAt(chunk.getCreatedAt());
        return vo;
    }
}
