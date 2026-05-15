package com.achen.novelbridge.common.result;

import lombok.Data;

/**
 * Unified API response model.
 * <p>
 * All controllers should return {@code Result<T>} instead of raw entities or {@code ResponseEntity}.
 * The frontend can handle all responses uniformly based on code + msg.
 */
@Data
public class Result<T> {

    private int code;
    private String msg;
    private T data;

    private Result() {}

    private Result(int code, String msg, T data) {
        this.code = code;
        this.msg = msg;
        this.data = data;
    }

    public static <T> Result<T> success(T data) {
        return new Result<>(1, "success", data);
    }

    public static <T> Result<T> success() {
        return new Result<>(1, "success", null);
    }

    public static <T> Result<T> error(String msg) {
        return new Result<>(0, msg, null);
    }

    public static <T> Result<T> error(int code, String msg) {
        return new Result<>(code, msg, null);
    }
}
