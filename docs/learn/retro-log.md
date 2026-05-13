# retro-log.md

## 2026-05-12

### Bug: MySQL Connector/J 9.x 不支持 utf8mb4 编码名
- **现象**：`Unsupported character encoding 'utf8mb4'`
- **原因**：新版驱动不再识别 `utf8mb4` 作为 Java encoding 名
- **修复**：JDBC URL 中 `characterEncoding=utf8mb4` → `characterEncoding=UTF-8`
- **教训**：新 JDBC 驱动对字符集编码名更严格

### 决策：表设计调整
- **原有设计**：ChapterFact 通过 fact_type 区分人物/事件/地点
- **调整**：新增 `novel_entity_profile` 表，含 `significance` 字段（MAJOR/SUPPORTING/MINOR/CAMEO）
- **原因**：区分主角与次要角色，为 v2 EntityProfile 聚合铺路
- **影响**：v1 只建表 + CRUD，不做跨章聚合逻辑

### 决策：单一数据库
- **决策**：一个库 `novel_bridge` + book_id 归属，不采用一书一库
- **原因**：连接管理简单、支持后续多书问答、建表脚本可复用

### Agent 偏差记录
- **偏差**：EntityProfileRepository 中写入了不存在的方法返回类型 `List<EntityProfileBySignificance>`
- **纠正**：改为 `List<EntityProfile>`
- **规则**：写 Repository 后立即确认返回类型与 Entity 一致
