package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelChatSession;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ChatSessionMapper {

    @Insert("INSERT INTO novel_chat_session (book_id, user_id, title, status, created_by, updated_by) "
            + "VALUES (#{bookId}, #{userId}, #{title}, #{status}, #{createdBy}, #{updatedBy})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelChatSession session);

    @Select("SELECT * FROM novel_chat_session WHERE id = #{id}")
    NovelChatSession findById(@Param("id") Long id);

    @Select("SELECT * FROM novel_chat_session WHERE book_id = #{bookId} ORDER BY created_at DESC")
    List<NovelChatSession> findByBookIdOrderByCreatedAtDesc(@Param("bookId") Long bookId);
}
