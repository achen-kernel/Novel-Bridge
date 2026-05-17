package com.achen.novelbridge.common.properties;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Maps novel-bridge.rag-agent.* configuration from application.yml.
 * <p>
 * Demo 5A: base-url for remote rag-agent endpoint.
 * Demo 5B+: will be extended with timeout, retry, model config.
 */
@Data
@Component
@ConfigurationProperties(prefix = "novel-bridge.rag-agent")
public class RagAgentProperties {

    /** Base URL of the remote rag-agent service, e.g. http://192.168.3.50:18081 */
    private String baseUrl;

    /** Request timeout in milliseconds (default 30s). */
    private long timeoutMs = 30_000;
}
