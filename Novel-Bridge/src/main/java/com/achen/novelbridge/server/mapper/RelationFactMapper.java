package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelRelationFact;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_relation_fact table operations.
 */
@Mapper
public interface RelationFactMapper {

    @Insert("INSERT INTO novel_relation_fact (book_id, relation_type, relation_family, source_entity_id, target_entity_id, "
            + "source_entity_name, target_entity_name, polarity, confidence, strength, evidence_ids_json, "
            + "first_chapter_id, last_chapter_id, status) "
            + "VALUES (#{bookId}, #{relationType}, #{relationFamily}, #{sourceEntityId}, #{targetEntityId}, "
            + "#{sourceEntityName}, #{targetEntityName}, #{polarity}, #{confidence}, #{strength}, #{evidenceIdsJson}, "
            + "#{firstChapterId}, #{lastChapterId}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelRelationFact fact);

    @Select("SELECT * FROM novel_relation_fact WHERE book_id = #{bookId} ORDER BY relation_type")
    List<NovelRelationFact> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_relation_fact WHERE id = #{id}")
    NovelRelationFact findById(Long id);

    @Select("SELECT * FROM novel_relation_fact WHERE book_id = #{bookId} "
            + "AND (source_entity_name = #{entityName} OR target_entity_name = #{entityName}) "
            + "ORDER BY relation_type")
    List<NovelRelationFact> findByEntityName(@Param("bookId") Long bookId, @Param("entityName") String entityName);
}
