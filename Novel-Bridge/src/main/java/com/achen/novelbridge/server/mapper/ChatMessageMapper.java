package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelChatMessage;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ChatMessageMapper {

    @Insert("INSERT INTO novel_chat_message (session_id, role, content, message_index, created_by, updated_by) "
            + "VALUES (#{sessionId}, #{role}, #{content}, #{messageIndex}, #{createdBy}, #{updatedBy})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelChatMessage message);

    @Select("SELECT * FROM novel_chat_message WHERE session_id = #{sessionId} ORDER BY message_index")
    List<NovelChatMessage> findBySessionIdOrderByMessageIndex(@Param("sessionId") Long sessionId);
}
