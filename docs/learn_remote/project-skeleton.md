# Project Skeleton (Recommended Layered Architecture)

> 参考模板：苍穹外卖（Sky Take-Out）多模块分层架构
> 适用阶段：NovelBridge 当前为**单模块单体应用**，随着业务增长可拆分为多模块

---

## 一、总体依赖关系

当前阶段为 **单模块单体架构**（所有代码在 `Novel-Bridge` 模块内）。未来可拆分为：

```
┌──────────────────────────────────────────────────────────────────────┐
│                        novel-bridge-server (可执行模块)                │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────────────────────┐   │
│  │ Controller   │→ │ Service  │→ │ Mapper (MyBatis)             │   │
│  │ (按业务域分组) │  │ (接口+实现)│  │ (@Mapper + SQL 注解/XML)     │   │
│  └──────────────┘  └──────────┘  └──────────────────────────────┘   │
│         │              │                    │                        │
│         │    ├─────────────────────┐       │                        │
│         │    │ handler/            │       │                        │
│         │    │ config/ (future)    │       │                        │
│         │    └─────────────────────┘       │                        │
│         ▼              ▼                    ▼                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              novel-bridge-pojo (DTO / Entity / VO)           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │           novel-bridge-common (工具/异常/响应/枚举/配置)        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### 模块依赖关系（未来目标）

| 模块 | 依赖 | 说明 |
|------|------|------|
| **novel-bridge-common** | 无 | 纯基础设施，最底层 |
| **novel-bridge-pojo** | 无 | 纯数据模型，独立定义 DTO/Entity/VO |
| **novel-bridge-server** | common + pojo | 业务主模块，引入两个基础模块 |

> **要点**：common 与 pojo 之间没有依赖关系。server 同时依赖两者。

---

## 二、当前包结构（单模块适用）

```
com.achen.novelbridge/
├── NovelBridgeApplication.java              # Spring Boot 入口
│                                           # @MapperScan + @ConfigurationPropertiesScan
│
├── common/                                  # 基础设施层（不依赖其他内部模块）
│   ├── base/
│   │   └── BaseEntity.java                 # 纯 POJO（无 ORM 注解）
│   │                                      # id, createdAt, updatedAt, createdBy, updatedBy
│   │                                      # 由 SQL DEFAULT + ON UPDATE 自动填充
│   ├── enums/
│   │   ├── BookStatus.java
│   │   ├── ChapterStatus.java
│   │   ├── ChatRole.java
│   │   ├── ChatSessionStatus.java
│   │   ├── RunType.java
│   │   ├── SourceType.java
│   │   ├── StepStatus.java
│   │   ├── StepType.java
│   │   └── TaskStatus.java
│   ├── exception/
│   │   └── BaseException.java              # 业务异常基类
│   ├── properties/
│   │   └── BooksProperties.java            # @ConfigurationProperties
│   ├── result/
│   │   └── Result.java                     # 统一响应模型
│   └── util/
│       └── ChapterSplitter.java            # 工具类（无状态静态方法）
│
├── pojo/                                    # 数据模型层（不依赖其他内部模块）
│   ├── entity/
│   │   ├── NovelAgentRun.java
│   │   ├── NovelAgentStep.java
│   │   ├── NovelBook.java
│   │   ├── NovelChapter.java
│   │   ├── NovelChatMessage.java
│   │   ├── NovelChatSession.java
│   │   └── NovelCitation.java
│   ├── dto/
│   │   ├── CreateBookRequest.java
│   │   ├── CreateSessionRequest.java
│   │   └── SendMessageRequest.java
│   └── vo/
│       ├── AgentRunVO.java
│       ├── AgentStepVO.java
│       ├── BookVO.java
│       ├── ChapterVO.java
│       ├── ChatMessageVO.java
│       ├── ChatSessionVO.java
│       └── CitationVO.java
│
├── resources/
│   ├── mapper/
│   │   └── BookMapper.xml                  # MyBatis XML 映射文件
│   ├── application.yml                     # 公共配置
│   ├── application-dev.yml                 # 开发环境配置
│   └── schema.sql                          # DDL（CREATE TABLE IF NOT EXISTS）
│
└── server/                                  # 业务主模块（依赖 common + pojo）
    ├── controller/
    │   ├── BookController.java             # REST 接口
    │   └── ChatController.java
    ├── mapper/                              # MyBatis 数据访问
    │   ├── AgentRunMapper.java
    │   ├── AgentStepMapper.java
    │   ├── BookMapper.java
    │   ├── ChapterMapper.java
    │   ├── ChatMessageMapper.java
    │   ├── ChatSessionMapper.java
    │   └── CitationMapper.java
    ├── service/
    │   ├── IBookService.java               # 接口（契约）
    │   ├── IAgentRunService.java
    │   ├── IChatService.java
    │   └── impl/
    │       ├── AgentRunServiceImpl.java
    │       ├── BookServiceImpl.java
    │       └── ChatServiceImpl.java
    └── handler/                             # 全局异常处理
        └── GlobalExceptionHandler.java     # @RestControllerAdvice
```

---

## 三、分层规范

### 3.1 请求处理流程

```
HTTP Request
    │
    ▼
┌──────────────────────┐
│  Controller 层        │  接收请求、参数校验 @Valid、调用 Service、返回 Result
│  (@RestController)    │
├──────────────────────┤
│  Service 层           │  业务逻辑编排、事务管理 @Transactional、调用 Mapper
│  (接口 + Impl)        │  接口定义契约、Impl 实现具体逻辑
├──────────────────────┤
│  Mapper 层            │  数据访问，MyBatis @Insert/@Select/@Update/@Delete
│  (@Mapper)            │  复杂查询 → XML 映射文件（resources/mapper/）
├──────────────────────┤
│  Handler 层           │  @RestControllerAdvice 统一异常处理
└──────────────────────┘
    │
    ▼
  Database (MySQL)
```

### 3.2 各层约束

**Controller**：注入 Service 接口（不是 Impl）。只做 HTTP 参数校验和响应组装，不含业务逻辑。

**Service**：接口定义契约，Impl 实现逻辑。`@Transactional` 标注在 Impl 方法上。可调用多个 Mapper。

**Mapper**：`@Mapper` + SQL 注解。每个方法操作一张表。XML 文件放在 `resources/mapper/`。

**通用约定**：
- 所有实体 `extends BaseEntity`
- 所有响应用 `Result<T>` 包裹
- 业务异常抛出 `BaseException` 子类
- 配置属性用 `@ConfigurationProperties` 集中管理

---

## 四、新建文件对照表

| 要创建... | 包路径 | 参考内容 |
|---|---|---|
| 新数据表 | `pojo/entity/XxxEntity.java` | `extends BaseEntity` + schema.sql 添加 DDL |
| 表 CRUD | `server/mapper/XxxMapper.java` | `@Mapper` + `@Insert`/`@Select` 注解 |
| 业务逻辑 | `server/service/IXxxService.java` + `server/service/impl/XxxServiceImpl.java` | 接口 + Impl |
| REST 接口 | `server/controller/XxxController.java` | 按业务域分组 |
| 请求体 | `pojo/dto/XxxRequest.java` | Jakarta Validation |
| 响应体 | `pojo/vo/XxxVO.java` | `@Builder` |
| 工具类 | `common/util/XxxUtil.java` | 无状态静态方法 |
| 异常 | `common/exception/XxxException.java` | `extends BaseException` |
| 配置 | `common/properties/XxxProperties.java` | `@ConfigurationProperties` |
