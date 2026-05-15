package com.achen.novelbridge.pojo.vo;

import com.achen.novelbridge.common.enums.RunType;
import com.achen.novelbridge.common.enums.TaskStatus;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class AgentRunVO {

    private Long id;
    private RunType runType;
    private Long bookId;
    private TaskStatus status;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
    private String errorMessage;
    private List<AgentStepVO> steps;
}
