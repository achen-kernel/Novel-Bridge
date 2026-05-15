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
│  │ Controller   │→ │ Service  │→ │ Mapper (Spring Data JPA)      │   │
│  │ (按端分组)    │  │ (接口+实现)│  │ (接口 = DAO)                  │   │
│  └──────────────┘  └──────────┘  └──────────────────────────────┘   │
│         │              │                    │                        │
│         ▼              ▼                    ▼                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              novel-bridge-pojo (DTO / Entity / VO)           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │           novel-bridge-common (工具/常量/异常/响应/配置)       │   │
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

## 二、推荐包结构（当前单模块适用）

```
com.achen.novelbridge/
├── NovelBridgeApplication.java              # Spring Boot 入口
│
├── common/
│   ├── base/
│   │   └── BaseEntity.java                 # id, createdAt, updatedAt, createdBy, updatedBy
│   │
│   ├── constant/                            # 🔲 常量定义（未来添加）
│   │   ├── BookConstant.java               # 书籍相关常量
│   │   └── RedisKeyConstant.java           # Redis 键名常量
│   │
│   ├── context/                             # 🔲 线程级上下文（未来添加）
│   │   └── BaseContext.java                # ThreadLocal 持有当前用户ID / 书籍ID
│   │
│   ├── enums/                               # 枚举定义
│   │   ├── BookStatus.java
│   │   ├── ChapterStatus.java
│   │   ├── RunType.java
│   │   ├── StepStatus.java
│   │   ├── StepType.java
│   │   └── TaskStatus.java
│   │
│   ├── exception/                           # 🔲 业务异常体系（推荐添加）
│   │   ├── BaseException.java              # 业务异常基类（extends RuntimeException）
│   │   ├── BookNotFoundException.java
│   │   └── ChapterSplitException.java
│   │
│   ├── handler/                             # 🔲 全局异常处理（推荐添加）
│   │   └── GlobalExceptionHandler.java     # @RestControllerAdvice 统一处理
│   │
│   ├── properties/                          # 🔲 配置属性类（未来添加）
│   │   └── BooksProperties.java            # novel-bridge.books.* 配置映射
│   │
│   ├── result/                              # 🔲 统一响应模型（推荐添加）
│   │   ├── Result.java                     # 通用响应封装（code/msg/data）
│   │   └── PageResult.java                 # 分页响应封装
│   │
│   └── util/                                # 工具类
│       └── ChapterSplitter.java            # 章节拆分工具（无状态静态方法）
│
├── config/                                  # 🔲 配置类（推荐添加）
│   └── WebMvcConfiguration.java            # CORS、消息转换器、拦截器注册
│
├── controller/                              # 控制器层
│   ├── book/                                # 按业务域分组（当前）
│   │   └── BookController.java
│   └── agent/                               # 🔲 未来可拆分出独立模块
│       └── AgentRunController.java
│
├── interceptor/                             # 🔲 拦截器（未来添加）
│   └── AuthInterceptor.java                # JWT/Token 校验
│
├── mapper/                                  # 数据访问层（Spring Data JPA）
│   ├── BookMapper.java
│   ├── ChapterMapper.java
│   ├── AgentRunMapper.java
│   └── AgentStepMapper.java
│
├── pojo/                                    # 数据模型
│   ├── entity/                              # 数据库实体
│   │   ├── NovelBook.java
│   │   ├── NovelChapter.java
│   │   ├── NovelAgentRun.java
│   │   └── NovelAgentStep.java
│   ├── dto/                                 # 请求 DTO
│   │   └── CreateBookRequest.java
│   └── vo/                                  # 响应 VO
│       ├── BookVO.java
│       ├── ChapterVO.java
│       ├── AgentRunVO.java
│       └── AgentStepVO.java
│
├── service/                                 # 业务服务层
│   ├── IBookService.java                  # 接口（契约）
│   ├── IAgentRunService.java
│   └── impl/                               # 实现
│       ├── BookServiceImpl.java
│       └── AgentRunServiceImpl.java
│
└── aspect/                                  # 🔲 AOP 切面（未来添加）
    └── AutoFillAspect.java                 # 公共字段自动填充
```

### 图例

| 标记 | 含义 |
|------|------|
| **无标记** | 已完成 ✅ |
| 🔲 **推荐添加** | 当前阶段建议添加，投入小收益大 |
| 🔲 **未来添加** | 当前阶段不建议添加，等业务增长后再做 |

---

## 三、各层设计规范

### 3.1 分层请求处理流程

```
HTTP Request
    │
    ▼
┌──────────────────────┐
│  Interceptor 层       │  🔲 未来：Token 校验、用户身份提取、BaseContext 设置
│  (HandlerInterceptor) │
├──────────────────────┤
│  Controller 层        │  ✅ 接收请求、参数校验 (@Valid)、调用 Service、返回 Result
│  (@RestController)    │
├──────────────────────┤
│  Service 层           │  ✅ 业务逻辑编排、事务管理 (@Transactional)、调用 Mapper
│  (接口 + Impl)        │
├──────────────────────┤
│  Mapper 层            │  ✅ 数据访问（Spring Data JPA），方法命名驱动查询
│  (JpaRepository)      │
├──────────────────────┤
│  Aspect 层            │  🔲 未来：公共字段自动填充、日志、权限校验
│  (@Aspect)            │
└──────────────────────┘
    │
    ▼
  Database (MySQL) + Cache (Redis) 🔲
```

### 3.2 Controller 层

**参考苍穹外卖**：按业务域分组（不是按 HTTP 方法），目前仅 `book/` 和 `agent/`。

```java
// ✅ 推荐模式
@RestController
@RequestMapping("/api/books")
public class BookController {
    private final IBookService bookService;      // 注入接口
    private final BookMapper bookMapper;         // 注入 Mapper（简单查询时直接使用）

    @PostMapping
    public ResponseEntity<Result<BookVO>> createBook(...)
}
```

**当前状态**：⚠️ 直接返回 `ResponseEntity<BookVO>`，未使用统一响应模型 `Result<T>`。

### 3.3 Service 层

**接口定义契约，Impl 实现逻辑**：

```java
// ✅ 已完成
public interface IBookService {
    NovelBook createBook(String relativePath);
    NovelBook buildBook(Long bookId);
}

@Service
public class BookServiceImpl implements IBookService {
    private final BookMapper bookMapper;       // Mapper 注入
    @Override
    @Transactional
    public NovelBook buildBook(Long bookId) { ... }
}
```

### 3.4 Mapper 层

使用 Spring Data JPA，方法命名驱动简单查询：

```java
// ✅ 已完成
@Repository
public interface ChapterMapper extends JpaRepository<NovelChapter, Long> {
    List<NovelChapter> findByBookIdOrderByChapterNumber(Long bookId);
    // 复杂查询用 @Query (JPQL)
}
```

> **苍穹外卖使用 MyBatis-Plus + XML 映射**。NovelBridge 当前 4 张表、查询简单，Spring Data JPA 完全足够。等出现复杂多表联查时再考虑 MyBatis-Plus。

### 3.5 POJO 层

| 类型 | 命名示例 | 用途 |
|------|---------|------|
| Entity | `NovelBook` | 完整映射数据库表，`extends BaseEntity` |
| DTO   | `CreateBookRequest` | 接收前端请求参数 |
| VO    | `BookVO` | 返回给前端的数据，按需组装 |

- 所有 POJO 标配 `@Data`（Lombok）
- Entity 使用 `@Table` 指定表名
- DTO 使用 `@NotBlank` / `@NotNull` 等 Jakarta Validation 注解

### 3.6 Common 层

**当前已有的**：
- `common.base.BaseEntity` — ✅ id + 审计字段
- `common.enums.*` — ✅ 6 个枚举
- `common.util.ChapterSplitter` — ✅ 无状态工具类

**推荐立即添加的**：
- `common.result.Result<T>` — 统一响应（code + msg + data）
- `common.exception.BaseException` + `GlobalExceptionHandler` — 统一异常处理

```java
// 🔲 推荐添加
// 统一响应
@Data
public class Result<T> {
    private int code;      // 1=成功, 0=失败
    private String msg;
    private T data;

    public static <T> Result<T> success(T data) { ... }
    public static <T> Result<T> error(String msg) { ... }
}

// 业务异常基类
public class BaseException extends RuntimeException {
    public BaseException(String msg) { super(msg); }
}

// 全局异常处理
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(BaseException.class)
    public Result<Void> handleBaseException(BaseException e) {
        return Result.error(e.getMessage());
    }
}
```

---

## 四、对比苍穹外卖：NovelBridge 成熟度评估

| 模块 | 苍穹外卖 | NovelBridge 当前状态 | 优先级 |
|------|---------|---------------------|--------|
| Maven 多模块 | ✅ 3 个模块 | ❌ 单模块（demo 阶段不需要） | **未来** |
| 统一响应模型 | ✅ `Result<T>` | ❌ 直接返回 Entity/VO | **推荐添加** |
| 统一异常处理 | ✅ BaseException + Handler | ❌ 无 | **推荐添加** |
| Service 接口+Impl | ✅ | ✅ 刚刚完成 | **已完成** |
| Mapper 层 | ✅ MyBatis-Plus | ✅ JPA Repository | **已完成** |
| Controller 分组 | ✅ admin/merchant/user | ✅ book/agent 按域分组 | **已完成** |
| 配置属性类 | ✅ `@ConfigurationProperties` | ❌ 硬编码在 Service 中 | **推荐添加** |
| 工具类 | ✅ `common/utils/` | ✅ `common/util/` | **已完成** |
| 线程上下文 | ✅ BaseContext (ThreadLocal) | ❌ 无（当前无多用户场景） | **未来** |
| 拦截器 | ✅ 3 套 JWT 拦截器 | ❌ 无（当前无鉴权） | **未来** |
| AOP 切面 | ✅ AutoFill + 权限 | ❌ 无（当前字段少） | **未来** |
| 定时任务 | ✅ Spring Task | ❌ 无 | **未来** |
| 消息队列 | ✅ RabbitMQ | ❌ 无 | **未来** |
| 枚举 | ✅ 少量 | ✅ 6 个枚举 | **已完成** |

---

## 五、推荐优化路线

### 立即优化（投入小、收益大）

1. **`common/result/Result.java`** — 统一响应模型
2. **`common/exception/BaseException.java`** — 业务异常基类
3. **`common/handler/GlobalExceptionHandler.java`** — 全局异常处理
4. **`config/WebMvcConfiguration.java`** — CORS 等 Web 配置

### 近期优化（Demo 3-4 阶段）

1. **`common/properties/BooksProperties.java`** — 替代 `@Value` 硬编码
2. **Controller 分层** — 按 book/agent 等业务域划分 Controller 包

### 远期优化（v1+ 阶段）

1. **拆分为多模块** — common/pojo/server
2. **拦截器 + 上下文** — 多用户鉴权
3. **AOP 自动填充** — 跨切面关注点
4. **MyBatis-Plus** — 复杂查询时再引入

---

## 六、新建文件对照表

| 你要创建... | 包路径 | 参考 |
|---|---|---|
| 新数据表 | `pojo/entity/XxxEntity.java` | `extends BaseEntity` |
| 表 CRUD | `mapper/XxxMapper.java` | `extends JpaRepository<XxxEntity, Long>` |
| 业务逻辑 | `service/IXxxService.java` + `service/impl/XxxServiceImpl.java` | 接口 + Impl |
| REST 接口 | `controller/xxx/XxxController.java` | 按业务域分组 |
| 请求体 | `pojo/dto/XxxRequest.java` | Jakarta Validation |
| 响应体 | `pojo/vo/XxxVO.java` | `@Builder` |
| 工具类 | `common/util/XxxUtil.java` | 无状态静态方法 |
| 异常 | `common/exception/XxxException.java` | `extends BaseException` |
| 配置 | `config/XxxConfiguration.java` | `@Configuration` |
