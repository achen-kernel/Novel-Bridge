package com.achen.novelbridge.server.service;

import com.achen.novelbridge.common.properties.RagAgentProperties;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

import java.time.Duration;
import java.util.Map;

/**
 * Service for checking the health of the Python rag-agent via its /health endpoint.
 * <p>
 * Uses Spring Boot 4.x {@link RestClient} (non-blocking MVC-friendly HTTP client).
 * </p>
 */
@Service
public class RagAgentHealthService {

    private final RestClient restClient;
    private final RagAgentProperties properties;

    public RagAgentHealthService(RagAgentProperties properties) {
        this.properties = properties;
        this.restClient = RestClient.builder()
                .baseUrl(properties.getBaseUrl())
                .build();
    }

    /**
     * Calls the rag-agent /health endpoint and returns the response body as a map,
     * or a map containing an error key on failure.
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> checkHealth() {
        try {
            return restClient.get()
                    .uri("/health")
                    .retrieve()
                    .body(Map.class);
        } catch (ResourceAccessException e) {
            return Map.of(
                    "status", "unavailable",
                    "error", "Cannot connect to rag-agent at " + properties.getBaseUrl() + ": " + e.getMessage()
            );
        } catch (Exception e) {
            return Map.of(
                    "status", "error",
                    "error", "Rag-agent health check failed: " + e.getMessage()
            );
        }
    }
}
