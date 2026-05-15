package com.achen.novelbridge.pojo.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CreateSessionRequest {

    @NotNull
    private Long bookId;

    private String title;
}
