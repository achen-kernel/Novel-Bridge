package com.achen.novelbridge.common.result;

/**
 * Unified response status codes for NovelBridge API.
 *
 * @NB-ROADMAP
 */
public enum ResultCode {

    SUCCESS(200, "success"),
    BAD_REQUEST(400, "bad request"),
    CONFLICT(409, "conflict"),
    NOT_FOUND(404, "not found"),
    FAILED(500, "failed"),
    SERVICE_UNAVAILABLE(503, "service unavailable");

    private final int code;
    private final String message;

    ResultCode(int code, String message) {
        this.code = code;
        this.message = message;
    }

    public int getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }
}
