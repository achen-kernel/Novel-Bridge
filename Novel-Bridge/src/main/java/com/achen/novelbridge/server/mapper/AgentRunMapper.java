package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelAgentRun;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

/**
 * MyBatis Mapper for novel_agent_run table operations.
 */
@Mapper
public interface AgentRunMapper {

    @Insert("INSERT INTO novel_agent_run (run_type, book_id, status, input_json, output_json, error_type, error_message, started_at, completed_at) "
            + "VALUES (#{runType}, #{bookId}, #{status}, #{inputJson}, #{outputJson}, #{errorType}, #{errorMessage}, #{startedAt}, #{completedAt})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertAgentRun(NovelAgentRun run);

    @Select("SELECT * FROM novel_agent_run WHERE id = #{id}")
    NovelAgentRun findById(Long id);

    @Update("UPDATE novel_agent_run SET status = #{status}, output_json = #{outputJson}, error_type = #{errorType}, "
            + "error_message = #{errorMessage}, completed_at = #{completedAt}, updated_at = NOW() WHERE id = #{id}")
    int updateStatus(@Param("id") Long id,
                     @Param("status") String status,
                     @Param("outputJson") String outputJson,
                     @Param("errorType") String errorType,
                     @Param("errorMessage") String errorMessage,
                     @Param("completedAt") java.time.LocalDateTime completedAt);
}
