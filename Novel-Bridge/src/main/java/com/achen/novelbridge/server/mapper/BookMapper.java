package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelBook;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Optional;

@Mapper
public interface BookMapper {

    @Insert("INSERT INTO novel_book (project_id, folder_id, title, author, source_filename, source_path, "
            + "file_size, file_type, total_chapters, total_chunks, status, error_message, "
            + "created_by, updated_by) "
            + "VALUES (#{projectId}, #{folderId}, #{title}, #{author}, #{sourceFilename}, #{sourcePath}, "
            + "#{fileSize}, #{fileType}, #{totalChapters}, #{totalChunks}, #{status}, #{errorMessage}, "
            + "#{createdBy}, #{updatedBy})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelBook book);

    @Select("SELECT * FROM novel_book WHERE id = #{id}")
    NovelBook findById(Long id);

    @Select("SELECT * FROM novel_book ORDER BY id DESC")
    List<NovelBook> findAll();

    @Delete("DELETE FROM novel_book WHERE id = #{id}")
    int deleteById(Long id);

    int update(NovelBook book);
}
