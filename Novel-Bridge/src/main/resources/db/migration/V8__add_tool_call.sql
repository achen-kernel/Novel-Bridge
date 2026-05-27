CREATE TABLE IF NOT EXISTS novel_tool_call (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    agent_run_id BIGINT DEFAULT NULL,
    agent_step_id BIGINT DEFAULT NULL,
    tool_name VARCHAR(100) NOT NULL,
    input_json JSON,
    output_json JSON,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    started_at DATETIME DEFAULT NULL,
    finished_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_tool_call_run (agent_run_id),
    KEY idx_tool_call_step (agent_step_id),
    CONSTRAINT fk_tool_call_run FOREIGN KEY (agent_run_id) REFERENCES novel_agent_run(id) ON DELETE SET NULL,
    CONSTRAINT fk_tool_call_step FOREIGN KEY (agent_step_id) REFERENCES novel_agent_step(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
