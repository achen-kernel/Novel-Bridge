# NovelBridge-Agents 后续路线

## 0. 路线原则

后续路线只在 v1 和 v2 稳定后推进。任何 agent 不得因为看到本文件，就在 v1 阶段提前实现多书问答、云同步、复杂图谱或完整设定卡系统。

## 1. v3：多书联合问答

### 目标

在单书 Book Memory Package 稳定后，支持跨书检索和问答。

### 前置条件

```text
v1 单书问答稳定
v2 EvalHarness 可评测
每本书都有明确 bookId、projectId、权限边界
Citation 可跨书表达来源
```

### 核心任务

```text
Project 级检索范围
跨书 Retriever
跨书 Citation
多书答案中明确区分来源书籍
冲突证据提示
```

### 红线

```text
不能让多书问答绕过单书权限
不能把不同书的同名实体默认合并
不能返回没有 bookId 的引用
```

## 2. v4：设定卡系统

### 目标

把审核后的知识沉淀为可复用设定卡。

### 对象

```text
SettingCard
SettingCollection
SettingCardCitation
```

### 类型

```text
CHARACTER
LOCATION
ITEM
ORGANIZATION
WORLD_RULE
EVENT
CUSTOM_NOTE
```

### 红线

```text
SettingCard 不能直接来自未审核模型输出
每张卡必须保留来源和审核状态
设定卡不能覆盖原始 ChapterFact
```

## 3. v5：云端同步与外部资料增强

### 目标

支持多设备同步和外部资料补充，但不破坏本地权威库原则。

### 核心任务

```text
SyncJob
ExternalSource
ConflictResolution
SourceTrustLevel
```

### 红线

```text
外部资料默认不可信
外部资料不能直接写入 APPROVED 知识
同步冲突必须可人工处理
```

## 4. v6：复杂知识图谱

### 目标

在轻量 EntityNode / EntityEdge 稳定后，再考虑更强的关系查询和图谱推理。

### 核心任务

```text
图查询服务
关系类型体系
时间线关系
冲突关系
图谱可视化
```

### 红线

```text
不要用图谱替代原文证据
不要把推理结果当事实
不要让图数据库成为 v1/v2 的启动依赖
```

## 5. v7：协作审核与发布流程

### 目标

支持多人审核、版本发布、知识包导出。

### 核心任务

```text
ReviewerRole
ReviewAssignment
KnowledgePackageVersion
ExportJob
AuditLog
```

### 红线

```text
审核动作必须可追踪
知识包导出必须包含来源
多人冲突必须保留审计记录
```

## 6. 后续路线总红线

```text
不管版本走到哪里，MySQL 仍是权威业务和知识资产库
Chroma / SQLite FTS / 图谱都只是辅助视图或检索层
模型输出默认不是权威知识
引用和审核链路不能被新功能绕过
评测必须覆盖关键改动
```

