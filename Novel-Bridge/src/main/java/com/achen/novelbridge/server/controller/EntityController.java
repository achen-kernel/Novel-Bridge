package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.result.R;
import com.achen.novelbridge.pojo.vo.AliasDecisionVO;
import com.achen.novelbridge.pojo.vo.ChapterEntityViewVO;
import com.achen.novelbridge.pojo.vo.EntityMentionVO;
import com.achen.novelbridge.pojo.vo.EntityProfileVO;
import com.achen.novelbridge.server.service.EntityGovernanceService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * REST controller for entity governance queries.
 * <p>
 * Provides read access to entity mentions, profiles, and alias decisions
 * managed by the entity governance pipeline.
 * </p>
 *
 * @NB-ENTRYPOINT
 * @NB-EVIDENCE
 */
@RestController
@RequestMapping("/api")
public class EntityController {

    private final EntityGovernanceService entityGovernanceService;

    public EntityController(EntityGovernanceService entityGovernanceService) {
        this.entityGovernanceService = entityGovernanceService;
    }

    /**
     * Get all entity mentions for a book.
     *
     * @param bookId the book ID
     * @return list of entity mention VOs
     */
    @GetMapping("/books/{bookId}/mentions")
    public R<List<EntityMentionVO>> getMentionsByBook(@PathVariable Long bookId) {
        List<EntityMentionVO> mentions = entityGovernanceService.getMentionsByBook(bookId);
        return R.ok(mentions);
    }

    /**
     * Get all entity mentions for a chapter.
     *
     * @param chapterId the chapter ID
     * @return list of entity mention VOs
     */
    @GetMapping("/chapters/{chapterId}/mentions")
    public R<List<EntityMentionVO>> getMentionsByChapter(@PathVariable Long chapterId) {
        List<EntityMentionVO> mentions = entityGovernanceService.getMentionsByChapter(chapterId);
        return R.ok(mentions);
    }

    /**
     * Get all entity profiles for a book.
     *
     * @param bookId the book ID
     * @return list of entity profile VOs
     */
    @GetMapping("/books/{bookId}/profiles")
    public R<List<EntityProfileVO>> getProfilesByBook(@PathVariable Long bookId) {
        List<EntityProfileVO> profiles = entityGovernanceService.getProfilesByBook(bookId);
        return R.ok(profiles);
    }

    /**
     * Get a single entity profile by its ID.
     *
     * @param profileId the profile ID
     * @return the entity profile VO
     */
    @GetMapping("/entity-profiles/{profileId}")
    public R<EntityProfileVO> getProfile(@PathVariable Long profileId) {
        EntityProfileVO profile = entityGovernanceService.getProfile(profileId);
        if (profile == null) {
            return R.failed(404, "Entity profile not found");
        }
        return R.ok(profile);
    }

    /**
     * Get all alias decisions for a book.
     *
     * @param bookId the book ID
     * @return list of alias decision VOs
     */
    @GetMapping("/books/{bookId}/alias-decisions")
    public R<List<AliasDecisionVO>> getDecisionsByBook(@PathVariable Long bookId) {
        List<AliasDecisionVO> decisions = entityGovernanceService.getDecisionsByBook(bookId);
        return R.ok(decisions);
    }

    /**
     * Get the deduplicated entity view for a chapter (no cross-chapter pollution).
     *
     * @param chapterId the chapter ID
     * @return chapter-scoped entity view
     */
    @GetMapping("/chapters/{chapterId}/entity-view")
    public R<ChapterEntityViewVO> getEntityViewByChapter(@PathVariable Long chapterId) {
        ChapterEntityViewVO view = entityGovernanceService.getEntityViewByChapter(chapterId);
        return R.ok(view);
    }
}
