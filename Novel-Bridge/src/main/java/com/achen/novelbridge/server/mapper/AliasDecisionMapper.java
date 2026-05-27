package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelAliasDecision;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_alias_decision table operations.
 */
@Mapper
public interface AliasDecisionMapper {

    @Insert("INSERT INTO novel_alias_decision (book_id, entity_a_name, entity_b_name, decision, "
            + "confidence, reason, risk_types_json, reviewer) "
            + "VALUES (#{bookId}, #{entityAName}, #{entityBName}, #{decision}, "
            + "#{confidence}, #{reason}, #{riskTypesJson}, #{reviewer})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertDecision(NovelAliasDecision decision);

    @Select("SELECT * FROM novel_alias_decision WHERE book_id = #{bookId} ORDER BY created_at DESC")
    List<NovelAliasDecision> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_alias_decision WHERE decision = #{decision} ORDER BY created_at DESC")
    List<NovelAliasDecision> findByDecision(@Param("decision") String decision);
}
