package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelEvalCase;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_eval_case table operations.
 */
@Mapper
public interface EvalCaseMapper {

    @Insert("INSERT INTO novel_eval_case (book_id, question, expected_answer, expected_entities_json, category, difficulty, status) "
            + "VALUES (#{bookId}, #{question}, #{expectedAnswer}, #{expectedEntitiesJson}, #{category}, #{difficulty}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertCase(NovelEvalCase evalCase);

    @Select("SELECT * FROM novel_eval_case ORDER BY created_at DESC")
    List<NovelEvalCase> findAll();

    @Select("SELECT * FROM novel_eval_case WHERE book_id = #{bookId} ORDER BY created_at DESC")
    List<NovelEvalCase> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_eval_case WHERE category = #{category} ORDER BY created_at DESC")
    List<NovelEvalCase> findByCategory(@Param("category") String category);
}
