# 脚本契约

脚本用于节省 token，并减少高风险手工操作。

## 必需行为

所有脚本在可行时支持 `--json`，输出：

```json
{
  "status": "success|warning|error",
  "summary": "...",
  "artifacts": [],
  "recommended_reads": [],
  "next_actions": [],
  "warnings": [],
  "stop_condition": null
}
```

## Token 规则

- 默认不输出长 diff。
- 输出改动文件列表、疑似接口变化、字段变化、标记数量和 recommended reads。
- Agent 只读取 recommended files。
- 正常使用优先 `--compact`。

## 安全规则

- 写入型脚本必须支持 `--dry-run`。
- 练习生成前，如果目标目录有未提交改动，必须停止。
- 未标记代码永远不能替换。
- 只能转换选中的 version。
- 脚本失败时必须给出清晰 stop condition。

## 项目适配器

如果通用扫描不准确，在项目本地创建适配器：

```text
.vtl/
  vtl-adapter.json
  scripts/
  adapter-notes.md
```

不要为单个项目修改全局 skill 脚本。
