package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelChatMessage;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_chat_message table operations.
 */
@Mapper
public interface ChatMessageMapper {

    @Insert("INSERT INTO novel_chat_message (session_id, book_id, role, content, message_index, model_call_id) "
            + "VALUES (#{sessionId}, #{bookId}, #{role}, #{content}, #{messageIndex}, #{modelCallId})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertMessage(NovelChatMessage message);

    @Select("SELECT * FROM novel_chat_message WHERE session_id = #{sessionId} ORDER BY message_index ASC")
    List<NovelChatMessage> findBySessionId(@Param("sessionId") Long sessionId);

    @Select("SELECT * FROM novel_chat_message WHERE id = #{id}")
    NovelChatMessage findById(Long id);
}
