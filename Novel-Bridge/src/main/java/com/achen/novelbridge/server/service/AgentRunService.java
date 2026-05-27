package com.achen.novelbridge.server.service;

import com.achen.novelbridge.pojo.entity.NovelAgentRun;

/**
 * Service interface for agent run lifecycle management.
 */
public interface AgentRunService {

    /**
     * Create a new agent run and persist it.
     *
     * @param runType type of run (e.g. BOOK_BUILD, CHAPTER_EXTRACT)
     * @param bookId  associated book ID
     * @param input   input data (serialized to JSON)
     * @return the persisted agent run with generated ID
     */
    NovelAgentRun createRun(String runType, Long bookId, Object input);

    /**
     * Retrieve an agent run by ID.
     *
     * @param id run ID
     * @return the agent run, or null if not found
     */
    NovelAgentRun getRun(Long id);
}
