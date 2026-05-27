package com.achen.novelbridge.server.service;

import com.achen.novelbridge.common.properties.RagAgentProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Client for calling the Python rag-agent's QA endpoint.
 * <p>
 * Posts questions to the rag-agent and returns the answer with citations.
 * Falls back to a mock response when the server is unavailable.
 * </p>
 */
@Service
public class QaClientService {

    private static final Logger log = LoggerFactory.getLogger(QaClientService.class);

    private final RestClient restClient;
    private final RagAgentProperties properties;

    public QaClientService(RagAgentProperties properties) {
        this.properties = properties;
        this.restClient = RestClient.builder()
                .baseUrl(properties.getBaseUrl())
                .build();
    }

    /**
     * Send a question to the rag-agent QA endpoint.
     *
     * @param sessionId the chat session ID
     * @param bookId    the book ID
     * @param question  the user's question
     * @return map containing "answer" (String) and "citations" (List of Maps)
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> askQuestion(Long sessionId, Long bookId, String question) {
        String url = properties.getQaUrl();
        log.info("Calling QA service: sessionId={}, bookId={}, url={}", sessionId, bookId, url);

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("session_id", sessionId);
        requestBody.put("book_id", bookId);
        requestBody.put("question", question);

        try {
            Map<String, Object> response = restClient.post()
                    .uri(url)
                    .body(requestBody)
                    .retrieve()
                    .body(Map.class);
            log.info("QA service response for sessionId={}: {}", sessionId, response);
            return response != null ? response : buildMockResponse(question);
        } catch (ResourceAccessException e) {
            log.error("Cannot connect to rag-agent QA service: {}", e.getMessage());
            return buildMockResponse(question);
        } catch (Exception e) {
            log.error("Failed to call QA service: {}", e.getMessage());
            return buildMockResponse(question);
        }
    }

    /**
     * Build a mock response when the QA service is unavailable.
     */
    private Map<String, Object> buildMockResponse(String question) {
        Map<String, Object> mock = new HashMap<>();
        mock.put("answer", "QA service is currently unavailable. Your question: \"" + question + "\"");
        mock.put("citations", Collections.emptyList());
        return mock;
    }
}
