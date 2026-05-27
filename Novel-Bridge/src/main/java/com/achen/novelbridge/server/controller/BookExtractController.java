package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.result.R;
import com.achen.novelbridge.server.service.RagAgentClientService;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * REST controller for triggering book fact extraction on the Python rag-agent.
 *
 * @NB-ENTRYPOINT
 */
@RestController
@RequestMapping("/api/books")
public class BookExtractController {

    private final RagAgentClientService ragAgentClientService;

    public BookExtractController(RagAgentClientService ragAgentClientService) {
        this.ragAgentClientService = ragAgentClientService;
    }

    /**
     * Trigger fact extraction for a book on the Python rag-agent.
     *
     * @param bookId the book ID
     * @return trigger status
     */
    @PostMapping("/{bookId}/extract")
    public R<Map<String, Object>> triggerExtract(@PathVariable Long bookId) {
        ragAgentClientService.triggerFactExtraction(bookId);
        Map<String, Object> result = Map.of(
                "bookId", bookId,
                "status", "triggered"
        );
        return R.ok(result);
    }
}
