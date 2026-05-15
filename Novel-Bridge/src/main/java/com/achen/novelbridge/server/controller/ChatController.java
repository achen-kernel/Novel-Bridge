package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.result.Result;
import com.achen.novelbridge.server.mapper.ChatMessageMapper;
import com.achen.novelbridge.server.mapper.CitationMapper;
import com.achen.novelbridge.pojo.dto.CreateSessionRequest;
import com.achen.novelbridge.pojo.dto.SendMessageRequest;
import com.achen.novelbridge.pojo.entity.NovelChatMessage;
import com.achen.novelbridge.pojo.entity.NovelChatSession;
import com.achen.novelbridge.pojo.entity.NovelCitation;
import com.achen.novelbridge.pojo.vo.ChatMessageVO;
import com.achen.novelbridge.pojo.vo.ChatSessionVO;
import com.achen.novelbridge.pojo.vo.CitationVO;
import com.achen.novelbridge.server.service.IChatService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final IChatService chatService;
    private final ChatMessageMapper chatMessageMapper;
    private final CitationMapper citationMapper;

    public ChatController(IChatService chatService,
                          ChatMessageMapper chatMessageMapper,
                          CitationMapper citationMapper) {
        this.chatService = chatService;
        this.chatMessageMapper = chatMessageMapper;
        this.citationMapper = citationMapper;
    }

    /**
     * Create a chat session for a book.
     */
    @PostMapping("/sessions")
    public Result<ChatSessionVO> createSession(@Valid @RequestBody CreateSessionRequest request) {
        NovelChatSession session = chatService.createSession(request.getBookId(), request.getTitle());
        return Result.success(toSessionVO(session));
    }

    /**
     * Send a message (question) and get an AI answer with citations.
     */
    @PostMapping("/sessions/{sessionId}/messages")
    public Result<ChatMessageVO> sendMessage(@PathVariable Long sessionId,
                                              @Valid @RequestBody SendMessageRequest request) {
        NovelChatMessage answer = chatService.sendMessage(sessionId, request.getContent());
        List<NovelCitation> citations = citationMapper.findByMessageId(answer.getId());
        return Result.success(toMessageVO(answer, citations));
    }

    /**
     * Get a session with all messages.
     */
    @GetMapping("/sessions/{sessionId}")
    public Result<ChatSessionVO> getSession(@PathVariable Long sessionId) {
        NovelChatSession session = chatService.getSession(sessionId);
        List<NovelChatMessage> messages = chatService.getMessages(sessionId);
        return Result.success(toSessionVO(session, messages));
    }

    // -- helper --

    private ChatSessionVO toSessionVO(NovelChatSession session) {
        return toSessionVO(session, List.of());
    }

    private ChatSessionVO toSessionVO(NovelChatSession session, List<NovelChatMessage> messages) {
        return ChatSessionVO.builder()
                .id(session.getId())
                .bookId(session.getBookId())
                .title(session.getTitle())
                .status(session.getStatus())
                .createdAt(session.getCreatedAt())
                .messages(messages.stream().map(m -> {
                    List<NovelCitation> cs = citationMapper.findByMessageId(m.getId());
                    return toMessageVO(m, cs);
                }).toList())
                .build();
    }

    private ChatMessageVO toMessageVO(NovelChatMessage msg, List<NovelCitation> citations) {
        return ChatMessageVO.builder()
                .id(msg.getId())
                .role(msg.getRole().name())
                .content(msg.getContent())
                .messageIndex(msg.getMessageIndex())
                .createdAt(msg.getCreatedAt())
                .citations(citations.stream().map(this::toCitationVO).toList())
                .build();
    }

    private CitationVO toCitationVO(NovelCitation c) {
        return CitationVO.builder()
                .id(c.getId())
                .sourceType(c.getSourceType().name())
                .sourceId(c.getSourceId())
                .chapterId(c.getChapterId())
                .relevanceScore(c.getRelevanceScore())
                .excerpt(c.getExcerpt())
                .build();
    }
}
