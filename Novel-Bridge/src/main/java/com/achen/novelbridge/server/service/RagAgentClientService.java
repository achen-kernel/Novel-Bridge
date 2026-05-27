package com.achen.novelbridge.server.service;

import com.achen.novelbridge.common.properties.RagAgentProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

import java.util.Map;

/**
 * Asynchronous client for triggering processing on the Python rag-agent.
 * <p>
 * Uses {@link RestClient} to POST to the rag-agent's book process endpoint.
 * Failures are logged but do not affect the upload response.
 * </p>
 */
@Service
public class RagAgentClientService {

    private static final Logger log = LoggerFactory.getLogger(RagAgentClientService.class);

    private final RestClient restClient;
    private final RagAgentProperties properties;

    public RagAgentClientService(RagAgentProperties properties) {
        this.properties = properties;
        this.restClient = RestClient.builder()
                .baseUrl(properties.getBaseUrl())
                .build();
    }

    /**
     * Asynchronously triggers book processing on the Python rag-agent.
     * <p>
     * The caller does not wait for this to complete.
     * </p>
     *
     * @param bookId the book ID to process
     */
    @Async
    @SuppressWarnings("unchecked")
    public void triggerBookProcessing(Long bookId) {
        String url = properties.getBookProcessUrl().replace("{bookId}", String.valueOf(bookId));
        log.info("Triggering book processing: bookId={}, url={}", bookId, url);

        try {
            Map<String, Object> response = restClient.post()
                    .uri(url)
                    .body(Map.of("book_id", bookId))
                    .retrieve()
                    .body(Map.class);
            log.info("Book processing trigger response for bookId={}: {}", bookId, response);
        } catch (ResourceAccessException e) {
            log.error("Cannot connect to rag-agent for book processing (bookId={}): {}", bookId, e.getMessage());
        } catch (Exception e) {
            log.error("Failed to trigger book processing for bookId={}: {}", bookId, e.getMessage());
        }
    }

    /**
     * Triggers fact extraction for a book on the Python rag-agent.
     * <p>
     * Unlike triggerBookProcessing, this is called synchronously from
     * the extract endpoint so the caller can observe the result.
     * </p>
     *
     * @param bookId the book ID to extract facts for
     */
    @SuppressWarnings("unchecked")
    public void triggerFactExtraction(Long bookId) {
        String url = properties.getFactExtractUrl().replace("{bookId}", String.valueOf(bookId));
        log.info("Triggering fact extraction: bookId={}, url={}", bookId, url);

        try {
            Map<String, Object> response = restClient.post()
                    .uri(url)
                    .body(Map.of("book_id", bookId))
                    .retrieve()
                    .body(Map.class);
            log.info("Fact extraction trigger response for bookId={}: {}", bookId, response);
        } catch (ResourceAccessException e) {
            log.error("Cannot connect to rag-agent for fact extraction (bookId={}): {}", bookId, e.getMessage());
        } catch (Exception e) {
            log.error("Failed to trigger fact extraction for bookId={}: {}", bookId, e.getMessage());
        }
    }
}
