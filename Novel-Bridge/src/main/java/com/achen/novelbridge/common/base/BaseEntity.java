package com.achen.novelbridge.common.base;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

/**
 * Abstract base class for all entities.
 * <p>
 * MyBatis maps fields via SQL (no JPA annotations).
 * created_at / updated_at use SQL DEFAULT + ON UPDATE in schema.
 * id is populated by MySQL AUTO_INCREMENT via @Options(useGeneratedKeys=true).
 */
@Getter
@Setter
public abstract class BaseEntity {

    private Long id;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private String createdBy;
    private String updatedBy;
}
