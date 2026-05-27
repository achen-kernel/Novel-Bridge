package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.pojo.entity.NovelAliasDecision;
import com.achen.novelbridge.pojo.entity.NovelEntityMention;
import com.achen.novelbridge.pojo.entity.NovelEntityProfile;
import com.achen.novelbridge.pojo.vo.AliasDecisionVO;
import com.achen.novelbridge.pojo.vo.ChapterEntityViewVO;
import com.achen.novelbridge.pojo.vo.ChapterEntityViewVO.ChapterEntityItem;
import com.achen.novelbridge.pojo.vo.EntityMentionVO;
import com.achen.novelbridge.pojo.vo.EntityProfileVO;
import com.achen.novelbridge.server.mapper.AliasDecisionMapper;
import com.achen.novelbridge.server.mapper.EntityMentionMapper;
import com.achen.novelbridge.server.mapper.EntityProfileMapper;
import com.achen.novelbridge.server.service.EntityGovernanceService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Implementation of EntityGovernanceService.
 * <p>
 * Converts entity entities to VOs, parsing JSON fields (aliases, risk types)
 * from their string representation into lists.
 * </p>
 */
@Service
public class EntityGovernanceServiceImpl implements EntityGovernanceService {

    private static final Logger log = LoggerFactory.getLogger(EntityGovernanceServiceImpl.class);

    private final EntityMentionMapper entityMentionMapper;
    private final EntityProfileMapper entityProfileMapper;
    private final AliasDecisionMapper aliasDecisionMapper;
    private final ObjectMapper objectMapper;

    public EntityGovernanceServiceImpl(EntityMentionMapper entityMentionMapper,
                                       EntityProfileMapper entityProfileMapper,
                                       AliasDecisionMapper aliasDecisionMapper) {
        this.entityMentionMapper = entityMentionMapper;
        this.entityProfileMapper = entityProfileMapper;
        this.aliasDecisionMapper = aliasDecisionMapper;
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public List<EntityMentionVO> getMentionsByBook(Long bookId) {
        List<NovelEntityMention> mentions = entityMentionMapper.findByBookId(bookId);
        if (mentions == null || mentions.isEmpty()) {
            return Collections.emptyList();
        }
        return mentions.stream().map(this::toEntityMentionVO).collect(Collectors.toList());
    }

    @Override
    public List<EntityMentionVO> getMentionsByChapter(Long chapterId) {
        List<NovelEntityMention> mentions = entityMentionMapper.findByChapterId(chapterId);
        if (mentions == null || mentions.isEmpty()) {
            return Collections.emptyList();
        }
        return mentions.stream().map(this::toEntityMentionVO).collect(Collectors.toList());
    }

    @Override
    public List<EntityProfileVO> getProfilesByBook(Long bookId) {
        List<NovelEntityProfile> profiles = entityProfileMapper.findByBookId(bookId);
        if (profiles == null || profiles.isEmpty()) {
            return Collections.emptyList();
        }
        return profiles.stream().map(this::toEntityProfileVO).collect(Collectors.toList());
    }

    @Override
    public EntityProfileVO getProfile(Long profileId) {
        NovelEntityProfile profile = entityProfileMapper.findById(profileId);
        if (profile == null) {
            return null;
        }
        return toEntityProfileVO(profile);
    }

    @Override
    public List<AliasDecisionVO> getDecisionsByBook(Long bookId) {
        List<NovelAliasDecision> decisions = aliasDecisionMapper.findByBookId(bookId);
        if (decisions == null || decisions.isEmpty()) {
            return Collections.emptyList();
        }
        return decisions.stream().map(this::toAliasDecisionVO).collect(Collectors.toList());
    }

    @Override
    public ChapterEntityViewVO getEntityViewByChapter(Long chapterId) {
        List<NovelEntityMention> mentions = entityMentionMapper.findByChapterId(chapterId);
        ChapterEntityViewVO view = new ChapterEntityViewVO();
        view.setChapterId(chapterId);

        // Group mentions by normalized_name (or surface_text if no normalized)
        Map<String, ChapterEntityItem> itemMap = new LinkedHashMap<>();
        if (mentions != null) {
            for (NovelEntityMention m : mentions) {
                String key = m.getNormalizedName() != null && !m.getNormalizedName().isBlank()
                        ? m.getNormalizedName() : m.getSurfaceText();
                ChapterEntityItem item = itemMap.get(key);
                if (item == null) {
                    item = new ChapterEntityItem();
                    item.setDisplayName(key);
                    item.setSurfaceTexts(new ArrayList<>());
                    item.setEntityType(m.getEntityType());
                    item.setIsGeneric(m.getIsGeneric());
                    item.setDoNotMergeGlobally(m.getDoNotMergeGlobally());
                    item.setMentionCount(0);
                    itemMap.put(key, item);
                }
                String st = m.getSurfaceText();
                if (st != null && !st.isBlank() && !item.getSurfaceTexts().contains(st)) {
                    item.getSurfaceTexts().add(st);
                }
                item.setMentionCount(item.getMentionCount() + 1);
            }
        }
        view.setEntities(new ArrayList<>(itemMap.values()));
        return view;
    }

    private EntityMentionVO toEntityMentionVO(NovelEntityMention mention) {
        EntityMentionVO vo = new EntityMentionVO();
        vo.setId(mention.getId());
        vo.setChapterId(mention.getChapterId());
        vo.setChunkId(mention.getChunkId());
        vo.setSurfaceText(mention.getSurfaceText());
        vo.setNormalizedName(mention.getNormalizedName());
        vo.setEntityType(mention.getEntityType());
        vo.setMentionRole(mention.getMentionRole());
        vo.setConfidence(mention.getConfidence());
        vo.setIsGeneric(mention.getIsGeneric());
        vo.setDoNotMergeGlobally(mention.getDoNotMergeGlobally());
        vo.setEvidenceText(mention.getEvidenceText());
        vo.setStatus(mention.getStatus());
        vo.setCreatedAt(mention.getCreatedAt());
        return vo;
    }

    private EntityProfileVO toEntityProfileVO(NovelEntityProfile profile) {
        EntityProfileVO vo = new EntityProfileVO();
        vo.setId(profile.getId());
        vo.setCanonicalName(profile.getCanonicalName());
        vo.setEntityType(profile.getEntityType());
        vo.setDescription(profile.getDescription());
        vo.setAliases(parseStringListSafe(profile.getAliasesJson()));
        vo.setMentionCount(profile.getMentionCount());
        vo.setSource(profile.getSource());
        vo.setStatus(profile.getStatus());
        vo.setCreatedAt(profile.getCreatedAt());
        return vo;
    }

    private AliasDecisionVO toAliasDecisionVO(NovelAliasDecision decision) {
        AliasDecisionVO vo = new AliasDecisionVO();
        vo.setId(decision.getId());
        vo.setEntityAName(decision.getEntityAName());
        vo.setEntityBName(decision.getEntityBName());
        vo.setDecision(decision.getDecision());
        vo.setConfidence(decision.getConfidence());
        vo.setReason(decision.getReason());
        vo.setRiskTypes(parseStringListSafe(decision.getRiskTypesJson()));
        vo.setReviewer(decision.getReviewer());
        vo.setCreatedAt(decision.getCreatedAt());
        return vo;
    }

    /**
     * Safely parse a JSON string array into a List of Strings.
     * Returns an empty list if parsing fails.
     */
    private List<String> parseStringListSafe(String json) {
        if (json == null || json.isBlank()) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (JsonProcessingException e) {
            log.warn("Failed to parse JSON string list, returning empty: {}", e.getMessage());
            return Collections.emptyList();
        }
    }
}
