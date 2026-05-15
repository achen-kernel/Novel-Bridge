package com.achen.novelbridge.server.service;

import com.achen.novelbridge.pojo.entity.NovelChatMessage;
import com.achen.novelbridge.pojo.entity.NovelChatSession;

import java.util.List;

/**
 * Chat session and question-answering service.
 * <p>
 * MOCK/DEBT: Uses keyword search + template answers.
 * Will be replaced by a real LLM in Demo 5.
 */
public interface IChatService {

    NovelChatSession createSession(Long bookId, String title);

    /**
     * Send a user question and get an answer with citations.
     * Returns the ASSISTANT message (answer).
     */
    NovelChatMessage sendMessage(Long sessionId, String questionContent);

    NovelChatSession getSession(Long sessionId);

    List<NovelChatMessage> getMessages(Long sessionId);
}
