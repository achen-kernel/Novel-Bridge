package com.achen.novelbridge.server.service;

import com.achen.novelbridge.pojo.vo.AliasDecisionVO;
import com.achen.novelbridge.pojo.vo.EntityMentionVO;
import com.achen.novelbridge.pojo.vo.ChapterEntityViewVO;
import com.achen.novelbridge.pojo.vo.EntityProfileVO;

import java.util.List;

/**
 * Service interface for entity governance operations.
 * <p>
 * Provides query access to entity mentions, profiles, and alias decisions
 * extracted and managed by the rag-agent pipeline.
 * </p>
 */
public interface EntityGovernanceService {

    /**
     * Get all entity mentions for a book.
     *
     * @param bookId the book ID
     * @return list of entity mention VOs
     */
    List<EntityMentionVO> getMentionsByBook(Long bookId);

    /**
     * Get all entity mentions for a chapter.
     *
     * @param chapterId the chapter ID
     * @return list of entity mention VOs
     */
    List<EntityMentionVO> getMentionsByChapter(Long chapterId);

    /**
     * Get all entity profiles for a book.
     *
     * @param bookId the book ID
     * @return list of entity profile VOs
     */
    List<EntityProfileVO> getProfilesByBook(Long bookId);

    /**
     * Get a single entity profile by its ID.
     *
     * @param profileId the profile ID
     * @return the entity profile VO, or null if not found
     */
    EntityProfileVO getProfile(Long profileId);

    /**
     * Get all alias decisions for a book.
     *
     * @param bookId the book ID
     * @return list of alias decision VOs
     */
    List<AliasDecisionVO> getDecisionsByBook(Long bookId);

    /**
     * Get the deduplicated entity view for a chapter (no cross-chapter pollution).
     *
     * @param chapterId the chapter ID
     * @return chapter-scoped entity view
     */
    ChapterEntityViewVO getEntityViewByChapter(Long chapterId);
}
