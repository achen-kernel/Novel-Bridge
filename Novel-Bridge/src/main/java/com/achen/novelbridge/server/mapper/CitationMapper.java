package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelCitation;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface CitationMapper {

    @Insert("INSERT INTO novel_citation (message_id, source_type, source_id, chapter_id, chunk_id, fact_id, "
            + "relevance_score, excerpt, created_by, updated_by) "
            + "VALUES (#{messageId}, #{sourceType}, #{sourceId}, #{chapterId}, #{chunkId}, #{factId}, "
            + "#{relevanceScore}, #{excerpt}, #{createdBy}, #{updatedBy})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelCitation citation);

    @Insert({
        "<script>",
        "INSERT INTO novel_citation (message_id, source_type, source_id, chapter_id, chunk_id, fact_id, ",
        "relevance_score, excerpt, created_by, updated_by) VALUES ",
        "<foreach collection='list' item='c' separator=','>",
        "(#{c.messageId}, #{c.sourceType}, #{c.sourceId}, #{c.chapterId}, #{c.chunkId}, #{c.factId}, ",
        "#{c.relevanceScore}, #{c.excerpt}, #{c.createdBy}, #{c.updatedBy})",
        "</foreach>",
        "</script>"
    })
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertBatch(@Param("list") List<NovelCitation> citations);

    @Select("SELECT * FROM novel_citation WHERE message_id = #{messageId}")
    List<NovelCitation> findByMessageId(@Param("messageId") Long messageId);
}
