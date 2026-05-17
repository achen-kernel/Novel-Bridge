package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelBookSource;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Optional;

@Mapper
public interface BookSourceMapper {

    @Insert("INSERT INTO novel_book_source (book_id, title, author, source_filename, file_type, "
            + "file_size, content_hash, raw_text, encoding, status, error_message, "
            + "created_by, updated_by) "
            + "VALUES (#{bookId}, #{title}, #{author}, #{sourceFilename}, #{fileType}, "
            + "#{fileSize}, #{contentHash}, #{rawText}, #{encoding}, #{status}, #{errorMessage}, "
            + "#{createdBy}, #{updatedBy})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelBookSource source);

    @Select("SELECT * FROM novel_book_source WHERE id = #{id}")
    NovelBookSource findById(Long id);

    @Select("SELECT * FROM novel_book_source WHERE book_id = #{bookId} ORDER BY id DESC")
    List<NovelBookSource> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_book_source WHERE content_hash = #{hash} LIMIT 1")
    Optional<NovelBookSource> findByContentHash(String hash);

    @Select("SELECT * FROM novel_book_source ORDER BY id DESC")
    List<NovelBookSource> findAll();

    int update(NovelBookSource source);
}
