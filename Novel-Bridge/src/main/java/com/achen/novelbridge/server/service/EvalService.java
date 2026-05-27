package com.achen.novelbridge.server.service;

import com.achen.novelbridge.pojo.vo.EvalCaseVO;
import com.achen.novelbridge.pojo.vo.EvalResultVO;
import com.achen.novelbridge.pojo.vo.EvalRunVO;

import java.util.List;

/**
 * Service interface for evaluation query operations.
 * <p>
 * Provides access to eval cases, runs, and results for
 * assessing retrieval and generation quality.
 * </p>
 */
public interface EvalService {

    /**
     * Get evaluation cases, optionally filtered by book or category.
     *
     * @param bookId   optional book ID filter
     * @param category optional category filter
     * @return list of eval case VOs
     */
    List<EvalCaseVO> getCases(Long bookId, String category);

    /**
     * Get all evaluation runs.
     *
     * @return list of eval run VOs
     */
    List<EvalRunVO> getRuns();

    /**
     * Get a single evaluation run by ID.
     *
     * @param runId the run ID
     * @return the eval run VO, or null if not found
     */
    EvalRunVO getRun(Long runId);

    /**
     * Get all evaluation results for a given run.
     *
     * @param runId the run ID
     * @return list of eval result VOs
     */
    List<EvalResultVO> getResults(Long runId);
}
