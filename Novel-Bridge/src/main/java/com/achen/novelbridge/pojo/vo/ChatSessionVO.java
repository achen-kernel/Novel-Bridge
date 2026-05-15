package com.achen.novelbridge.pojo.vo;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class ChatSessionVO {

    private Long id;
    private Long bookId;
    private String title;
    private String status;
    private LocalDateTime createdAt;
    private List<ChatMessageVO> messages;
}
