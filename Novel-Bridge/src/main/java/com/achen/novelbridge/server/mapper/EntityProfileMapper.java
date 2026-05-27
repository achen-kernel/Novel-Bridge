package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelEntityProfile;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * MyBatis Mapper for novel_entity_profile table operations.
 */
@Mapper
public interface EntityProfileMapper {

    @Insert("INSERT INTO novel_entity_profile (book_id, canonical_name, entity_type, description, "
            + "aliases_json, first_chapter_id, last_chapter_id, mention_count, source, status) "
            + "VALUES (#{bookId}, #{canonicalName}, #{entityType}, #{description}, "
            + "#{aliasesJson}, #{firstChapterId}, #{lastChapterId}, #{mentionCount}, #{source}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertProfile(NovelEntityProfile profile);

    @Select("SELECT * FROM novel_entity_profile WHERE id = #{id}")
    NovelEntityProfile findById(Long id);

    @Select("SELECT * FROM novel_entity_profile WHERE book_id = #{bookId} ORDER BY canonical_name")
    List<NovelEntityProfile> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_entity_profile WHERE book_id = #{bookId} AND canonical_name = #{name}")
    NovelEntityProfile findByCanonicalName(@Param("bookId") Long bookId, @Param("name") String name);

    @Update("UPDATE novel_entity_profile SET description = #{description}, updated_at = NOW() WHERE id = #{id}")
    int updateDescription(@Param("id") Long id, @Param("description") String description);
}
