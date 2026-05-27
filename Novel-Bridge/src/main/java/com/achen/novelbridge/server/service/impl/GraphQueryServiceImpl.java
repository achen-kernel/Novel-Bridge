package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.pojo.entity.NovelEventFact;
import com.achen.novelbridge.pojo.entity.NovelPlotStage;
import com.achen.novelbridge.pojo.entity.NovelRelationFact;
import com.achen.novelbridge.pojo.vo.EventVO;
import com.achen.novelbridge.pojo.vo.PlotStageVO;
import com.achen.novelbridge.pojo.vo.RelationVO;
import com.achen.novelbridge.server.mapper.EventFactMapper;
import com.achen.novelbridge.server.mapper.PlotStageMapper;
import com.achen.novelbridge.server.mapper.RelationFactMapper;
import com.achen.novelbridge.server.service.GraphQueryService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Implementation of GraphQueryService.
 * <p>
 * Converts relation, event, and plot entities to VOs, parsing JSON fields
 * from their string representation into lists.
 * </p>
 */
@Service
public class GraphQueryServiceImpl implements GraphQueryService {

    private static final Logger log = LoggerFactory.getLogger(GraphQueryServiceImpl.class);

    private final RelationFactMapper relationFactMapper;
    private final EventFactMapper eventFactMapper;
    private final PlotStageMapper plotStageMapper;
    private final ObjectMapper objectMapper;

    public GraphQueryServiceImpl(RelationFactMapper relationFactMapper,
                                 EventFactMapper eventFactMapper,
                                 PlotStageMapper plotStageMapper) {
        this.relationFactMapper = relationFactMapper;
        this.eventFactMapper = eventFactMapper;
        this.plotStageMapper = plotStageMapper;
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public List<RelationVO> getRelationsByBook(Long bookId) {
        List<NovelRelationFact> facts = relationFactMapper.findByBookId(bookId);
        if (facts == null || facts.isEmpty()) {
            return Collections.emptyList();
        }
        return facts.stream().map(this::toRelationVO).collect(Collectors.toList());
    }

    @Override
    public List<RelationVO> getRelationsByEntity(Long bookId, String entityName) {
        List<NovelRelationFact> facts = relationFactMapper.findByEntityName(bookId, entityName);
        if (facts == null || facts.isEmpty()) {
            return Collections.emptyList();
        }
        return facts.stream().map(this::toRelationVO).collect(Collectors.toList());
    }

    @Override
    public List<EventVO> getEventsByBook(Long bookId) {
        List<NovelEventFact> facts = eventFactMapper.findByBookId(bookId);
        if (facts == null || facts.isEmpty()) {
            return Collections.emptyList();
        }
        return facts.stream().map(this::toEventVO).collect(Collectors.toList());
    }

    @Override
    public List<EventVO> getEventsByParticipant(Long bookId, String participant) {
        List<NovelEventFact> facts = eventFactMapper.findByParticipant(bookId, participant);
        if (facts == null || facts.isEmpty()) {
            return Collections.emptyList();
        }
        return facts.stream().map(this::toEventVO).collect(Collectors.toList());
    }

    @Override
    public List<PlotStageVO> getPlotStages(Long bookId) {
        List<NovelPlotStage> stages = plotStageMapper.findByBookId(bookId);
        if (stages == null || stages.isEmpty()) {
            return Collections.emptyList();
        }
        return stages.stream().map(this::toPlotStageVO).collect(Collectors.toList());
    }

    @Override
    public Map<String, Object> getEntityGraph(Long bookId, String entityName) {
        List<RelationVO> relations = getRelationsByEntity(bookId, entityName);
        List<EventVO> events = getEventsByParticipant(bookId, entityName);

        Map<String, Object> graph = new HashMap<>();
        graph.put("entityName", entityName);
        graph.put("relations", relations);
        graph.put("events", events);
        return graph;
    }

    private RelationVO toRelationVO(NovelRelationFact fact) {
        RelationVO vo = new RelationVO();
        vo.setId(fact.getId());
        vo.setSourceEntityName(fact.getSourceEntityName());
        vo.setTargetEntityName(fact.getTargetEntityName());
        vo.setRelationType(fact.getRelationType());
        vo.setRelationFamily(fact.getRelationFamily());
        vo.setPolarity(fact.getPolarity());
        vo.setConfidence(fact.getConfidence());
        vo.setStatus(fact.getStatus());
        return vo;
    }

    private EventVO toEventVO(NovelEventFact fact) {
        EventVO vo = new EventVO();
        vo.setId(fact.getId());
        vo.setEventType(fact.getEventType());
        vo.setSummary(fact.getSummary());
        vo.setParticipants(parseStringListSafe(fact.getParticipantsJson()));
        vo.setLocation(fact.getLocation());
        vo.setImportance(fact.getImportance());
        vo.setConfidence(null); // confidence not at event fact level
        vo.setStatus(fact.getStatus());
        return vo;
    }

    private PlotStageVO toPlotStageVO(NovelPlotStage stage) {
        PlotStageVO vo = new PlotStageVO();
        vo.setId(stage.getId());
        vo.setStageIndex(stage.getStageIndex());
        vo.setStageName(stage.getStageName());
        vo.setSummary(stage.getSummary());
        vo.setStartChapterId(stage.getStartChapterId() != null ? stage.getStartChapterId().intValue() : null);
        vo.setEndChapterId(stage.getEndChapterId() != null ? stage.getEndChapterId().intValue() : null);
        vo.setKeyEntities(parseStringListSafe(stage.getKeyEntitiesJson()));
        vo.setStatus(stage.getStatus());
        return vo;
    }

    /**
     * Safely parse a JSON string array into a List of Strings.
     * Returns an empty list if parsing fails.
     */
    private List<String> parseStringListSafe(String json) {
        if (json == null || json.isBlank()) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (JsonProcessingException e) {
            log.warn("Failed to parse JSON string list, returning empty: {}", e.getMessage());
            return Collections.emptyList();
        }
    }
}
