package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelBook;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

/**
 * MyBatis Mapper for novel_book table operations.
 */
@Mapper
public interface BookMapper {

    @Insert("INSERT INTO novel_book (title, author, language, source_file_name, source_encoding, source_hash, raw_text, char_count, chapter_count, chunk_count, status, error_message) "
            + "VALUES (#{title}, #{author}, #{language}, #{sourceFileName}, #{sourceEncoding}, #{sourceHash}, #{rawText}, #{charCount}, #{chapterCount}, #{chunkCount}, #{status}, #{errorMessage})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertBook(NovelBook book);

    @Select("SELECT * FROM novel_book WHERE id = #{id}")
    NovelBook findById(Long id);

    @Select("SELECT * FROM novel_book WHERE source_hash = #{sourceHash}")
    NovelBook findBySourceHash(String sourceHash);

    @Update("UPDATE novel_book SET status = #{status}, error_message = #{errorMessage}, updated_at = NOW() WHERE id = #{id}")
    int updateStatus(@Param("id") Long id, @Param("status") String status, @Param("errorMessage") String errorMessage);
}
