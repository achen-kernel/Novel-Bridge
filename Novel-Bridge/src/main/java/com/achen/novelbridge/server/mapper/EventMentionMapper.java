package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelEventMention;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_event_mention table operations.
 */
@Mapper
public interface EventMentionMapper {

    @Insert("INSERT INTO novel_event_mention (book_id, chapter_id, chunk_id, event_type, summary, "
            + "participants_json, location, time_hint, event_trigger, evidence_text, importance, confidence, status) "
            + "VALUES (#{bookId}, #{chapterId}, #{chunkId}, #{eventType}, #{summary}, "
            + "#{participantsJson}, #{location}, #{timeHint}, #{eventTrigger}, #{evidenceText}, #{importance}, #{confidence}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelEventMention mention);

    @Select("SELECT * FROM novel_event_mention WHERE book_id = #{bookId} ORDER BY chapter_id, chunk_id")
    List<NovelEventMention> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_event_mention WHERE chapter_id = #{chapterId} ORDER BY chunk_id")
    List<NovelEventMention> findByChapterId(Long chapterId);
}
