package com.achen.novelbridge.server.controller;

import com.achen.novelbridge.common.result.R;
import com.achen.novelbridge.pojo.vo.BookUploadVO;
import com.achen.novelbridge.pojo.vo.BookVO;
import com.achen.novelbridge.server.service.BookService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * REST controller for book upload and retrieval endpoints.
 * <p>
 * Stage 2: Book upload with encoding detection, hash dedup, and async Python processing trigger.
 * </p>
 *
 * @NB-ENTRYPOINT
 * @NB-ROADMAP
 */
@RestController
@RequestMapping("/api/books")
public class BookController {

    private final BookService bookService;

    public BookController(BookService bookService) {
        this.bookService = bookService;
    }

    /**
     * Upload one or more TXT book files merged into a single book.
     * <p>
     * Accepts multipart form data with multiple files and optional metadata.
     * Files are concatenated in order with a double newline separator.
     * </p>
     *
     * @param files    the uploaded TXT files (required, at least one)
     * @param encoding optional source encoding hint (auto-detected if omitted)
     * @param title    optional book title (inferred from first filename if omitted)
     * @param author   optional author name
     * @return upload result with book ID and processing status
     */
    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public R<BookUploadVO> upload(
            @RequestParam("files") MultipartFile[] files,
            @RequestParam(value = "encoding", required = false) String encoding,
            @RequestParam(value = "title", required = false) String title,
            @RequestParam(value = "author", required = false) String author
    ) {
        if (files == null || files.length == 0) {
            return R.failed(400, "At least one file is required");
        }
        BookUploadVO result = bookService.uploadBook(files, encoding, title, author);
        return R.ok(result);
    }

    /**
     * Get book details by ID.
     *
     * @param id book ID
     * @return book details
     */
    @GetMapping("/{id}")
    public R<BookVO> getBook(@PathVariable Long id) {
        BookVO book = bookService.getBook(id);
        return R.ok(book);
    }

    /**
     * Get book processing status by ID.
     *
     * @param id book ID
     * @return book status details
     */
    @GetMapping("/{id}/status")
    public R<BookVO> getBookStatus(@PathVariable Long id) {
        BookVO book = bookService.getBook(id);
        return R.ok(book);
    }
}
