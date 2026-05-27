package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelEvalResult;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_eval_result table operations.
 */
@Mapper
public interface EvalResultMapper {

    @Insert("INSERT INTO novel_eval_result (run_id, case_id, question, actual_answer, citations_json, scores_json, error_type, error_message, status) "
            + "VALUES (#{runId}, #{caseId}, #{question}, #{actualAnswer}, #{citationsJson}, #{scoresJson}, #{errorType}, #{errorMessage}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertResult(NovelEvalResult result);

    @Select("SELECT * FROM novel_eval_result WHERE run_id = #{runId} ORDER BY id")
    List<NovelEvalResult> findByRunId(Long runId);

    @Select("SELECT * FROM novel_eval_result WHERE status = #{status} ORDER BY id")
    List<NovelEvalResult> findByStatus(@Param("status") String status);
}
