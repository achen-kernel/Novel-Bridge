package com.achen.novelbridge.common.properties;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Configuration properties for the Python rag-agent service connection.
 */
@ConfigurationProperties(prefix = "novelbridge.rag-agent")
public class RagAgentProperties {

    /**
     * Base URL of the Python rag-agent service.
     */
    private String baseUrl = "http://localhost:18081";

    /**
     * Connection/read timeout in milliseconds.
     */
    private int timeout = 5000;

    /**
     * URL template for triggering book processing on the rag-agent.
     * {bookId} is replaced with the actual book ID.
     */
    private String bookProcessUrl = "http://localhost:18081/api/books/{bookId}/process";

    /**
     * URL template for triggering fact extraction on the rag-agent.
     * {bookId} is replaced with the actual book ID.
     */
    private String factExtractUrl = "http://localhost:18081/api/books/{bookId}/extract";

    /**
     * URL for the QA ask endpoint on the rag-agent.
     */
    private String qaUrl = "http://localhost:18081/api/qa/ask";

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public int getTimeout() {
        return timeout;
    }

    public void setTimeout(int timeout) {
        this.timeout = timeout;
    }

    public String getBookProcessUrl() {
        return bookProcessUrl;
    }

    public void setBookProcessUrl(String bookProcessUrl) {
        this.bookProcessUrl = bookProcessUrl;
    }

    public String getFactExtractUrl() {
        return factExtractUrl;
    }

    public void setFactExtractUrl(String factExtractUrl) {
        this.factExtractUrl = factExtractUrl;
    }

    public String getQaUrl() {
        return qaUrl;
    }

    public void setQaUrl(String qaUrl) {
        this.qaUrl = qaUrl;
    }
}
