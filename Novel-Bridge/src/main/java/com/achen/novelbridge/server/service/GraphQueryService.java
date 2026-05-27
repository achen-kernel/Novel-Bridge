package com.achen.novelbridge.server.service;

import com.achen.novelbridge.pojo.vo.EventVO;
import com.achen.novelbridge.pojo.vo.PlotStageVO;
import com.achen.novelbridge.pojo.vo.RelationVO;

import java.util.List;
import java.util.Map;

/**
 * Service interface for graph/relation/event/plot queries.
 * <p>
 * Provides read access to consolidated relation facts, event facts,
 * and plot stages for a book, including entity-centered graph views.
 * </p>
 */
public interface GraphQueryService {

    /**
     * Get all consolidated relations for a book.
     */
    List<RelationVO> getRelationsByBook(Long bookId);

    /**
     * Get relations involving a specific entity in a book.
     */
    List<RelationVO> getRelationsByEntity(Long bookId, String entityName);

    /**
     * Get all consolidated events for a book.
     */
    List<EventVO> getEventsByBook(Long bookId);

    /**
     * Get events involving a specific participant in a book.
     */
    List<EventVO> getEventsByParticipant(Long bookId, String participant);

    /**
     * Get all plot stages for a book.
     */
    List<PlotStageVO> getPlotStages(Long bookId);

    /**
     * Get an entity-centered graph for a book, including relations and events.
     *
     * @return map with keys: "relations", "events", "entityName"
     */
    Map<String, Object> getEntityGraph(Long bookId, String entityName);
}
