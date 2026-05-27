package com.achen.novelbridge.common.exception;

import com.achen.novelbridge.common.result.ResultCode;

/**
 * Custom runtime exception carrying a business error code and message.
 */
public class BusinessException extends RuntimeException {

    private final int code;

    public BusinessException(int code, String message) {
        super(message);
        this.code = code;
    }

    public BusinessException(ResultCode resultCode) {
        super(resultCode.getMessage());
        this.code = resultCode.getCode();
    }

    public int getCode() {
        return code;
    }
}
