package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.common.enums.ChatRole;
import com.achen.novelbridge.common.enums.ChatSessionStatus;
import com.achen.novelbridge.common.enums.SourceType;
import com.achen.novelbridge.common.util.ChapterSplitter;
import com.achen.novelbridge.server.mapper.ChapterMapper;
import com.achen.novelbridge.server.mapper.ChatMessageMapper;
import com.achen.novelbridge.server.mapper.ChatSessionMapper;
import com.achen.novelbridge.server.mapper.CitationMapper;
import com.achen.novelbridge.pojo.entity.NovelChatMessage;
import com.achen.novelbridge.pojo.entity.NovelChatSession;
import com.achen.novelbridge.pojo.entity.NovelChapter;
import com.achen.novelbridge.pojo.entity.NovelCitation;
import com.achen.novelbridge.server.service.IChatService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Mock chat service using keyword search.
 * <p>
 * MOCK/DEBT: No LLM. Simple keyword matching to find relevant chapters.
 * Will be replaced by real model inference in Demo 5.
 */
@Slf4j
@Service
public class ChatServiceImpl implements IChatService {

    private static final Set<String> STOP_WORDS = Set.of(
            "的", "了", "是", "在", "有", "和", "就", "不", "人", "都",
            "一", "个", "上", "也", "很", "到", "说", "要", "去", "你",
            "会", "着", "没", "看", "好", "自己", "这", "那", "他", "她",
            "它", "们", "我", "与", "而", "或", "但", "被", "把", "从",
            "以", "对", "为", "其", "之", "所", "比", "将", "并", "让");

    private final ChatSessionMapper sessionMapper;
    private final ChatMessageMapper messageMapper;
    private final CitationMapper citationMapper;
    private final ChapterMapper chapterMapper;

    public ChatServiceImpl(ChatSessionMapper sessionMapper,
                           ChatMessageMapper messageMapper,
                           CitationMapper citationMapper,
                           ChapterMapper chapterMapper) {
        this.sessionMapper = sessionMapper;
        this.messageMapper = messageMapper;
        this.citationMapper = citationMapper;
        this.chapterMapper = chapterMapper;
    }

    @Override
    @Transactional
    public NovelChatSession createSession(Long bookId, String title) {
        NovelChatSession session = new NovelChatSession();
        session.setBookId(bookId);
        session.setUserId(1L); // MOCK: default user
        session.setTitle(title != null ? title : "新问答会话");
        session.setStatus(ChatSessionStatus.ACTIVE.name());
        session.setCreatedBy("SYSTEM");
        sessionMapper.insert(session);
        return session;
    }

    @Override
    @Transactional
    public NovelChatMessage sendMessage(Long sessionId, String questionContent) {
        NovelChatSession session = sessionMapper.findById(sessionId);
        if (session == null) {
            throw new IllegalArgumentException("Session not found: " + sessionId);
        }

        List<NovelChatMessage> existing = messageMapper.findBySessionIdOrderByMessageIndex(sessionId);
        int nextIndex = existing.isEmpty() ? 0 : existing.get(existing.size() - 1).getMessageIndex() + 1;

        // Save user message
        NovelChatMessage userMsg = new NovelChatMessage();
        userMsg.setSessionId(sessionId);
        userMsg.setRole(ChatRole.USER);
        userMsg.setContent(questionContent);
        userMsg.setMessageIndex(nextIndex);
        userMsg.setCreatedBy("SYSTEM");
        messageMapper.insert(userMsg);

        // Mock keyword search
        List<NovelChapter> chapters = chapterMapper.findByBookIdOrderByChapterNumber(session.getBookId());
        List<String> keywords = extractKeywords(questionContent);
        List<ChapterMatch> matches = scoreChapters(keywords, chapters);

        // Build answer
        String answer = buildAnswer(questionContent, keywords, matches);
        NovelChatMessage assistantMsg = new NovelChatMessage();
        assistantMsg.setSessionId(sessionId);
        assistantMsg.setRole(ChatRole.ASSISTANT);
        assistantMsg.setContent(answer);
        assistantMsg.setMessageIndex(nextIndex + 1);
        assistantMsg.setCreatedBy("SYSTEM");
        messageMapper.insert(assistantMsg);

        // Build citations from top matches
        List<NovelCitation> citations = new ArrayList<>();
        for (int i = 0; i < Math.min(3, matches.size()); i++) {
            ChapterMatch m = matches.get(i);
            if (m.score <= 0) continue;

            NovelCitation c = new NovelCitation();
            c.setMessageId(assistantMsg.getId());
            c.setSourceType(SourceType.CHAPTER);
            c.setSourceId(m.chapter.getId());
            c.setChapterId(m.chapter.getId());
            c.setRelevanceScore((double) m.score / keywords.size());
            c.setExcerpt(buildExcerpt(m.chapter.getCleanedContent(), keywords, 120));
            c.setCreatedBy("SYSTEM");
            citations.add(c);
        }
        if (!citations.isEmpty()) {
            citationMapper.insertBatch(citations);
        }

        log.info("Session {}: question '{}' → {} citations", sessionId,
                questionContent.substring(0, Math.min(30, questionContent.length())), citations.size());
        return assistantMsg;
    }

    @Override
    public NovelChatSession getSession(Long sessionId) {
        NovelChatSession session = sessionMapper.findById(sessionId);
        if (session == null) {
            throw new IllegalArgumentException("Session not found: " + sessionId);
        }
        return session;
    }

    @Override
    public List<NovelChatMessage> getMessages(Long sessionId) {
        return messageMapper.findBySessionIdOrderByMessageIndex(sessionId);
    }

    // ---- Mock keyword search ----

    private List<String> extractKeywords(String text) {
        String[] tokens = text.split("[^\\u4e00-\\u9fa5\\w]+");
        return java.util.Arrays.stream(tokens)
                .map(String::trim)
                .filter(t -> t.length() >= 2)
                .filter(t -> !STOP_WORDS.contains(t))
                .distinct()
                .limit(10)
                .collect(Collectors.toList());
    }

    private List<ChapterMatch> scoreChapters(List<String> keywords, List<NovelChapter> chapters) {
        List<ChapterMatch> results = new ArrayList<>();
        for (NovelChapter chapter : chapters) {
            String content = chapter.getCleanedContent() != null
                    ? chapter.getCleanedContent() : chapter.getRawContent();
            if (content == null) continue;

            int score = 0;
            for (String kw : keywords) {
                score += countOccurrences(content.toLowerCase(), kw.toLowerCase());
            }
            if (score > 0) {
                results.add(new ChapterMatch(chapter, score));
            }
        }
        results.sort(Comparator.comparingInt((ChapterMatch m) -> m.score).reversed());
        return results;
    }

    private int countOccurrences(String text, String keyword) {
        int count = 0, idx = 0;
        while ((idx = text.indexOf(keyword, idx)) != -1) {
            count++;
            idx += keyword.length();
        }
        return count;
    }

    private String buildAnswer(String question, List<String> keywords, List<ChapterMatch> matches) {
        if (keywords.isEmpty() || matches.isEmpty()) {
            return "你问的是「" + question + "」。\n\n"
                    + "（暂未找到相关章节。MOCK/DEBT：当前使用关键词检索，"
                    + "Demo 5 将接入真实模型。）";
        }

        StringBuilder sb = new StringBuilder();
        sb.append("你的问题提到了「").append(String.join("、", keywords)).append("」");
        sb.append("，以下是《西游记》中相关章节的内容：\n\n");

        int limit = Math.min(3, matches.size());
        for (int i = 0; i < limit; i++) {
            ChapterMatch m = matches.get(i);
            sb.append("📖 第").append(m.chapter.getChapterNumber()).append("回「")
                    .append(m.chapter.getTitle()).append("」\n");
            String excerpt = buildExcerpt(m.chapter.getCleanedContent() != null
                    ? m.chapter.getCleanedContent() : m.chapter.getRawContent(), keywords, 100);
            sb.append("   ").append(excerpt).append("…\n\n");
        }
        sb.append("（MOCK/DEBT：当前为关键词检索结果，Demo 5 将接入真实 LLM 模型。）");
        return sb.toString();
    }

    private String buildExcerpt(String text, List<String> keywords, int maxLen) {
        if (text == null || text.isEmpty()) return "";
        int bestPos = text.length();
        for (String kw : keywords) {
            int pos = text.indexOf(kw);
            if (pos != -1 && pos < bestPos) {
                bestPos = pos;
            }
        }
        int start = Math.max(0, bestPos - maxLen / 2);
        int end = Math.min(text.length(), bestPos + maxLen / 2);
        String excerpt = text.substring(start, end).replace('\n', ' ').trim();
        if (start > 0) excerpt = "…" + excerpt;
        if (end < text.length()) excerpt = excerpt + "…";
        return excerpt;
    }

    private record ChapterMatch(NovelChapter chapter, int score) {}
}
