# 后端到全栈桥接

本 skill 面向 Java 后端初学者进阶初级全栈。前端只讲理解端到端功能所需的部分。

## 重点

优先：

- Controller -> Service -> Mapper -> DB
- DTO、Entity、VO、参数校验、异常链路
- Vue 页面 -> API 调用 -> Controller -> 响应渲染
- 各层字段命名和映射
- 需要时讲登录 token 存储、请求头、路由守卫

暂缓：

- 高级 CSS
- 复杂组件架构
- 前端性能
- 动画
- 高级状态管理

## 链路地图

当阶段改变后端链路、API 形状、DTO/VO 字段、数据库字段或 Vue API 调用时，更新 `flow-map.md`。

## 字段溯源表

全栈阶段使用这张表：

| 页面字段 | Vue 状态 | API 参数 | DTO 字段 | Service 处理 | DB 字段 | VO 字段 | 页面展示 |
|---|---|---|---|---|---|---|---|

## 新手解释方式

一次只解释一条具体链路。例如：

`Login.vue 用户名输入 -> auth.ts 登录请求 -> LoginDTO.username -> AuthService.login -> user.username 字段 -> LoginVO.token -> localStorage token`
