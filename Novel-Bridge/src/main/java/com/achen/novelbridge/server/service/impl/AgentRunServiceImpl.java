package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.common.enums.RunType;
import com.achen.novelbridge.common.enums.StepStatus;
import com.achen.novelbridge.common.enums.StepType;
import com.achen.novelbridge.common.enums.TaskStatus;
import com.achen.novelbridge.server.mapper.AgentRunMapper;
import com.achen.novelbridge.server.mapper.AgentStepMapper;
import com.achen.novelbridge.pojo.entity.NovelAgentRun;
import com.achen.novelbridge.pojo.entity.NovelAgentStep;
import com.achen.novelbridge.server.service.IAgentRunService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
public class AgentRunServiceImpl implements IAgentRunService {

    private final AgentRunMapper runMapper;
    private final AgentStepMapper stepMapper;

    public AgentRunServiceImpl(AgentRunMapper runMapper, AgentStepMapper stepMapper) {
        this.runMapper = runMapper;
        this.stepMapper = stepMapper;
    }

    @Override
    @Transactional
    public NovelAgentRun createRun(RunType runType, Long bookId) {
        NovelAgentRun run = new NovelAgentRun();
        run.setRunType(runType);
        run.setBookId(bookId);
        run.setStatus(TaskStatus.RUNNING);
        run.setStartedAt(LocalDateTime.now());
        run.setCreatedBy("SYSTEM");
        runMapper.insert(run);
        return run;
    }

    @Override
    @Transactional
    public void completeRun(NovelAgentRun run) {
        run.setStatus(TaskStatus.SUCCESS);
        run.setCompletedAt(LocalDateTime.now());
        runMapper.update(run);
        log.info("AgentRun {} completed successfully", run.getId());
    }

    @Override
    @Transactional
    public void failRun(NovelAgentRun run, String errorMessage) {
        run.setStatus(TaskStatus.FAILED);
        run.setCompletedAt(LocalDateTime.now());
        run.setErrorMessage(errorMessage);
        runMapper.update(run);
        log.warn("AgentRun {} failed: {}", run.getId(), errorMessage);
    }

    @Override
    @Transactional
    public NovelAgentStep startStep(NovelAgentRun run, StepType stepType, int order) {
        NovelAgentStep step = new NovelAgentStep();
        step.setAgentRunId(run.getId());
        step.setStepType(stepType);
        step.setStepOrder(order);
        step.setStatus(StepStatus.RUNNING);
        step.setStartedAt(LocalDateTime.now());
        step.setCreatedBy("SYSTEM");
        stepMapper.insert(step);
        return step;
    }

    @Override
    @Transactional
    public void completeStep(NovelAgentStep step) {
        step.setStatus(StepStatus.SUCCESS);
        step.setCompletedAt(LocalDateTime.now());
        stepMapper.update(step);
    }

    @Override
    @Transactional
    public void failStep(NovelAgentStep step, String errorMessage) {
        step.setStatus(StepStatus.FAILED);
        step.setCompletedAt(LocalDateTime.now());
        step.setErrorMessage(errorMessage);
        stepMapper.update(step);
    }

    @Override
    public List<NovelAgentRun> getRunsByBookId(Long bookId) {
        return runMapper.findByBookIdOrderByCreatedAtDesc(bookId);
    }

    @Override
    public List<NovelAgentStep> getStepsByRunId(Long runId) {
        return stepMapper.findByAgentRunIdOrderByStepOrder(runId);
    }
}
