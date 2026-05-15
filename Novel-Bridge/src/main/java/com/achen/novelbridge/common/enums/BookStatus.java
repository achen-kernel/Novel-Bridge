package com.achen.novelbridge.common.enums;

/**
 * Book build lifecycle.
 * IMPORTED -> BUILDING -> READY_FOR_QA / BUILD_FAILED
 */
public enum BookStatus {
    IMPORTED,
    BUILDING,
    READY_FOR_QA,
    BUILD_FAILED
}
