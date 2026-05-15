package com.achen.novelbridge.mapper;

import com.achen.novelbridge.pojo.entity.NovelChapter;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ChapterMapper extends JpaRepository<NovelChapter, Long> {

    List<NovelChapter> findByBookIdOrderByChapterNumber(Long bookId);
}
