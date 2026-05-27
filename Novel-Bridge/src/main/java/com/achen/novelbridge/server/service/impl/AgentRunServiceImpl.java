package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.pojo.entity.NovelAgentRun;
import com.achen.novelbridge.server.mapper.AgentRunMapper;
import com.achen.novelbridge.server.service.AgentRunService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

/**
 * Implementation of {@link AgentRunService} for managing agent run lifecycle.
 */
@Service
public class AgentRunServiceImpl implements AgentRunService {

    private static final Logger log = LoggerFactory.getLogger(AgentRunServiceImpl.class);

    private final AgentRunMapper agentRunMapper;

    private static final ObjectMapper objectMapper = new ObjectMapper();

    public AgentRunServiceImpl(AgentRunMapper agentRunMapper) {
        this.agentRunMapper = agentRunMapper;
    }

    @Override
    public NovelAgentRun createRun(String runType, Long bookId, Object input) {
        NovelAgentRun run = new NovelAgentRun();
        run.setRunType(runType);
        run.setBookId(bookId);
        run.setStatus("RUNNING");
        run.setStartedAt(LocalDateTime.now());

        if (input != null) {
            try {
                run.setInputJson(objectMapper.writeValueAsString(input));
            } catch (Exception e) {
                log.warn("Failed to serialize input JSON for agent run: {}", e.getMessage());
                run.setInputJson("{\"error\":\"serialization failed\"}");
            }
        }

        agentRunMapper.insertAgentRun(run);
        log.info("Created agent run: id={}, type={}, bookId={}", run.getId(), runType, bookId);
        return run;
    }

    @Override
    public NovelAgentRun getRun(Long id) {
        return agentRunMapper.findById(id);
    }
}
