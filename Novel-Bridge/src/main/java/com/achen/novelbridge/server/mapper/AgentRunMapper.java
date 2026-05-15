package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelAgentRun;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

@Mapper
public interface AgentRunMapper {

    @Insert("INSERT INTO novel_agent_run (run_type, book_id, status, started_at, completed_at, "
            + "error_message, created_by, updated_by) "
            + "VALUES (#{runType}, #{bookId}, #{status}, #{startedAt}, #{completedAt}, "
            + "#{errorMessage}, #{createdBy}, #{updatedBy})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelAgentRun run);

    @Update("UPDATE novel_agent_run SET status = #{status}, completed_at = #{completedAt}, "
            + "error_message = #{errorMessage}, updated_at = NOW() WHERE id = #{id}")
    int update(NovelAgentRun run);

    @Select("SELECT * FROM novel_agent_run WHERE book_id = #{bookId} ORDER BY created_at DESC")
    List<NovelAgentRun> findByBookIdOrderByCreatedAtDesc(@Param("bookId") Long bookId);

    @Delete("DELETE FROM novel_agent_run WHERE book_id = #{bookId}")
    int deleteByBookId(@Param("bookId") Long bookId);
}
