package com.achen.novelbridge.server.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

/**
 * MyBatis Mapper for basic database connectivity health check.
 */
@Mapper
public interface HealthCheckMapper {

    @Select("SELECT 1")
    int checkConnection();
}
