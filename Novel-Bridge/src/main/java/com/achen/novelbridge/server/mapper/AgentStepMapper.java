package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelAgentStep;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

@Mapper
public interface AgentStepMapper {

    @Insert("INSERT INTO novel_agent_step (agent_run_id, step_type, step_order, status, started_at, "
            + "completed_at, error_message, created_by, updated_by) "
            + "VALUES (#{agentRunId}, #{stepType}, #{stepOrder}, #{status}, #{startedAt}, "
            + "#{completedAt}, #{errorMessage}, #{createdBy}, #{updatedBy})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelAgentStep step);

    @Update("UPDATE novel_agent_step SET status = #{status}, completed_at = #{completedAt}, "
            + "error_message = #{errorMessage}, updated_at = NOW() WHERE id = #{id}")
    int update(NovelAgentStep step);

    @Select("SELECT * FROM novel_agent_step WHERE agent_run_id = #{agentRunId} ORDER BY step_order")
    List<NovelAgentStep> findByAgentRunIdOrderByStepOrder(@Param("agentRunId") Long agentRunId);

    @Delete("DELETE FROM novel_agent_step WHERE agent_run_id IN "
            + "(SELECT id FROM novel_agent_run WHERE book_id = #{bookId})")
    int deleteByBookId(@Param("bookId") Long bookId);

    @Delete("DELETE FROM novel_agent_step WHERE agent_run_id = #{agentRunId}")
    int deleteByAgentRunId(@Param("agentRunId") Long agentRunId);
}
