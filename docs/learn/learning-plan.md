# learning-plan.md

## NovelBridge-Agents — 学习计划

v0.1 目标是打好后端地基。采用三层包结构（controller / pojo / server）而非按功能分包，按学习曲线分 9 轮渐进实现。

### 轮次列表

| 轮次 | 内容 | 学习重点 | 练习量 |
| --- | --- | --- | --- |
| 1 | **项目骨架**（轻） | Git、pom.xml、MySQL 配置、空项目能启动 | 1 |
| 2 | **数据库表设计**（中） | 表设计、主外键、索引、枚举字段 | 纯设计 |
| 3 | **公共基础设施**（轻） | BaseEntity、枚举、统一 ApiResponse | 2-3 |
| 4 | **实体类**（重） | @Entity、@Column、字段映射、JPA 实战 | 3-5 |
| 5 | **Repository 层**（轻） | Spring Data JPA 方法命名、自定义查询 | 2-3 |
| 6 | **Service 基础业务**（中） | @Service、CRUD 封装 | 2-3 |
| 7 | **Service 任务与问答**（中） | @Transactional、长任务追踪、聊天链 | 2-3 |
| 8 | **Controller 层**（重） | @RestController、Restful API、统一返回 | 3-5 |
| 9 | **启动验证**（轻） | 编译、启动、curl 全链路测试、生成 practice | 验收 |

### 学习方式
- main 分支：完整可运行的参考答案
- practice-N 分支：@VTL-PRACTICE 标记处清空为 TODO
- 完成练习后切回 main 对比参考答案

### 版本检查点
每个轮次完成后都有一个可编译、可启动的 Git commit。
