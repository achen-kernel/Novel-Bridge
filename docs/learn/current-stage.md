# current-stage.md

阶段 id：第1轮 — 项目骨架
状态：closed
轮次：1/9

## 功能目标
Git 初始化 + 空 Spring Boot 项目能启动

## 已完成
- Git 仓库初始化 ✅
- 三层包结构（controller/pojo/server）✅
- .gitignore ✅
- pom.xml 清理（无 mongodb/thymeleaf/restdocs）✅
- application.properties 配置 ✅
- data/ 目录 ✅

## 待完成
- 编译验证 `mvn compile`
- 启动验证 `mvn spring-boot:run`
- 首次全部提交

## 练习候选
- 编写 application.properties，配置 MySQL 数据源

## 已知
- MySQL 密码：123456
- 数据库：novel_bridge（已建空库）
- 端口：8080
