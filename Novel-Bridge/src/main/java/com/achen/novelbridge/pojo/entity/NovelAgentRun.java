package com.achen.novelbridge.pojo.entity;

import com.achen.novelbridge.common.base.BaseEntity;
import com.achen.novelbridge.common.enums.RunType;
import com.achen.novelbridge.common.enums.TaskStatus;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class NovelAgentRun extends BaseEntity {

    private RunType runType;
    private Long bookId;
    private TaskStatus status;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
    private String errorMessage;
}
