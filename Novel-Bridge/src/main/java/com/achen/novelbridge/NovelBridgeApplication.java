package com.achen.novelbridge;

import com.achen.novelbridge.common.properties.RagAgentProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * NovelBridge — API-first novel reading and authoring analysis agent.
 * <p>
 * Stage 1: Foundation Skeleton.
 * </p>
 *
 * @NB-ENTRYPOINT
 * @NB-ROADMAP
 */
@SpringBootApplication
@EnableAsync
@EnableConfigurationProperties(RagAgentProperties.class)
public class NovelBridgeApplication {

    public static void main(String[] args) {
        SpringApplication.run(NovelBridgeApplication.class, args);
    }
}
