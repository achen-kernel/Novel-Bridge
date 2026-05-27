package com.achen.novelbridge.server.service;

import com.achen.novelbridge.pojo.vo.BookUploadVO;
import com.achen.novelbridge.pojo.vo.BookVO;
import org.springframework.web.multipart.MultipartFile;

/**
 * Service interface for book upload and retrieval operations.
 */
public interface BookService {

    /**
     * Upload one or more book files, detect encoding per file, compute combined hash,
     * store merged raw text, and trigger async Python processing.
     *
     * @param files    uploaded TXT files (merged into one book)
     * @param encoding optional encoding hint (auto-detected if null)
     * @param title    optional title (inferred from first filename if null)
     * @param author   optional author
     * @return upload result with book ID and processing status
     */
    BookUploadVO uploadBook(MultipartFile[] files, String encoding, String title, String author);

    /**
     * Retrieve book details by ID.
     *
     * @param id book ID
     * @return book view object
     */
    BookVO getBook(Long id);
}
