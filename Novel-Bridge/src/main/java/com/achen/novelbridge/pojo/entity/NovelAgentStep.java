package com.achen.novelbridge.pojo.entity;

import com.achen.novelbridge.common.base.BaseEntity;
import com.achen.novelbridge.common.enums.StepStatus;
import com.achen.novelbridge.common.enums.StepType;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class NovelAgentStep extends BaseEntity {

    private Long agentRunId;
    private StepType stepType;
    private Integer stepOrder;
    private StepStatus status;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
    private String errorMessage;
}
