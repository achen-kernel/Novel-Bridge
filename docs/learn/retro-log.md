# retro-log.md

## 2026-05-13 — 项目重启

### 决策：从按功能分包改为三层包结构
- **背景**：第一版代码按功能分包（user/、book/、agent/…），共 57 个文件
- **问题**：作为学习项目，按功能分包看不到每层的职责边界，不适合初学者
- **决策**：清空旧代码，改为 common / controller / pojo / server 三层结构
- **影响**：旧 57 文件已删除，从空白骨架重新开始，分 9 轮渐进实现
- **教训**：学习项目一开始就应该用清晰的分层结构

### 决策：Git 仓库位置
- **第一版**：git 建在 Novel-Bridge/ 子目录内，data/ 和 docs/learn/ 在外
- **纠正**：删掉子目录 git，在项目根目录 D:\Novel-Bridge 重新 init
- **原因**：根目录涵盖了后端、数据、文档、skill 所有内容

## 2026-05-12 — 第一次尝试

### Bug: MySQL Connector/J 9.x 不支持 utf8mb4 编码名
- **现象**：`Unsupported character encoding 'utf8mb4'`
- **修复**：JDBC URL 中 `characterEncoding=utf8mb4` → `characterEncoding=UTF-8`
- **教训**：新 JDBC 驱动对字符集编码名更严格

### 决策：EntityProfile + significance
- **原因**：区分主角与次要角色，为 v2 聚合铺路
- **字段**：significance 枚举 MAJOR / SUPPORTING / MINOR / CAMEO
- **范围**：v1 只建表 + CRUD，不做跨章聚合

### 决策：单一数据库 novel_bridge + book_id 归属
- **原因**：连接管理简单、支持后续多书问答、建表脚本可复用
