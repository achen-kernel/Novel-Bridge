package com.achen.novelbridge;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
@MapperScan("com.achen.novelbridge.server.mapper")
public class NovelBridgeApplication {

    public static void main(String[] args) {
        SpringApplication.run(NovelBridgeApplication.class, args);
    }

}
