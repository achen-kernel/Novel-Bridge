package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelChapter;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_chapter table operations.
 */
@Mapper
public interface ChapterMapper {

    @Select("SELECT * FROM novel_chapter WHERE book_id = #{bookId} ORDER BY chapter_number")
    List<NovelChapter> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_chapter WHERE id = #{id}")
    NovelChapter findById(Long id);
}
