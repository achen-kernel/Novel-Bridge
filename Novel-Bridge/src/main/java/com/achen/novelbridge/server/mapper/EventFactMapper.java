package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelEventFact;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_event_fact table operations.
 */
@Mapper
public interface EventFactMapper {

    @Insert("INSERT INTO novel_event_fact (book_id, event_type, summary, participants_json, location, importance, "
            + "evidence_ids_json, first_chapter_id, last_chapter_id, status) "
            + "VALUES (#{bookId}, #{eventType}, #{summary}, #{participantsJson}, #{location}, #{importance}, "
            + "#{evidenceIdsJson}, #{firstChapterId}, #{lastChapterId}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelEventFact fact);

    @Select("SELECT * FROM novel_event_fact WHERE book_id = #{bookId} ORDER BY event_type")
    List<NovelEventFact> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_event_fact WHERE id = #{id}")
    NovelEventFact findById(Long id);

    @Select("SELECT * FROM novel_event_fact WHERE book_id = #{bookId} "
            + "AND participants_json LIKE CONCAT('%', #{participant}, '%') "
            + "ORDER BY event_type")
    List<NovelEventFact> findByParticipant(@Param("bookId") Long bookId, @Param("participant") String participant);
}
