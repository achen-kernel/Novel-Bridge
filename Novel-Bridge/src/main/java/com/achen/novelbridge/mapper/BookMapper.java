package com.achen.novelbridge.mapper;

import com.achen.novelbridge.pojo.entity.NovelBook;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface BookMapper extends JpaRepository<NovelBook, Long> {
}
