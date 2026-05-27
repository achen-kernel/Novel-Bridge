package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelChapterFact;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * MyBatis Mapper for novel_chapter_fact table operations.
 */
@Mapper
public interface ChapterFactMapper {

    @Insert("INSERT INTO novel_chapter_fact (book_id, chapter_id, model_call_id, fact_json, evidence_json, summary, "
            + "parse_status, evidence_status, review_status, quality_flags_json, status, error_message) "
            + "VALUES (#{bookId}, #{chapterId}, #{modelCallId}, #{factJson}, #{evidenceJson}, #{summary}, "
            + "#{parseStatus}, #{evidenceStatus}, #{reviewStatus}, #{qualityFlagsJson}, #{status}, #{errorMessage})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertFact(NovelChapterFact fact);

    @Select("SELECT * FROM novel_chapter_fact WHERE id = #{id}")
    NovelChapterFact findById(Long id);

    @Select("SELECT * FROM novel_chapter_fact WHERE book_id = #{bookId} ORDER BY chapter_id")
    List<NovelChapterFact> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_chapter_fact WHERE chapter_id = #{chapterId}")
    List<NovelChapterFact> findByChapterId(Long chapterId);

    @Update("UPDATE novel_chapter_fact SET review_status = #{reviewStatus}, updated_at = NOW() WHERE id = #{id}")
    int updateReviewStatus(@Param("id") Long id, @Param("reviewStatus") String reviewStatus);
}
