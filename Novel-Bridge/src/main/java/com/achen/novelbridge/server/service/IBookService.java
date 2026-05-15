package com.achen.novelbridge.server.service;

import com.achen.novelbridge.pojo.entity.NovelBook;

/**
 * Book import and chapter building service contract.
 */
public interface IBookService {

    /**
     * Create a Book record from a file path.
     * Status = IMPORTED.
     */
    NovelBook createBook(String relativePath);

    /**
     * Split the book's source file into chapters and persist them,
     * with AgentRun/AgentStep tracking.
     * Status: BUILDING -> READY_FOR_QA, or BUILD_FAILED on error.
     */
    NovelBook buildBook(Long bookId);
}
