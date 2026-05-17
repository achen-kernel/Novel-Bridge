package com.achen.novelbridge.server.service.impl;

import com.achen.novelbridge.common.enums.BookStatus;
import com.achen.novelbridge.common.enums.RunType;
import com.achen.novelbridge.common.enums.StepType;
import com.achen.novelbridge.common.properties.RagAgentProperties;
import com.achen.novelbridge.pojo.entity.NovelAgentRun;
import com.achen.novelbridge.pojo.entity.NovelAgentStep;
import com.achen.novelbridge.pojo.entity.NovelBook;
import com.achen.novelbridge.pojo.entity.NovelBookSource;
import com.achen.novelbridge.server.mapper.BookMapper;
import com.achen.novelbridge.server.mapper.BookSourceMapper;
import com.achen.novelbridge.server.service.IAgentRunService;
import com.achen.novelbridge.server.service.IBookSourceService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.Charset;
import java.nio.charset.CharsetDecoder;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;

/**
 * Handles book upload to remote MySQL via SSH tunnel,
 * and triggers remote rag-agent for downstream processing.
 * <p>
 * MOCK/DEBT: Default project (id=1), no auth. UTF-8 encoding assumed.
 */
@Slf4j
@Service
public class BookSourceServiceImpl implements IBookSourceService {

    private final BookSourceMapper bookSourceMapper;
    private final BookMapper bookMapper;
    private final IAgentRunService agentRunService;
    private final RagAgentProperties ragAgentProperties;

    public BookSourceServiceImpl(BookSourceMapper bookSourceMapper,
                                  BookMapper bookMapper,
                                  IAgentRunService agentRunService,
                                  RagAgentProperties ragAgentProperties) {
        this.bookSourceMapper = bookSourceMapper;
        this.bookMapper = bookMapper;
        this.agentRunService = agentRunService;
        this.ragAgentProperties = ragAgentProperties;
    }

    @Override
    @Transactional
    public NovelBookSource uploadAndTrigger(MultipartFile file, String title, String author, String encoding) {
        // ---- Validate ----
        if (file.isEmpty()) {
            throw new IllegalArgumentException("Uploaded file is empty");
        }

        String filename = file.getOriginalFilename();
        if (filename == null || filename.isBlank()) {
            filename = "unknown.txt";
        }

        String ext = parseExtension(filename);
        String bookTitle = resolveTitle(title, filename, ext);
        String bookAuthor = (author != null && !author.isBlank()) ? author : null;

        // ---- Read file bytes ----
        byte[] fileBytes = readFileBytes(file);
        String contentHash = sha256Hex(fileBytes);

        // ---- Auto-detect encoding: try UTF-8 first, fallback to GB18030 ----
        String fileEncoding = (encoding != null && !encoding.isBlank()) ? encoding : detectEncoding(fileBytes);
        String rawText = new String(fileBytes, Charset.forName(fileEncoding));
        log.info("Uploading '{}' ({} bytes, encoding={}, hash={})", bookTitle, fileBytes.length, fileEncoding, contentHash);

        // ---- Check duplicate ----
        java.util.Optional<NovelBookSource> existing = bookSourceMapper.findByContentHash(contentHash);
        if (existing.isPresent()) {
            log.warn("Duplicate upload detected: hash={}, existing source_id={}", contentHash, existing.get().getId());
            throw new IllegalArgumentException("File already uploaded (source_id=" + existing.get().getId()
                    + ", title=" + existing.get().getTitle() + ")");
        }

        // ---- Create novel_book ----
        NovelBook book = new NovelBook();
        book.setProjectId(1L); // MOCK: default project
        book.setTitle(bookTitle);
        book.setAuthor(bookAuthor);
        book.setSourceFilename(filename);
        book.setSourcePath("upload://" + filename);
        book.setFileSize((long) fileBytes.length);
        book.setFileType(ext);
        book.setStatus(BookStatus.IMPORTED);
        book.setCreatedBy("SYSTEM");
        bookMapper.insert(book);
        log.info("Created novel_book id={}", book.getId());

        // ---- Create novel_book_source ----
        NovelBookSource source = new NovelBookSource();
        source.setBookId(book.getId());
        source.setTitle(bookTitle);
        source.setAuthor(bookAuthor);
        source.setSourceFilename(filename);
        source.setFileType(ext);
        source.setFileSize((long) fileBytes.length);
        source.setContentHash(contentHash);
        source.setRawText(rawText);
        source.setEncoding(fileEncoding);
        source.setStatus("UPLOADED");
        source.setCreatedBy("SYSTEM");
        bookSourceMapper.insert(source);
        log.info("Created novel_book_source id={}", source.getId());

        // ---- AgentRun ----
        NovelAgentRun run = agentRunService.createRun(RunType.BOOK_UPLOAD, book.getId());
        int order = 0;

        try {
            NovelAgentStep stepUpload = agentRunService.startStep(run, StepType.UPLOAD_FILE, order++);
            agentRunService.completeStep(stepUpload);

            NovelAgentStep stepTrigger = agentRunService.startStep(run, StepType.TRIGGER_REMOTE_BUILD, order);
            triggerRemoteBuild(source.getId());
            agentRunService.completeStep(stepTrigger);

            source.setStatus("TRIGGERED");
            bookSourceMapper.update(source);
            agentRunService.completeRun(run);
            log.info("Upload+trigger OK source_id={}", source.getId());

        } catch (Exception e) {
            log.error("Upload/trigger failed source_id={}: {}", source.getId(), e.getMessage());
            source.setStatus("TRIGGER_FAILED");
            source.setErrorMessage(e.getMessage());
            bookSourceMapper.update(source);
            agentRunService.failRun(run, e.getMessage());
        }

        return source;
    }

    // ---- Remote trigger ----

    private void triggerRemoteBuild(Long sourceId) {
        String url = ragAgentProperties.getBaseUrl() + "/build?source_id=" + sourceId;
        log.info("Triggering rag-agent: POST {}", url);

        HttpClient client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(ragAgentProperties.getTimeoutMs()))
                .build();

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofMillis(ragAgentProperties.getTimeoutMs()))
                .POST(HttpRequest.BodyPublishers.noBody())
                .build();

        try {
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 200 && response.statusCode() < 300) {
                log.info("rag-agent responded {}: {}", response.statusCode(), response.body());
            } else {
                String msg = String.format("rag-agent returned HTTP %d: %s",
                        response.statusCode(), response.body());
                throw new IllegalStateException(msg);
            }
        } catch (IOException e) {
            throw new IllegalStateException("Cannot reach rag-agent at " + url + ": " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Trigger interrupted", e);
        }
    }

    // ---- Helpers ----

    private String parseExtension(String filename) {
        int dot = filename.lastIndexOf('.');
        return (dot > 0) ? filename.substring(dot + 1).toLowerCase() : "";
    }

    private String resolveTitle(String title, String filename, String ext) {
        if (title != null && !title.isBlank()) return title;
        int dot = filename.lastIndexOf('.');
        return (dot > 0) ? filename.substring(0, dot) : filename;
    }

    private byte[] readFileBytes(MultipartFile file) {
        try {
            return file.getBytes();
        } catch (IOException e) {
            throw new IllegalStateException("Failed to read uploaded file: " + e.getMessage(), e);
        }
    }

    private String sha256Hex(byte[] data) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(data);
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }

    /**
     * Auto-detect file encoding: try UTF-8 first, fallback to GB18030.
     * Uses CharsetDecoder to validate whether bytes are valid UTF-8.
     */
    private String detectEncoding(byte[] bytes) {
        // Check for UTF-8 BOM (EF BB BF)
        if (bytes.length >= 3 && (bytes[0] & 0xFF) == 0xEF
                && (bytes[1] & 0xFF) == 0xBB && (bytes[2] & 0xFF) == 0xBF) {
            return "UTF-8";
        }
        // Try to decode as UTF-8, report if any byte is malformed
        CharsetDecoder decoder = StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT);
        try {
            decoder.decode(ByteBuffer.wrap(bytes));
            return "UTF-8";
        } catch (CharacterCodingException e) {
            // Not valid UTF-8, fallback to GB18030 (covers GBK)
            log.info("File is not valid UTF-8, detected as GB18030");
            return "GB18030";
        }
    }
}
