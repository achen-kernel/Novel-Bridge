package com.achen.novelbridge.pojo.vo;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class ChatMessageVO {

    private Long id;
    private String role;
    private String content;
    private Integer messageIndex;
    private LocalDateTime createdAt;
    private List<CitationVO> citations;
}
