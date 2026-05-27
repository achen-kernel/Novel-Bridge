package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelEvalRun;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * MyBatis Mapper for novel_eval_run table operations.
 */
@Mapper
public interface EvalRunMapper {

    @Insert("INSERT INTO novel_eval_run (run_type, status, summary_json, started_at, completed_at) "
            + "VALUES (#{runType}, #{status}, #{summaryJson}, #{startedAt}, #{completedAt})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertRun(NovelEvalRun run);

    @Select("SELECT * FROM novel_eval_run WHERE id = #{id}")
    NovelEvalRun findById(Long id);

    @Select("SELECT * FROM novel_eval_run ORDER BY created_at DESC")
    List<NovelEvalRun> findAll();

    @Update("UPDATE novel_eval_run SET status = #{status}, summary_json = #{summaryJson}, completed_at = NOW() WHERE id = #{id}")
    int updateStatus(@Param("id") Long id, @Param("status") String status, @Param("summaryJson") String summaryJson);
}
