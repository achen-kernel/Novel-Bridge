package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.common.exception.BusinessException;
import com.achen.novelbridge.common.result.ResultCode;
import com.achen.novelbridge.pojo.entity.NovelChatMessage;
import com.achen.novelbridge.pojo.entity.NovelChatSession;
import com.achen.novelbridge.pojo.entity.NovelCitation;
import com.achen.novelbridge.pojo.vo.ChatMessageVO;
import com.achen.novelbridge.pojo.vo.ChatSessionVO;
import com.achen.novelbridge.pojo.vo.CitationVO;
import com.achen.novelbridge.pojo.vo.QaRequest;
import com.achen.novelbridge.server.mapper.ChatMessageMapper;
import com.achen.novelbridge.server.mapper.ChatSessionMapper;
import com.achen.novelbridge.server.mapper.CitationMapper;
import com.achen.novelbridge.server.service.ChatService;
import com.achen.novelbridge.server.service.QaClientService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Implementation of {@link ChatService} for chat session and QA operations.
 */
@Service
public class ChatServiceImpl implements ChatService {

    private static final Logger log = LoggerFactory.getLogger(ChatServiceImpl.class);

    private final ChatSessionMapper chatSessionMapper;
    private final ChatMessageMapper chatMessageMapper;
    private final CitationMapper citationMapper;
    private final QaClientService qaClientService;

    public ChatServiceImpl(ChatSessionMapper chatSessionMapper,
                           ChatMessageMapper chatMessageMapper,
                           CitationMapper citationMapper,
                           QaClientService qaClientService) {
        this.chatSessionMapper = chatSessionMapper;
        this.chatMessageMapper = chatMessageMapper;
        this.citationMapper = citationMapper;
        this.qaClientService = qaClientService;
    }

    @Override
    public ChatSessionVO createSession(Long bookId, String title) {
        NovelChatSession session = new NovelChatSession();
        session.setBookId(bookId);
        session.setTitle(title != null ? title : "");
        session.setStatus("ACTIVE");
        chatSessionMapper.insertSession(session);

        ChatSessionVO vo = new ChatSessionVO();
        vo.setId(session.getId());
        vo.setBookId(session.getBookId());
        vo.setTitle(session.getTitle());
        vo.setStatus(session.getStatus());
        vo.setMessageCount(0);
        vo.setCreatedAt(session.getCreatedAt());
        return vo;
    }

    @Override
    public List<ChatSessionVO> getSessions(Long bookId) {
        List<NovelChatSession> sessions = chatSessionMapper.findByBookId(bookId);
        if (sessions == null || sessions.isEmpty()) {
            return Collections.emptyList();
        }

        List<ChatSessionVO> vos = new ArrayList<>();
        for (NovelChatSession s : sessions) {
            ChatSessionVO vo = new ChatSessionVO();
            vo.setId(s.getId());
            vo.setBookId(s.getBookId());
            vo.setTitle(s.getTitle());
            vo.setStatus(s.getStatus());
            vo.setMessageCount(0);
            vo.setCreatedAt(s.getCreatedAt());
            vos.add(vo);
        }
        return vos;
    }

    @Override
    @Transactional
    public ChatMessageVO sendMessage(QaRequest request) {
        Long sessionId = request.getSessionId();
        NovelChatSession session = chatSessionMapper.findById(sessionId);
        if (session == null) {
            throw new BusinessException(ResultCode.NOT_FOUND.getCode(), "Chat session not found: " + sessionId);
        }

        // Determine next message index
        List<NovelChatMessage> existingMessages = chatMessageMapper.findBySessionId(sessionId);
        int nextIndex = (existingMessages != null ? existingMessages.size() : 0);

        // 1. Save user message
        NovelChatMessage userMsg = new NovelChatMessage();
        userMsg.setSessionId(sessionId);
        userMsg.setBookId(session.getBookId());
        userMsg.setRole("user");
        userMsg.setContent(request.getQuestion());
        userMsg.setMessageIndex(nextIndex);
        chatMessageMapper.insertMessage(userMsg);

        // 2. Call QA service
        Map<String, Object> qaResult = qaClientService.askQuestion(sessionId, session.getBookId(), request.getQuestion());

        // 3. Parse response
        String answer = (String) qaResult.getOrDefault("answer", "");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> citationMaps = (List<Map<String, Object>>) qaResult.getOrDefault("citations", Collections.emptyList());

        // 4. Save assistant message
        NovelChatMessage assistantMsg = new NovelChatMessage();
        assistantMsg.setSessionId(sessionId);
        assistantMsg.setBookId(session.getBookId());
        assistantMsg.setRole("assistant");
        assistantMsg.setContent(answer);
        assistantMsg.setMessageIndex(nextIndex + 1);
        chatMessageMapper.insertMessage(assistantMsg);

        // 5. Save citations
        List<NovelCitation> citationEntities = new ArrayList<>();
        if (citationMaps != null) {
            for (Map<String, Object> cm : citationMaps) {
                NovelCitation c = new NovelCitation();
                c.setMessageId(assistantMsg.getId());
                c.setBookId(session.getBookId());
                c.setSourceType((String) cm.getOrDefault("source_type", "chunk"));
                Object sourceId = cm.get("source_id");
                c.setSourceId(sourceId != null ? ((Number) sourceId).longValue() : 0L);
                Object chapterId = cm.get("chapter_id");
                if (chapterId != null) {
                    c.setChapterId(((Number) chapterId).longValue());
                }
                Object chunkId = cm.get("chunk_id");
                if (chunkId != null) {
                    c.setChunkId(((Number) chunkId).longValue());
                }
                Object chapterFactId = cm.get("chapter_fact_id");
                if (chapterFactId != null) {
                    c.setChapterFactId(((Number) chapterFactId).longValue());
                }
                c.setExcerpt((String) cm.getOrDefault("excerpt", ""));
                Object startOffset = cm.get("start_offset");
                if (startOffset != null) {
                    c.setStartOffset(((Number) startOffset).intValue());
                }
                Object endOffset = cm.get("end_offset");
                if (endOffset != null) {
                    c.setEndOffset(((Number) endOffset).intValue());
                }
                Object relevanceScore = cm.get("relevance_score");
                if (relevanceScore != null) {
                    c.setRelevanceScore(((Number) relevanceScore).doubleValue());
                }
                c.setEvidenceLevel((String) cm.getOrDefault("evidence_level", "NOT_CHECKED"));
                citationEntities.add(c);
            }
        }
        if (!citationEntities.isEmpty()) {
            citationMapper.insertBatch(citationEntities);
        }

        // 6. Build response
        return toChatMessageVO(assistantMsg, citationEntities);
    }

    @Override
    public List<ChatMessageVO> getMessages(Long sessionId) {
        NovelChatSession session = chatSessionMapper.findById(sessionId);
        if (session == null) {
            throw new BusinessException(ResultCode.NOT_FOUND.getCode(), "Chat session not found: " + sessionId);
        }

        List<NovelChatMessage> messages = chatMessageMapper.findBySessionId(sessionId);
        if (messages == null || messages.isEmpty()) {
            return Collections.emptyList();
        }

        List<ChatMessageVO> vos = new ArrayList<>();
        for (NovelChatMessage msg : messages) {
            List<NovelCitation> citations = citationMapper.findByMessageId(msg.getId());
            vos.add(toChatMessageVO(msg, citations));
        }
        return vos;
    }

    private ChatMessageVO toChatMessageVO(NovelChatMessage msg, List<NovelCitation> citations) {
        ChatMessageVO vo = new ChatMessageVO();
        vo.setId(msg.getId());
        vo.setSessionId(msg.getSessionId());
        vo.setRole(msg.getRole());
        vo.setContent(msg.getContent());
        vo.setMessageIndex(msg.getMessageIndex());
        vo.setCreatedAt(msg.getCreatedAt());
        if (citations != null) {
            vo.setCitations(citations.stream().map(this::toCitationVO).collect(Collectors.toList()));
        }
        return vo;
    }

    private CitationVO toCitationVO(NovelCitation c) {
        CitationVO vo = new CitationVO();
        vo.setId(c.getId());
        vo.setSourceType(c.getSourceType());
        vo.setSourceId(c.getSourceId());
        vo.setChapterId(c.getChapterId());
        vo.setExcerpt(c.getExcerpt());
        vo.setRelevanceScore(c.getRelevanceScore());
        vo.setEvidenceLevel(c.getEvidenceLevel());
        return vo;
    }
}
