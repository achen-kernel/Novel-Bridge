package com.achen.novelbridge.pojo.entity;

import com.achen.novelbridge.common.base.BaseEntity;
import com.achen.novelbridge.common.enums.ChatRole;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class NovelChatMessage extends BaseEntity {

    private Long sessionId;
    private ChatRole role;
    private String content;
    private Integer messageIndex;
}
