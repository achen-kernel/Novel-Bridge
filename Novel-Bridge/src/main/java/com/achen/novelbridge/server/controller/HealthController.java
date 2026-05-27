package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.result.R;
import com.achen.novelbridge.server.service.RagAgentHealthService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * Health check endpoints for the NovelBridge API.
 */
@RestController
@RequestMapping("/api")
public class HealthController {

    private final RagAgentHealthService ragAgentHealthService;

    public HealthController(RagAgentHealthService ragAgentHealthService) {
        this.ragAgentHealthService = ragAgentHealthService;
    }

    /**
     * Simple alive check for the Java API itself.
     */
    @GetMapping("/health")
    public R<String> health() {
        return R.ok("NovelBridge API is running");
    }

    /**
     * Proxies health check to the Python rag-agent service.
     */
    @GetMapping("/health/rag-agent")
    public R<Map<String, Object>> healthRagAgent() {
        Map<String, Object> agentStatus = ragAgentHealthService.checkHealth();
        return R.ok(agentStatus);
    }
}
