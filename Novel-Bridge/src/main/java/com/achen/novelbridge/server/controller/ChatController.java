package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.result.R;
import com.achen.novelbridge.pojo.vo.ChatMessageVO;
import com.achen.novelbridge.pojo.vo.ChatSessionVO;
import com.achen.novelbridge.pojo.vo.QaRequest;
import com.achen.novelbridge.server.service.ChatService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * Chat session and QA endpoints.
 */
@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping("/sessions")
    public R<ChatSessionVO> createSession(@RequestParam Long bookId,
                                          @RequestParam(required = false) String title) {
        ChatSessionVO session = chatService.createSession(bookId, title);
        return R.ok(session);
    }

    @GetMapping("/sessions")
    public R<List<ChatSessionVO>> getSessions(@RequestParam Long bookId) {
        List<ChatSessionVO> sessions = chatService.getSessions(bookId);
        return R.ok(sessions);
    }

    @PostMapping("/sessions/{sessionId}/messages")
    public R<ChatMessageVO> sendMessage(@PathVariable Long sessionId,
                                        @Valid @RequestBody QaRequest request) {
        request.setSessionId(sessionId);
        ChatMessageVO message = chatService.sendMessage(request);
        return R.ok(message);
    }

    @GetMapping("/sessions/{sessionId}/messages")
    public R<List<ChatMessageVO>> getMessages(@PathVariable Long sessionId) {
        List<ChatMessageVO> messages = chatService.getMessages(sessionId);
        return R.ok(messages);
    }
}
