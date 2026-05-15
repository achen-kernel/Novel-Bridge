package com.achen.novelbridge.mapper;

import com.achen.novelbridge.pojo.entity.NovelAgentStep;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AgentStepMapper extends JpaRepository<NovelAgentStep, Long> {

    List<NovelAgentStep> findByAgentRunIdOrderByStepOrder(Long agentRunId);
}
