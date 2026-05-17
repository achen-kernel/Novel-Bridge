package com.achen.novelbridge.server.service;

import com.achen.novelbridge.pojo.entity.NovelBookSource;
import org.springframework.web.multipart.MultipartFile;

/**
 * Book upload and remote trigger service.
 * <p>
 * Demo 5B scope:
 * 1. Upload a TXT/book file → save to novel_book + novel_book_source
 * 2. Trigger remote rag-agent POST /build?source_id=X
 * 3. Track via AgentRun / AgentStep
 * <p>
 * Java does NOT do chapter splitting, chunking, or entity extraction.
 */
public interface IBookSourceService {

    /**
     * Upload a book file and trigger remote build.
     *
     * @param file   uploaded TXT file
     * @param title  optional title (falls back to filename)
     * @param author optional author
     * @return the created book_source record
     */
    NovelBookSource uploadAndTrigger(MultipartFile file, String title, String author, String encoding);
}
