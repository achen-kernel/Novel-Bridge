package com.achen.novelbridge.pojo.vo;

import com.achen.novelbridge.common.enums.StepStatus;
import com.achen.novelbridge.common.enums.StepType;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class AgentStepVO {

    private Long id;
    private StepType stepType;
    private Integer stepOrder;
    private StepStatus status;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
    private String errorMessage;
}
