package com.achen.novelbridge.pojo.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateBookRequest {

    @NotBlank(message = "filePath is required")
    private String filePath;
}
