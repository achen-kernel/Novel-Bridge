package com.achen.novelbridge.server.mapper;

import com.achen.novelbridge.pojo.entity.NovelPlotStage;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * MyBatis Mapper for novel_plot_stage table operations.
 */
@Mapper
public interface PlotStageMapper {

    @Insert("INSERT INTO novel_plot_stage (book_id, stage_index, stage_name, summary, start_chapter_id, end_chapter_id, "
            + "key_entities_json, status) "
            + "VALUES (#{bookId}, #{stageIndex}, #{stageName}, #{summary}, #{startChapterId}, #{endChapterId}, "
            + "#{keyEntitiesJson}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(NovelPlotStage plotStage);

    @Select("SELECT * FROM novel_plot_stage WHERE book_id = #{bookId} ORDER BY stage_index")
    List<NovelPlotStage> findByBookId(Long bookId);

    @Select("SELECT * FROM novel_plot_stage WHERE id = #{id}")
    NovelPlotStage findById(Long id);
}
