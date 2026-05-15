package com.achen.novelbridge.mapper;

import com.achen.novelbridge.pojo.entity.NovelAgentRun;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AgentRunMapper extends JpaRepository<NovelAgentRun, Long> {

    List<NovelAgentRun> findByBookIdOrderByCreatedAtDesc(Long bookId);
}
