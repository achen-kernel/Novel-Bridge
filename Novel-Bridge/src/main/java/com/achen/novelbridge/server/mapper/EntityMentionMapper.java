package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelEntityMention;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * MyBatis Mapper for novel_entity_mention table operations.
 */
@Mapper
public interface EntityMentionMapper {

    @Insert("INSERT INTO novel_entity_mention (book_id, chapter_id, chunk_id, surface_text, normalized_name, "
            + "entity_type, mention_role, confidence, is_generic, do_not_merge_globally, "
            + "evidence_text, context_before, context_after, status) "
            + "VALUES (#{bookId}, #{chapterId}, #{chunkId}, #{surfaceText}, #{normalizedName}, "
            + "#{entityType}, #{mentionRole}, #{confidence}, #{isGeneric}, #{doNotMergeGlobally}, "
            + "#{evidenceText}, #{contextBefore}, #{contextAfter}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertMention(NovelEntityMention mention);

    @Select("SELECT * FROM novel_entity_mention WHERE book_id = #{bookId} ORDER BY chapter_id, chunk_id")
    List<NovelEntityMention> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_entity_mention WHERE chapter_id = #{chapterId} ORDER BY chunk_id")
    List<NovelEntityMention> findByChapterId(Long chapterId);

    @Select("SELECT * FROM novel_entity_mention WHERE book_id = #{bookId} AND surface_text = #{surfaceText}")
    List<NovelEntityMention> findBySurfaceText(@Param("bookId") Long bookId, @Param("surfaceText") String surfaceText);

    @Update("UPDATE novel_entity_mention SET status = #{status} WHERE id = #{id}")
    int updateStatus(@Param("id") Long id, @Param("status") String status);
}
