package com.achen.novelbridge.common.exception;

/**
 * Base class for all business exceptions.
 * <p>
 * Extend this class for specific exception types.
 * Caught by {@link com.achen.novelbridge.common.handler.GlobalExceptionHandler}
 * and returned as {@link com.achen.novelbridge.common.result.Result#error(String)}.
 */
public class BaseException extends RuntimeException {

    public BaseException(String message) {
        super(message);
    }

    public BaseException(String message, Throwable cause) {
        super(message, cause);
    }
}
