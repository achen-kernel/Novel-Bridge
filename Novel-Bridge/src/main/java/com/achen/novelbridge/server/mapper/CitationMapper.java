package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelCitation;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_citation table operations.
 */
@Mapper
public interface CitationMapper {

    @Insert("INSERT INTO novel_citation (message_id, book_id, source_type, source_id, chapter_id, chunk_id, chapter_fact_id, excerpt, start_offset, end_offset, relevance_score, evidence_level) "
            + "VALUES (#{messageId}, #{bookId}, #{sourceType}, #{sourceId}, #{chapterId}, #{chunkId}, #{chapterFactId}, #{excerpt}, #{startOffset}, #{endOffset}, #{relevanceScore}, #{evidenceLevel})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertCitation(NovelCitation citation);

    @Select("SELECT * FROM novel_citation WHERE message_id = #{messageId}")
    List<NovelCitation> findByMessageId(Long messageId);

    @Insert("<script>"
            + "INSERT INTO novel_citation (message_id, book_id, source_type, source_id, chapter_id, chunk_id, chapter_fact_id, excerpt, start_offset, end_offset, relevance_score, evidence_level) VALUES "
            + "<foreach collection='list' item='c' separator=','>"
            + "(#{c.messageId}, #{c.bookId}, #{c.sourceType}, #{c.sourceId}, #{c.chapterId}, #{c.chunkId}, #{c.chapterFactId}, #{c.excerpt}, #{c.startOffset}, #{c.endOffset}, #{c.relevanceScore}, #{c.evidenceLevel})"
            + "</foreach>"
            + "</script>")
    int insertBatch(List<NovelCitation> citations);
}
