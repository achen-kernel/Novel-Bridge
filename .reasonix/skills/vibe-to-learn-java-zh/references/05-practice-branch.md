# Practice 分支与练习标记

在 `main` 上正常开发，从 `main` 生成练习。

## 分支模型

- `main`：完整可运行项目。
- `practice`：生成的练习分支或 worktree。

优先使用 worktree：

```text
my-project/           main
my-project-practice/  practice
```

## 快照规则

每个版本生成一次练习快照：

1. 在 `main` 完成阶段。
2. 确保 `main` 是完整可运行解。
3. 检查 practice 目标目录干净。
4. 从 `main` 同步。
5. 只替换选中版本的 `@VTL-PRACTICE` 代码块。
6. 记录来源提交和版本。

## 标记质量

优先标记包含以下价值的代码：

- 业务分支
- 参数校验或异常处理
- 数据库访问
- DTO/VO 转换
- 事务边界
- 全栈字段映射

避免标记：

- getter/setter
- 生成代码
- 简单包装
- 需要隐藏上下文才能完成的代码
- 高风险基础设施代码

## 标记格式

```java
// @VTL-PRACTICE version=v1-auth level=2 module=auth target=method
// name=login
// signature=public LoginVO login(LoginDTO loginDTO)
// goal=完成登录：查询用户、校验密码、生成 token。
// prerequisites=Controller-Service-Mapper 链路；DTO/VO；密码哈希。
// inputs=LoginDTO 中的用户名和密码。
// outputs=LoginVO 中的 token 和用户展示字段。
// pitfalls=用户为空；密码错误；返回 token 结构不一致。
// hints=先查询用户，再校验密码，最后组装返回值。
public LoginVO login(LoginDTO loginDTO) {
    // complete implementation
}
```

在 `practice-plan.md` 里记录标记理由。
