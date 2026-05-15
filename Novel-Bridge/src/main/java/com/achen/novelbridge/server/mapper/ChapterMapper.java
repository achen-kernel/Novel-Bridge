package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelChapter;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ChapterMapper {

    @Insert("INSERT INTO novel_chapter (book_id, chapter_number, title, raw_content, cleaned_content, "
            + "char_count, status, error_message, created_by, updated_by) "
            + "VALUES (#{bookId}, #{chapterNumber}, #{title}, #{rawContent}, #{cleanedContent}, "
            + "#{charCount}, #{status}, #{errorMessage}, #{createdBy}, #{updatedBy})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelChapter chapter);

    @Select("SELECT * FROM novel_chapter WHERE book_id = #{bookId} ORDER BY chapter_number")
    List<NovelChapter> findByBookIdOrderByChapterNumber(@Param("bookId") Long bookId);
}
