package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.result.R;
import com.achen.novelbridge.pojo.vo.EventVO;
import com.achen.novelbridge.pojo.vo.PlotStageVO;
import com.achen.novelbridge.pojo.vo.RelationVO;
import com.achen.novelbridge.server.service.GraphQueryService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * REST controller for graph/relation/event/plot queries.
 * <p>
 * Provides read access to relation facts, event facts, plot stages,
 * and entity-centered graph views.
 * </p>
 *
 * @NB-ENTRYPOINT
 * @NB-EVIDENCE
 */
@RestController
@RequestMapping("/api")
public class GraphController {

    private final GraphQueryService graphQueryService;

    public GraphController(GraphQueryService graphQueryService) {
        this.graphQueryService = graphQueryService;
    }

    /**
     * Get all consolidated relations for a book.
     *
     * @param bookId the book ID
     * @return list of relation VOs
     */
    @GetMapping("/books/{bookId}/relations")
    public R<List<RelationVO>> getRelationsByBook(@PathVariable Long bookId) {
        List<RelationVO> relations = graphQueryService.getRelationsByBook(bookId);
        return R.ok(relations);
    }

    /**
     * Get relations involving a specific entity in a book.
     *
     * @param bookId   the book ID
     * @param entity   the entity name
     * @return list of relation VOs
     */
    @GetMapping("/books/{bookId}/relations/{entity}")
    public R<List<RelationVO>> getRelationsByEntity(@PathVariable Long bookId, @PathVariable String entity) {
        List<RelationVO> relations = graphQueryService.getRelationsByEntity(bookId, entity);
        return R.ok(relations);
    }

    /**
     * Get all consolidated events for a book.
     *
     * @param bookId the book ID
     * @return list of event VOs
     */
    @GetMapping("/books/{bookId}/events")
    public R<List<EventVO>> getEventsByBook(@PathVariable Long bookId) {
        List<EventVO> events = graphQueryService.getEventsByBook(bookId);
        return R.ok(events);
    }

    /**
     * Get events involving a specific participant in a book.
     *
     * @param bookId      the book ID
     * @param participant the participant name
     * @return list of event VOs
     */
    @GetMapping("/books/{bookId}/events/{participant}")
    public R<List<EventVO>> getEventsByParticipant(@PathVariable Long bookId, @PathVariable String participant) {
        List<EventVO> events = graphQueryService.getEventsByParticipant(bookId, participant);
        return R.ok(events);
    }

    /**
     * Get all plot stages for a book.
     *
     * @param bookId the book ID
     * @return list of plot stage VOs
     */
    @GetMapping("/books/{bookId}/plot-stages")
    public R<List<PlotStageVO>> getPlotStages(@PathVariable Long bookId) {
        List<PlotStageVO> stages = graphQueryService.getPlotStages(bookId);
        return R.ok(stages);
    }

    /**
     * Get an entity-centered graph for a book.
     * <p>
     * Returns relations and events involving the specified entity.
     *
     * @param bookId     the book ID
     * @param entityName the entity name
     * @return map with keys: "entityName", "relations", "events"
     */
    @GetMapping("/books/{bookId}/graph/{entityName}")
    public R<Map<String, Object>> getEntityGraph(@PathVariable Long bookId, @PathVariable String entityName) {
        Map<String, Object> graph = graphQueryService.getEntityGraph(bookId, entityName);
        return R.ok(graph);
    }
}
