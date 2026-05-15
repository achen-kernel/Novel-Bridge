package com.achen.novelbridge.server.service;

import com.achen.novelbridge.common.enums.RunType;
import com.achen.novelbridge.common.enums.StepType;
import com.achen.novelbridge.pojo.entity.NovelAgentRun;
import com.achen.novelbridge.pojo.entity.NovelAgentStep;

import java.util.List;

/**
 * Agent run/step tracking service contract.
 */
public interface IAgentRunService {

    // ===== Run =====

    NovelAgentRun createRun(RunType runType, Long bookId);

    void completeRun(NovelAgentRun run);

    void failRun(NovelAgentRun run, String errorMessage);

    // ===== Step =====

    NovelAgentStep startStep(NovelAgentRun run, StepType stepType, int order);

    void completeStep(NovelAgentStep step);

    void failStep(NovelAgentStep step, String errorMessage);

    // ===== Query =====

    List<NovelAgentRun> getRunsByBookId(Long bookId);

    List<NovelAgentStep> getStepsByRunId(Long runId);
}
