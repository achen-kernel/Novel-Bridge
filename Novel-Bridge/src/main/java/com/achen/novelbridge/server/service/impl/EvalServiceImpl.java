package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.pojo.entity.NovelEvalCase;
import com.achen.novelbridge.pojo.entity.NovelEvalResult;
import com.achen.novelbridge.pojo.entity.NovelEvalRun;
import com.achen.novelbridge.pojo.vo.EvalCaseVO;
import com.achen.novelbridge.pojo.vo.EvalResultVO;
import com.achen.novelbridge.pojo.vo.EvalRunVO;
import com.achen.novelbridge.server.mapper.EvalCaseMapper;
import com.achen.novelbridge.server.mapper.EvalResultMapper;
import com.achen.novelbridge.server.mapper.EvalRunMapper;
import com.achen.novelbridge.server.service.EvalService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Implementation of {@link EvalService} for evaluation queries.
 * <p>
 * JSON fields (expectedEntitiesJson, summaryJson, citationsJson, scoresJson)
 * are parsed into appropriate types before being returned in VOs.
 * </p>
 */
@Service
public class EvalServiceImpl implements EvalService {

    private static final Logger log = LoggerFactory.getLogger(EvalServiceImpl.class);

    private final EvalCaseMapper evalCaseMapper;
    private final EvalRunMapper evalRunMapper;
    private final EvalResultMapper evalResultMapper;
    private final ObjectMapper objectMapper;

    public EvalServiceImpl(EvalCaseMapper evalCaseMapper,
                           EvalRunMapper evalRunMapper,
                           EvalResultMapper evalResultMapper) {
        this.evalCaseMapper = evalCaseMapper;
        this.evalRunMapper = evalRunMapper;
        this.evalResultMapper = evalResultMapper;
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public List<EvalCaseVO> getCases(Long bookId, String category) {
        List<NovelEvalCase> cases;
        if (bookId != null) {
            cases = evalCaseMapper.findByBookId(bookId);
        } else if (category != null && !category.isBlank()) {
            cases = evalCaseMapper.findByCategory(category);
        } else {
            cases = evalCaseMapper.findAll();
        }
        if (cases == null || cases.isEmpty()) {
            return Collections.emptyList();
        }
        return cases.stream().map(this::toEvalCaseVO).collect(Collectors.toList());
    }

    @Override
    public List<EvalRunVO> getRuns() {
        List<NovelEvalRun> runs = evalRunMapper.findAll();
        if (runs == null || runs.isEmpty()) {
            return Collections.emptyList();
        }
        return runs.stream().map(this::toEvalRunVO).collect(Collectors.toList());
    }

    @Override
    public EvalRunVO getRun(Long runId) {
        NovelEvalRun run = evalRunMapper.findById(runId);
        if (run == null) {
            return null;
        }
        return toEvalRunVO(run);
    }

    @Override
    public List<EvalResultVO> getResults(Long runId) {
        List<NovelEvalResult> results = evalResultMapper.findByRunId(runId);
        if (results == null || results.isEmpty()) {
            return Collections.emptyList();
        }
        return results.stream().map(this::toEvalResultVO).collect(Collectors.toList());
    }

    private EvalCaseVO toEvalCaseVO(NovelEvalCase entity) {
        EvalCaseVO vo = new EvalCaseVO();
        vo.setId(entity.getId());
        vo.setBookId(entity.getBookId());
        vo.setQuestion(entity.getQuestion());
        vo.setExpectedAnswer(entity.getExpectedAnswer());
        vo.setExpectedEntities(parseJsonListSafe(entity.getExpectedEntitiesJson()));
        vo.setCategory(entity.getCategory());
        vo.setDifficulty(entity.getDifficulty());
        vo.setStatus(entity.getStatus());
        vo.setCreatedAt(entity.getCreatedAt());
        return vo;
    }

    private EvalRunVO toEvalRunVO(NovelEvalRun entity) {
        EvalRunVO vo = new EvalRunVO();
        vo.setId(entity.getId());
        vo.setRunType(entity.getRunType());
        vo.setStatus(entity.getStatus());
        vo.setSummary(parseJsonMapSafe(entity.getSummaryJson()));
        vo.setStartedAt(entity.getStartedAt());
        vo.setCompletedAt(entity.getCompletedAt());
        return vo;
    }

    private EvalResultVO toEvalResultVO(NovelEvalResult entity) {
        EvalResultVO vo = new EvalResultVO();
        vo.setId(entity.getId());
        vo.setRunId(entity.getRunId());
        vo.setCaseId(entity.getCaseId());
        vo.setQuestion(entity.getQuestion());
        vo.setActualAnswer(entity.getActualAnswer());
        vo.setCitations(parseJsonObjectListSafe(entity.getCitationsJson()));
        vo.setScores(parseJsonMapSafe(entity.getScoresJson()));
        vo.setErrorType(entity.getErrorType());
        vo.setStatus(entity.getStatus());
        return vo;
    }

    /**
     * Safely parse a JSON string into a List of Strings.
     * Returns null if parsing fails or input is blank.
     */
    private List<String> parseJsonListSafe(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (JsonProcessingException e) {
            log.warn("Failed to parse JSON list, returning null: {}", e.getMessage());
            return null;
        }
    }

    /**
     * Safely parse a JSON string into a Map of String to Object.
     * Returns null if parsing fails or input is blank.
     */
    private Map<String, Object> parseJsonMapSafe(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
        } catch (JsonProcessingException e) {
            log.warn("Failed to parse JSON map, returning null: {}", e.getMessage());
            return null;
        }
    }

    /**
     * Safely parse a JSON string into a List of generic Objects.
     * Returns null if parsing fails or input is blank.
     */
    private List<Object> parseJsonObjectListSafe(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<Object>>() {});
        } catch (JsonProcessingException e) {
            log.warn("Failed to parse JSON object list, returning null: {}", e.getMessage());
            return null;
        }
    }
}
