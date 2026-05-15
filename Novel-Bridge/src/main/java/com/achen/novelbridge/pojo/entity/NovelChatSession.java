package com.achen.novelbridge.pojo.entity;

import com.achen.novelbridge.common.base.BaseEntity;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class NovelChatSession extends BaseEntity {

    private Long bookId;
    private Long userId;
    private String title;
    private String status;
}
