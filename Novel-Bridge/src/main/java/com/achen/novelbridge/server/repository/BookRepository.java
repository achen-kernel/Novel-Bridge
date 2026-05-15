package com.achen.novelbridge.server.repository;

import com.achen.novelbridge.pojo.entity.NovelBook;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface BookRepository extends JpaRepository<NovelBook, Long> {
}
