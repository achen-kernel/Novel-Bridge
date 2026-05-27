package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.pojo.entity.NovelChapterFact;
import com.achen.novelbridge.pojo.vo.ChapterFactVO;
import com.achen.novelbridge.server.mapper.ChapterFactMapper;
import com.achen.novelbridge.server.service.ChapterFactService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Implementation of ChapterFactService.
 * <p>
 * factJson and evidenceJson are parsed from JSON strings into Object
 * using Jackson ObjectMapper before being returned in the VO.
 * </p>
 *
 * @NB-EVIDENCE
 */
@Service
public class ChapterFactServiceImpl implements ChapterFactService {

    private static final Logger log = LoggerFactory.getLogger(ChapterFactServiceImpl.class);

    private final ChapterFactMapper chapterFactMapper;
    private final ObjectMapper objectMapper;

    public ChapterFactServiceImpl(ChapterFactMapper chapterFactMapper) {
        this.chapterFactMapper = chapterFactMapper;
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public ChapterFactVO getChapterFact(Long factId) {
        NovelChapterFact fact = chapterFactMapper.findById(factId);
        if (fact == null) {
            return null;
        }
        return toChapterFactVO(fact);
    }

    @Override
    public List<ChapterFactVO> getFactsByBook(Long bookId) {
        List<NovelChapterFact> facts = chapterFactMapper.findByBookId(bookId);
        if (facts == null || facts.isEmpty()) {
            return Collections.emptyList();
        }
        return facts.stream().map(this::toChapterFactVO).collect(Collectors.toList());
    }

    @Override
    public List<ChapterFactVO> getFactsByChapter(Long chapterId) {
        List<NovelChapterFact> facts = chapterFactMapper.findByChapterId(chapterId);
        if (facts == null || facts.isEmpty()) {
            return Collections.emptyList();
        }
        return facts.stream().map(this::toChapterFactVO).collect(Collectors.toList());
    }

    private ChapterFactVO toChapterFactVO(NovelChapterFact fact) {
        ChapterFactVO vo = new ChapterFactVO();
        vo.setId(fact.getId());
        vo.setBookId(fact.getBookId());
        vo.setChapterId(fact.getChapterId());
        vo.setFactJson(parseJsonSafe(fact.getFactJson()));
        vo.setEvidenceJson(parseJsonSafe(fact.getEvidenceJson()));
        vo.setSummary(fact.getSummary());
        vo.setParseStatus(fact.getParseStatus());
        vo.setEvidenceStatus(fact.getEvidenceStatus());
        vo.setReviewStatus(fact.getReviewStatus());
        vo.setStatus(fact.getStatus());
        vo.setErrorMessage(fact.getErrorMessage());
        vo.setCreatedAt(fact.getCreatedAt());
        return vo;
    }

    /**
     * Safely parse a JSON string into an Object.
     * Returns the raw string if parsing fails.
     */
    private Object parseJsonSafe(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, Object.class);
        } catch (JsonProcessingException e) {
            log.warn("Failed to parse JSON, returning raw string: {}", e.getMessage());
            return json;
        }
    }
}
