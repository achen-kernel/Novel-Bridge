package com.achen.novelbridge.common.properties;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Maps novel-bridge.books.* configuration from application.yml.
 */
@Data
@Component
@ConfigurationProperties(prefix = "novel-bridge.books")
public class BooksProperties {

    /** Base directory for book source files. */
    private String baseDir;

    public Path getBaseDirPath() {
        return Paths.get(baseDir).toAbsolutePath().normalize();
    }
}
