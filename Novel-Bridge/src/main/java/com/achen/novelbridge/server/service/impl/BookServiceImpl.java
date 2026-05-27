package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.common.exception.BusinessException;
import com.achen.novelbridge.common.result.ResultCode;
import com.achen.novelbridge.pojo.entity.NovelBook;
import com.achen.novelbridge.pojo.vo.BookUploadVO;
import com.achen.novelbridge.pojo.vo.BookVO;
import com.achen.novelbridge.server.mapper.BookMapper;
import com.achen.novelbridge.server.service.BookService;
import com.achen.novelbridge.server.service.RagAgentClientService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.charset.Charset;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Set;

/**
 * Implementation of {@link BookService} for book upload and retrieval.
 */
@Service
public class BookServiceImpl implements BookService {

    private static final Logger log = LoggerFactory.getLogger(BookServiceImpl.class);

    private static final byte[] UTF8_BOM = {(byte) 0xEF, (byte) 0xBB, (byte) 0xBF};

    private final BookMapper bookMapper;
    private final RagAgentClientService ragAgentClientService;

    public BookServiceImpl(BookMapper bookMapper,
                           RagAgentClientService ragAgentClientService) {
        this.bookMapper = bookMapper;
        this.ragAgentClientService = ragAgentClientService;
    }

    @Override
    public BookUploadVO uploadBook(MultipartFile[] files, String encoding, String title, String author) {
        if (files == null || files.length == 0) {
            throw new BusinessException(400, "At least one file is required");
        }

        // Aggregate across files
        StringBuilder allNames = new StringBuilder();
        StringBuilder allText = new StringBuilder();
        Set<String> encodings = new java.util.LinkedHashSet<>();
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new BusinessException(500, "SHA-256 not available: " + e.getMessage());
        }

        for (int i = 0; i < files.length; i++) {
            MultipartFile file = files[i];

            // 1. Read raw bytes
            byte[] rawBytes;
            try {
                rawBytes = file.getBytes();
            } catch (IOException e) {
                throw new BusinessException(500,
                        "Failed to read uploaded file '" + file.getOriginalFilename() + "': " + e.getMessage());
            }

            if (rawBytes.length == 0) {
                throw new BusinessException(400, "Uploaded file is empty: " + file.getOriginalFilename());
            }

            // Accumulate hash over all raw bytes (concatenation-equivalent)
            digest.update(rawBytes);

            // 4. Detect encoding per file
            String detectedEncoding = detectEncoding(rawBytes, encoding);
            log.info("Detected encoding: {} for file: {}", detectedEncoding, file.getOriginalFilename());
            encodings.add(detectedEncoding);

            // 5. Decode to string
            String rawText = decodeText(rawBytes, detectedEncoding);

            // Append text with separator
            if (i > 0) {
                allText.append("\n\n");
            }
            allText.append(rawText);

            // Collect file names
            if (i > 0) {
                allNames.append("; ");
            }
            allNames.append(file.getOriginalFilename() != null ? file.getOriginalFilename() : "unnamed_" + i);
        }

        // 2. Compute final SHA-256 over all concatenated raw bytes
        String sourceHash = HexFormat.of().formatHex(digest.digest());

        // 3. Check for duplicate by hash
        NovelBook existing = bookMapper.findBySourceHash(sourceHash);
        if (existing != null) {
            throw new BusinessException(ResultCode.CONFLICT.getCode(),
                    "Book already exists with id=" + existing.getId() + ", title=" + existing.getTitle());
        }

        String mergedText = allText.toString();
        String sourceEncoding = String.join("; ", encodings);
        String sourceFileName = allNames.toString();

        // 6. Build NovelBook entity
        NovelBook book = new NovelBook();
        book.setTitle(title != null && !title.isBlank() ? title : inferTitle(files[0]));
        book.setAuthor(author != null && !author.isBlank() ? author : "");
        book.setLanguage("zh");
        book.setSourceFileName(sourceFileName);
        book.setSourceEncoding(sourceEncoding);
        book.setSourceHash(sourceHash);
        book.setRawText(mergedText);
        book.setCharCount(mergedText.length());
        book.setChapterCount(0);
        book.setChunkCount(0);
        book.setStatus("IMPORTED");

        bookMapper.insertBook(book);
        log.info("Inserted book: id={}, title={}, hash={}, files={}",
                book.getId(), book.getTitle(), sourceHash, files.length);

        // 7. Asynchronously trigger Python processing (no AgentRun created here)
        ragAgentClientService.triggerBookProcessing(book.getId());

        // 8. Build response
        BookUploadVO vo = new BookUploadVO();
        vo.setBookId(book.getId());
        vo.setTitle(book.getTitle());
        vo.setStatus(book.getStatus());
        vo.setFileCount(files.length);
        vo.setCharCount(mergedText.length());
        vo.setMessage("Book uploaded successfully. Processing triggered.");
        return vo;
    }

    @Override
    public BookVO getBook(Long id) {
        NovelBook book = bookMapper.findById(id);
        if (book == null) {
            throw new BusinessException(ResultCode.NOT_FOUND.getCode(), "Book not found: " + id);
        }
        return toBookVO(book);
    }

    // ---- Private helpers ----

    private String detectEncoding(byte[] rawBytes, String hint) {
        // Protect against null or empty bytes
        if (rawBytes == null || rawBytes.length == 0) {
            return "UTF-8";
        }

        // Check for UTF-8 BOM first
        if (hasUtf8Bom(rawBytes)) {
            return "UTF-8";
        }

        // If hint provided and valid, use it
        if (hint != null && !hint.isBlank()) {
            if (isValidEncoding(rawBytes, hint)) {
                return hint;
            }
        }

        // Try UTF-8 (most common for Chinese text uploaded by this system)
        if (isValidEncoding(rawBytes, "UTF-8")) {
            return "UTF-8";
        }

        // Try GB18030 (superset of GBK)
        if (isValidEncoding(rawBytes, "GB18030")) {
            return "GB18030";
        }

        // Fallback to GBK (most common Chinese encoding after UTF-8)
        return "GBK";
    }

    private boolean hasUtf8Bom(byte[] bytes) {
        if (bytes.length < 3) return false;
        return bytes[0] == UTF8_BOM[0] && bytes[1] == UTF8_BOM[1] && bytes[2] == UTF8_BOM[2];
    }

    private boolean isValidEncoding(byte[] bytes, String charsetName) {
        if (bytes == null || bytes.length < 3) {
            return false;
        }
        try {
            String decoded = new String(bytes, charsetName);
            if (decoded.isEmpty()) {
                return false;
            }
            long replacementCount = decoded.chars().filter(c -> c == '\uFFFD').count();
            return (double) replacementCount / decoded.length() < 0.05;
        } catch (Exception e) {
            return false;
        }
    }

    private String decodeText(byte[] rawBytes, String encoding) {
        // Strip BOM if present
        int offset = hasUtf8Bom(rawBytes) ? 3 : 0;
        int length = rawBytes.length - offset;
        byte[] content = new byte[length];
        System.arraycopy(rawBytes, offset, content, 0, length);

        return new String(content, Charset.forName(encoding));
    }

    private String inferTitle(MultipartFile file) {
        String originalName = file.getOriginalFilename();
        if (originalName == null || originalName.isBlank()) {
            return "Untitled";
        }
        // Remove extension
        int dotIndex = originalName.lastIndexOf('.');
        if (dotIndex > 0) {
            return originalName.substring(0, dotIndex);
        }
        return originalName;
    }

    private BookVO toBookVO(NovelBook book) {
        BookVO vo = new BookVO();
        vo.setId(book.getId());
        vo.setTitle(book.getTitle());
        vo.setAuthor(book.getAuthor());
        vo.setLanguage(book.getLanguage());
        vo.setSourceEncoding(book.getSourceEncoding());
        vo.setCharCount(book.getCharCount());
        vo.setChapterCount(book.getChapterCount());
        vo.setChunkCount(book.getChunkCount());
        vo.setStatus(book.getStatus());
        vo.setErrorMessage(book.getErrorMessage());
        vo.setCreatedAt(book.getCreatedAt());
        return vo;
    }
}
