# Java Tech Stack

## Decision

Keep Java as the product API layer, but keep AI execution in Python `rag-agent`.

Java owns:

- upload and book metadata APIs;
- task status and progress APIs;
- chat session/message/citation APIs;
- review workflow APIs;
- frontend aggregation;
- later user/project/workspace APIs.

Python owns:

- text processing;
- prompt/model execution;
- extraction;
- evidence validation;
- retrieval indexing;
- graph projection.

## Selected Baseline

| Area | Choice | Reason |
|---|---|---|
| JDK | Java 21 | modern LTS, already used by the project |
| Framework | Spring Boot 4.0.6 | current project baseline; Java is product API, not AI runtime |
| Web | Spring MVC | simple product API, SSE support later, less moving parts than WebFlux |
| Build | Maven | existing project and local workflow |
| Database access | MyBatis 4.0.x starter | Spring Boot 4 compatible; explicit SQL for traceable data model and JSON fields |
| Migration | Flyway | versioned schema, safer than ad hoc `spring.sql.init` |
| DB driver | MySQL Connector/J | remote MySQL 8.4 target |
| API docs | springdoc-openapi | useful while front-end and agent APIs evolve |
| Validation | Spring Validation | request DTO validation |
| Observability | Spring Actuator | health/info endpoints |
| AI in Java | Not in Stage 1 core | Java should call `rag-agent`; direct model calls stay in Python first |
| Security | Deferred | add Spring Security when users/workspaces start |

## Why Spring Boot 4 Is Acceptable

The current Java project already uses JDK 21 and Spring Boot 4.0.6. This is acceptable because Java is the product API layer, while AI execution lives in Python `rag-agent`.

Spring AI documentation currently emphasizes Spring Boot 3.4.x and 3.5.x compatibility. Therefore Spring AI must not be a Stage 1 dependency. If we later need Java-side Spring AI integration, verify the current compatibility matrix before adding it.

## Spring AI Policy

Do not make Spring AI the main AI runtime in Stage 1.

Allowed later uses:

- product-side DeepSeek smoke tests;
- simple admin tools;
- Java-side chat client experiments;
- optional Qdrant `VectorStore` integration for front-end-facing read APIs.

Default route:

```text
Java API -> Python rag-agent -> DeepSeek/local 9B/Qdrant/Neo4j
```

If Java directly uses Spring AI later:

- verify Spring Boot 4 compatibility first;
- use Spring AI BOM only after compatibility is confirmed;
- use `spring-ai-starter-model-deepseek` for DeepSeek;
- use `spring-ai-starter-vector-store-qdrant` only if Java needs direct vector access;
- do not duplicate Python extraction/retrieval logic without a specific reason.

## MyBatis Policy

Use MyBatis first, not MyBatis-Plus.

Reason:

- schema is still evolving;
- SQL visibility matters for agent debugging;
- joins and JSON fields should stay explicit;
- MyBatis-Plus can be added later when CRUD boilerplate becomes repetitive.

Rules:

- simple queries may use mapper annotations;
- complex queries go in XML;
- no business logic in mapper XML;
- status transitions happen in service layer;
- all long-running writes are tied to AgentRun/AgentStep where applicable.

## Initial Maven Dependencies

Stage 1 should keep dependencies small:

```text
spring-boot-starter-web
spring-boot-starter-validation
spring-boot-starter-actuator
mybatis-spring-boot-starter
mysql-connector-j
flyway-core
flyway-mysql
springdoc-openapi-starter-webmvc-ui
spring-boot-starter-test
```

Do not add Spring Security, Spring AI, Redis, Neo4j Java driver, or Qdrant Java client until a stage needs them.

## Package Layout

```text
com.achen.novelbridge
├── common
│   ├── result
│   ├── exception
│   ├── properties
│   └── util
├── pojo
│   ├── entity
│   ├── dto
│   └── vo
└── server
    ├── controller
    ├── service
    ├── mapper
    └── handler
```

## Configuration Policy

Use clean YAML from scratch:

- `application.yml` for common config;
- `application-local.yml` for local database/service URLs;
- `application-dev.yml` for SSH-tunnel remote service URLs.

No real passwords in YAML. Use environment variables.

## Sources

- Current project baseline: JDK 21, Spring Boot 4.0.6, MyBatis Spring Boot Starter 4.0.0.
- Spring AI Getting Started: Spring AI compatibility must be checked before adding it to the Spring Boot 4 app.
- Spring AI DeepSeek docs: `spring-ai-starter-model-deepseek` and `spring.ai.deepseek.*`.
- Spring AI Qdrant docs: `spring-ai-starter-vector-store-qdrant` and Qdrant metadata filtering.
- MyBatis Spring Boot Starter docs: `4.0.x` targets Spring Boot 4.
