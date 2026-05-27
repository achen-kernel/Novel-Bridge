package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelRelationMention;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_relation_mention table operations.
 */
@Mapper
public interface RelationMentionMapper {

    @Insert("INSERT INTO novel_relation_mention (book_id, chapter_id, chunk_id, source_entity_name, target_entity_name, "
            + "relation_type, relation_family, relation_polarity, direction, evidence_text, relation_trigger, "
            + "confidence, status) "
            + "VALUES (#{bookId}, #{chapterId}, #{chunkId}, #{sourceEntityName}, #{targetEntityName}, "
            + "#{relationType}, #{relationFamily}, #{relationPolarity}, #{direction}, #{evidenceText}, #{relationTrigger}, "
            + "#{confidence}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelRelationMention mention);

    @Select("SELECT * FROM novel_relation_mention WHERE book_id = #{bookId} ORDER BY chapter_id, chunk_id")
    List<NovelRelationMention> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_relation_mention WHERE chapter_id = #{chapterId} ORDER BY chunk_id")
    List<NovelRelationMention> findByChapterId(Long chapterId);
}
