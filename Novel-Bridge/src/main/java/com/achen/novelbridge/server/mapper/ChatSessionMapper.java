package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelChatSession;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * MyBatis Mapper for novel_chat_session table operations.
 */
@Mapper
public interface ChatSessionMapper {

    @Insert("INSERT INTO novel_chat_session (book_id, title, status) VALUES (#{bookId}, #{title}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertSession(NovelChatSession session);

    @Select("SELECT * FROM novel_chat_session WHERE id = #{id}")
    NovelChatSession findById(Long id);

    @Select("SELECT * FROM novel_chat_session WHERE book_id = #{bookId} ORDER BY created_at DESC")
    List<NovelChatSession> findByBookId(Long bookId);

    @Update("UPDATE novel_chat_session SET status = #{status}, updated_at = NOW() WHERE id = #{id}")
    int updateStatus(@Param("id") Long id, @Param("status") String status);
}
