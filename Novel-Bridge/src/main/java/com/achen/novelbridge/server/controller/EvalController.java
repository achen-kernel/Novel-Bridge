package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.result.R;
import com.achen.novelbridge.pojo.vo.EvalCaseVO;
import com.achen.novelbridge.pojo.vo.EvalResultVO;
import com.achen.novelbridge.pojo.vo.EvalRunVO;
import com.achen.novelbridge.server.service.EvalService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * REST controller for evaluation query endpoints.
 * <p>
 * Stage 7: Eval case, run, and result retrieval for QA quality assessment.
 * </p>
 *
 * @NB-ENTRYPOINT
 * @NB-ROADMAP
 */
@RestController
@RequestMapping("/api/eval")
public class EvalController {

    private final EvalService evalService;

    public EvalController(EvalService evalService) {
        this.evalService = evalService;
    }

    /**
     * Get evaluation cases, optionally filtered by book ID or category.
     *
     * @param bookId   optional book ID filter
     * @param category optional category filter
     * @return list of eval cases
     */
    @GetMapping("/cases")
    public R<List<EvalCaseVO>> getCases(
            @RequestParam(value = "bookId", required = false) Long bookId,
            @RequestParam(value = "category", required = false) String category) {
        List<EvalCaseVO> cases = evalService.getCases(bookId, category);
        return R.ok(cases);
    }

    /**
     * Get all evaluation runs.
     *
     * @return list of eval runs
     */
    @GetMapping("/runs")
    public R<List<EvalRunVO>> getRuns() {
        List<EvalRunVO> runs = evalService.getRuns();
        return R.ok(runs);
    }

    /**
     * Get a single evaluation run by ID.
     *
     * @param runId the run ID
     * @return the eval run
     */
    @GetMapping("/runs/{runId}")
    public R<EvalRunVO> getRun(@PathVariable Long runId) {
        EvalRunVO run = evalService.getRun(runId);
        if (run == null) {
            return R.failed(404, "Eval run not found: " + runId);
        }
        return R.ok(run);
    }

    /**
     * Get all evaluation results for a given run.
     *
     * @param runId the run ID
     * @return list of eval results
     */
    @GetMapping("/runs/{runId}/results")
    public R<List<EvalResultVO>> getResults(@PathVariable Long runId) {
        List<EvalResultVO> results = evalService.getResults(runId);
        return R.ok(results);
    }
}
