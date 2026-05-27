package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelChunk;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_chunk table operations.
 */
@Mapper
public interface ChunkMapper {

    @Select("SELECT * FROM novel_chunk WHERE chapter_id = #{chapterId} ORDER BY chunk_index")
    List<NovelChunk> findByChapterId(Long chapterId);

    @Select("SELECT * FROM novel_chunk WHERE id = #{id}")
    NovelChunk findById(Long id);
}
