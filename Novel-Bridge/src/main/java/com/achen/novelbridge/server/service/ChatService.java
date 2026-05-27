package com.achen.novelbridge.server.service;

import com.achen.novelbridge.pojo.vo.ChatMessageVO;
import com.achen.novelbridge.pojo.vo.ChatSessionVO;
import com.achen.novelbridge.pojo.vo.QaRequest;

import java.util.List;

/**
 * Service interface for chat session and QA operations.
 */
public interface ChatService {

    /**
     * Create a new chat session for a book.
     *
     * @param bookId the book ID
     * @param title  optional session title
     * @return created session view
     */
    ChatSessionVO createSession(Long bookId, String title);

    /**
     * List all chat sessions for a book.
     *
     * @param bookId the book ID
     * @return list of session views
     */
    List<ChatSessionVO> getSessions(Long bookId);

    /**
     * Send a user question and get an AI answer with citations.
     *
     * @param request QA request with session ID and question
     * @return message view with answer and citations
     */
    ChatMessageVO sendMessage(QaRequest request);

    /**
     * Get all messages in a chat session.
     *
     * @param sessionId the session ID
     * @return list of message views with citations
     */
    List<ChatMessageVO> getMessages(Long sessionId);
}
