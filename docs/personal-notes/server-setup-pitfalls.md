# 服务器环境配置踩坑记录

> 本文档给自己看，用来记录远程 Linux / llama.cpp / 模型部署过程中的环境坑。  
> 不作为新 agent 的默认阅读文档，不加入 `AGENTS.md` Read First。  
> 不写服务器密码、数据库密码、token、私钥。

## 当前背景

- 远程 Linux 用户：`wk`
- 项目根目录规划：`/home/wk/novelbridge`
- 模型目录规划：`/home/wk/novelbridge/models`
- 原模型来源：`/home/wk/models/qwen3.6-35b-gguf`
- 当前方向：不再依赖 `llama-cpp-python` server，准备安装原生 `llama-server`
- Python/Conda：可以保留已有环境，但长期服务不应该依赖 conda 激活

## 目录规划

推荐结构：

```text
/home/wk/novelbridge/
  apps/
    llama.cpp/
    rag-agent/
  models/
    qwen3.6-35b-gguf/
  data/
    mysql/
    neo4j/
    chroma/
  logs/
    llama.cpp/
    rag-agent/
    mysql/
    neo4j/
    chroma/
  runtime/
    pids/
    ports/
  env/
  deploy/
    remote/
  scripts/
    remote/
```

注意：如果看到这种目录：

```text
/home/wk/novelbridge/apps/{rag-agent}
```

这是异常目录。说明 shell 没有展开 brace，直接创建了带 `{}` 的目录。

修复：

```bash
mkdir -p /home/wk/novelbridge/apps/rag-agent

if [ -d "/home/wk/novelbridge/apps/{rag-agent}" ]; then
  rmdir "/home/wk/novelbridge/apps/{rag-agent}"
fi
```

如果里面有文件，先检查：

```bash
find "/home/wk/novelbridge/apps/{rag-agent}" -maxdepth 2 -type f -o -type d
```

确认没用后再删：

```bash
rm -r "/home/wk/novelbridge/apps/{rag-agent}"
```

## llama-cpp-python server 踩坑

已有环境：

```bash
pip list | grep llama
# llama_cpp_python   0.3.23
```

`python -m llama_cpp.server --help` 有输出，说明 Python server 模块存在。

启动后现象：

```text
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
ERROR:    [Errno -3] Temporary failure in name resolution
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
```

测试结果：

- `hostname` 返回 `root1-System-Product-Name`
- `getent hosts "$(hostname)"` 正常返回 `127.0.1.1 root1-System-Product-Name`
- `getent hosts localhost` 返回 `::1 localhost`
- Python 最小 HTTP 服务可连通
- uvicorn 最小 app 可返回 `ok`
- 说明系统端口绑定和 uvicorn 本身没有问题
- 问题集中在 `llama_cpp.server` 自身启动流程、依赖或解析逻辑

临时结论：

```text
不要继续在 llama-cpp-python server 上耗时间。
Demo 5A 转向原生 llama-server。
```

## 是否要卸载 llama-cpp-python

不强制。

如果它只装在 conda env `llamacpp` 中，可以先保留。原生 `llama-server` 跑通后再考虑卸载：

```bash
conda activate llamacpp
pip uninstall -y llama-cpp-python
```

长期服务建议：

```text
原生 llama-server：/home/wk/novelbridge/apps/llama.cpp
Python rag-agent：独立 venv 或 uv 管理
不要依赖 conda activate 来启动长期服务
```

## 原生 llama.cpp 安装方向

推荐安装位置：

```bash
/home/wk/novelbridge/apps/llama.cpp
```

推荐构建命令：

```bash
cd /home/wk/novelbridge/apps
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp

cmake -B build \
  -DGGML_CUDA=ON \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build --config Release -j"$(nproc)"
```

检查：

```bash
/home/wk/novelbridge/apps/llama.cpp/build/bin/llama-server --help
```

启动方向：

```bash
source /home/wk/novelbridge/deploy/remote/.env

nohup /home/wk/novelbridge/apps/llama.cpp/build/bin/llama-server \
  -m "$LLAMA_MODEL" \
  --host 127.0.0.1 \
  --port 18080 \
  -ngl 999 \
  -c 8192 \
  --jinja \
  > /home/wk/novelbridge/logs/llama.cpp/server.log 2>&1 &

echo $! > /home/wk/novelbridge/runtime/pids/llama-server.pid
```

### 实际编译坑：server Web UI 生成失败

第一次编译 `llama-server` 时遇到：

```text
CMake Error at scripts/xxd.cmake:13 (string):
  string sub-command LENGTH requires two arguments.

tools/ui/CMakeFiles/llama-ui.dir/build.make
```

判断：

```text
这是 server embedded Web UI 资源生成失败，不是 CUDA 或 llama.cpp 核心库失败。
Demo 5A 只需要 OpenAI-compatible API，不需要 Web UI。
```

解决方式：

```bash
cd /home/wk/novelbridge/apps/llama.cpp

rm -rf build

cmake -B build \
  -DGGML_CUDA=ON \
  -DLLAMA_BUILD_SERVER=ON \
  -DLLAMA_BUILD_UI=OFF \
  -DLLAMA_BUILD_WEBUI=OFF \
  -DLLAMA_USE_PREBUILT_UI=OFF \
  -DLLAMA_USE_PREBUILT_WEBUI=OFF \
  -DLLAMA_BUILD_TESTS=OFF \
  -DGGML_BUILD_TESTS=OFF \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build --config Release -j"$(nproc)" --target llama-server
```

确认配置：

```bash
cmake -B build -LAH | grep -Ei "LLAMA_BUILD_UI|LLAMA_BUILD_WEBUI|LLAMA_USE_PREBUILT"
```

应看到：

```text
LLAMA_BUILD_UI:BOOL=OFF
LLAMA_BUILD_WEBUI:BOOL=OFF
LLAMA_USE_PREBUILT_UI:BOOL=OFF
LLAMA_USE_PREBUILT_WEBUI:BOOL=OFF
```

### 实际启动成功命令

成功启动命令：

```bash
nohup /home/wk/novelbridge/apps/llama.cpp/build/bin/llama-server \
  -m "$LLAMA_MODEL" \
  --host 127.0.0.1 \
  --port 18080 \
  -ngl 999 \
  -c 8192 \
  --jinja \
  > /home/wk/novelbridge/logs/llama.cpp/server.log 2>&1 &

echo $! > /home/wk/novelbridge/runtime/pids/llama-server.pid
```

注意：

```text
当前 shell 里使用的是 $LLAMA_MODEL。
文档和 .env 中后续应统一变量名，建议保留 LLAMA_MODEL 或在脚本中兼容 LLAMA_MODEL_PATH。
```

检查：

```bash
curl http://127.0.0.1:18080/v1/models
tail -f /home/wk/novelbridge/logs/llama.cpp/server.log
```

停止：

```bash
kill "$(cat /home/wk/novelbridge/runtime/pids/llama-server.pid)"
rm -f /home/wk/novelbridge/runtime/pids/llama-server.pid
```

如果只是继续调试 Demo 5A，可以先不关；如果暂时不测，应停止，避免长时间占用双 3090 显存。

## Docker 镜像拉取失败

Docker Engine 已安装，但没有 Compose plugin；后来手动安装了 Docker Compose plugin 后，拉取 Docker Hub 镜像仍失败。

现象：

```text
failed to resolve reference "docker.io/library/mysql:8.4"
read: connection reset by peer
```

即使配置镜像源：

```text
https://docker.m.daocloud.io/
https://docker.1ms.run/
https://dockerproxy.com/
```

仍然可能拉不下来。

已验证 mirror 配置生效：

```bash
sudo docker info | grep -A5 "Registry Mirrors"
```

输出包含：

```text
Registry Mirrors:
  https://docker.m.daocloud.io/
  https://docker.1ms.run/
  https://dockerproxy.com/
```

但继续执行：

```bash
sudo docker compose up -d mysql neo4j
```

仍然失败：

```text
failed to resolve reference "docker.io/library/mysql:8.4"
failed to do request: Head "https://registry-1.docker.io/..."
read: connection reset by peer
```

结论：

```text
不是 docker-compose.yml 写错，也不是 mirror 没写进去。
是当前网络环境下 Docker Hub / mirror 拉取链路不可用或不稳定。
后续不要反复让 agent 配置 Docker mirror。
```

临时决策：

```text
不要继续在 Docker 源上耗时间。
Demo 5A 改为用户目录原生/半原生路线：
- llama.cpp 原生编译运行
- Chroma embedded in rag-agent venv
- Neo4j 使用 tar.gz 用户目录运行，或后续手动传包
- MySQL 使用 apt/system service 或已有 MySQL
- Docker route postponed
```

这条路线更符合当前网络环境。

### 后续修正：Docker 路线最终可用

后续通过 1Panel / Docker Compose plugin 处理后，Docker Compose 已经可以正常拉取并启动 MySQL 与 Neo4j：

```bash
cd /home/wk/novelbridge/deploy/remote
sudo docker compose pull mysql neo4j
sudo docker compose up -d mysql neo4j
```

实际结果：

```text
mysql:8.4 pulled
neo4j:5-community pulled
novelbridge-mysql started
novelbridge-neo4j started
```

因此当前结论更新为：

```text
Demo 5A 继续使用 Docker Compose 承载 MySQL / Neo4j。
llama.cpp 继续使用原生 llama-server。
Chroma 继续使用 rag-agent 内嵌 PersistentClient。
不要再切回 tar.gz Neo4j 或 apt MySQL，除非 Docker 再次长期不可用。
```

## Demo 5A 一键启动踩坑与闭环

### `.env` 缺少 LOG_DIR

现象：

```text
nb_up.sh: 行 36: LOG_DIR: 请设置 LOG_DIR（在 .env 中）
```

原因：

```text
真实 .env 只填了少量 MySQL / Neo4j 变量，没有从 .env.example 保留完整变量。
```

处理：

```text
不要手写极简 .env。
先 cp .env.example .env，再用 nano 修改必要值。
至少需要 NB_REMOTE_DEPLOY_DIR、RAG_AGENT_DIR、LLAMA_BIN、LLAMA_MODEL_PATH、LOG_DIR、MYSQL_*、NEO4J_AUTH、CHROMA_DATA_DIR、RAG_AGENT_VENV。
```

### Neo4j 密码长度不足

现象：

```text
Invalid value for password. The minimum password length is 8 characters.
org.neo4j.commandline.admin.security.exception.InvalidPasswordException
```

原因：

```text
Neo4j 5 community 默认要求密码至少 8 位。
```

处理：

```text
NEO4J_AUTH=neo4j/<at-least-8-chars>
```

注意：`.env` 会被 shell 脚本 source，密码不要使用反引号、未转义 `$`、复杂 shell 元字符。避免让 shell 把密码当命令或变量展开。

### Docker 权限导致脚本未真正启动容器

现象：

```text
permission denied while trying to connect to the Docker daemon socket
```

但健康检查仍显示 MySQL / Neo4j UP。

判断：

```text
这是因为容器之前已经用 sudo docker compose up -d 启动过。
脚本当时没有 Docker 权限，没能完整启动容器，只是检测到了已存在的端口。
```

处理：

```bash
sudo usermod -aG docker wk
exit
```

重新 SSH 登录后验证：

```bash
docker ps
```

如果 `docker ps` 不再报 permission denied，说明当前用户已经能直接运行 Docker。

### MySQL 变量缺失

现象：

```text
The "MYSQL_PASSWORD" variable is not set. Defaulting to a blank string.
```

原因：

```text
docker-compose.yml 或脚本引用了 MYSQL_PASSWORD，但 .env 没有定义。
```

处理：MySQL 段至少保留：

```env
MYSQL_ROOT_PASSWORD=<secret>
MYSQL_DATABASE=novel_bridge
MYSQL_USER=novel_bridge
MYSQL_PASSWORD=<secret>
MYSQL_DATA_DIR=/home/wk/novelbridge/data/mysql
```

### llama-server 健康检查

早期健康检查如果只测 `/health`，可能会误判 llama-server 为 mock 或异常。

当前 native `llama-server` 的可靠检查是：

```bash
curl http://127.0.0.1:18080/v1/models
```

实际已验证返回模型信息：

```text
Qwen_Qwen3.6-35B-A3B-Q8_0.gguf
n_ctx=8192
n_params=34660610688
```

### 当前已验证状态

时间：2026-05-16 23:47 左右。

`docker ps`：

```text
novelbridge-mysql  Up  127.0.0.1:13306->3306
novelbridge-neo4j  Up  127.0.0.1:17474->7474, 127.0.0.1:17687->7687
```

`bash nb_up.sh` 输出：

```text
MySQL:          [UP]
Neo4j:          [UP]
Neo4j-HTTP:     [UP]
Chroma:         [UP] (embedded)
llama-server:   [UP]
rag-agent:      [UP]
```

结论：

```text
Demo 5A 的远程基础服务已经初步闭环。
后续还需要用 nb_down.sh -> nb_up.sh 做一次从零停止再启动验证，确认脚本不仅能识别已有服务，也能完整恢复所有服务。
```

## Chroma 决策

向量数据库确定使用 Chroma。

Demo 5A 建议：

```text
Chroma 使用 embedded PersistentClient
路径：/home/wk/novelbridge/data/chroma
先不单独启动 Chroma server
```

原因：

- 少一个服务
- 少一个端口
- 少一个 health check 复杂度
- 更适合 Demo 5A

Demo 7 再做真正向量检索。

## 端口与 secrets 规则

固定端口：

```text
llama-server: 18080
rag-agent: 18081
mysql: 13306
neo4j-http: 17474
neo4j-bolt: 17687
```

不要把以下内容写进 tracked 文件：

```text
服务器密码
数据库密码
Neo4j 密码
API token
私钥
```

`.env.example` 只写占位值。真实 `.env` 不提交。

## Windows 本地连接远程服务（SSH Tunnel）

### 整体架构

```
Windows 本地                                Linux 远程 (192.168.3.50)
┌─────────────────────┐                   ┌─────────────────────────┐
│ Spring Boot         │   SSH Tunnel      │  MySQL       :13306     │
│ (profile=dev)       │ ── port forward──▶│  Neo4j       :17474     │
│                     │                   │  llama-server:18080     │
│  localhost:13306 ───┤                   │  rag-agent   :18081     │
│  localhost:17474 ───┤                   └─────────────────────────┘
│  localhost:18080 ───┤
│  localhost:18081 ───┤
└─────────────────────┘
```

Tunnel 的作用：把远程服务器的内部端口"映射"到本机的 localhost，让 Spring Boot 感觉所有服务都在本地。

### 前置条件：SSH 免密登录

```powershell
# Windows PowerShell 执行（只做一次）
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\id_ed25519" -N '""'
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh wk@192.168.3.50 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

第一次需要输入密码，之后就不需要了。

验证：
```powershell
ssh wk@192.168.3.50 "echo OK"
# 输出 OK 表示免密成功
```

### 启动 Tunnel

```powershell
# 在项目根目录执行
.\scripts\remote\nb_tunnel_up.ps1
```

成功后可以看到：
```
Local mappings:
  localhost:13306  ->  remote MySQL
  localhost:17474  ->  remote Neo4j HTTP
  localhost:17687  ->  remote Neo4j Bolt
  localhost:18080  ->  remote llama-server
  localhost:18081  ->  remote rag-agent
```

Tunnel 是后台进程，保持窗口开即可。关闭用 `.\scripts\remote\nb_tunnel_down.ps1`。

### 启动 Spring Boot（连远程）

#### 方式 1：命令行

```powershell
$env:SPRING_PROFILES_ACTIVE="dev"
cd Novel-Bridge
mvn spring-boot:run
```

#### 方式 2：IntelliJ IDEA

IDEA 里设置 VM 参数：

```
Run → Edit Configurations → 选择 NovelBridgeApplication
→ VM options 栏填入:
-Dspring.profiles.active=dev
→ 点 OK
```

然后点 Run 按钮即可。效果：Spring Boot 会使用 `application-dev.yml` 的配置（端口 13306，指向 SSH tunnel 转发的远程 MySQL）。

如果不想连远程，把 VM options 删掉或用 `-Dspring.profiles.active=local`，就会连回本地 3306。

### 两个 Profile 的用途对比

| Profile | 需要 Tunnel | MySQL 端口 | 适用场景 |
|---|---|---|---|
| `local`（默认） | 不需要 | localhost:3306（本地 MySQL） | 日常开发、mvn test |
| `dev` | 需要先开 tunnel | localhost:13306（→ 远程） | 需要连远程 llama + rag-agent |

### 踩坑记录

**Tunnel 启动报错 "Permission denied"**

原因：没有配 SSH key，密码输入在后台进程中被阻塞。
处理：配好免密 key 后重试。如果不想配 key，可以用 ssh 手动测试：
```powershell
ssh wk@192.168.3.50
```
先登录一次接受 host key，之后再开 tunnel 就不会提示了。

**Tunnel 映射端口和本地冲突**

如果本地 3306 已经有 MySQL，tunnel 映射的是 13306，不会冲突。如果 13306 也被占了，需要改 `nb_tunnel_up.ps1` 中的本地端口映射或停掉占用进程。

**MySQL 密码不对：改了 .env 但容器还是旧密码**

现象：`grep MYSQL_ROOT_PASSWORD .env` 看到密码是对的，但 `docker exec mysql -u root -p` 输同样密码报 `Access denied`。

原因：Docker 容器**第一次启动时**读取 `.env` 的密码初始化数据库，之后改 `.env` 不会影响已存在的容器和数据卷。

修复（数据会丢失，Demo 阶段可接受）：
```bash
docker compose down mysql
sudo rm -rf /home/wk/novelbridge/data/mysql   # 删除数据卷
docker compose up -d mysql                     # 用新密码重建
```

重建后数据库是空的，Spring Boot 启动时 `spring.sql.init.mode=always` 会自动跑 `schema.sql` 建表。重启前已导入的测试数据需要重新导入。

如果不想丢数据，需要 `docker exec` 进容器后用 `ALTER USER` 改密码，但前提是得能连上 MySQL，这就有鸡生蛋问题。所以在 Demo 阶段直接重建更省事。

**MySQL root 在 Docker 内权限问题**

从 tunnel 连 MySQL 时，连接来源显示为 Docker 网桥 IP（如 `172.19.0.1`）而不是 `localhost`，需要 root 有 `'root'@'%'` 权限：

```sql
ALTER USER 'root'@'%' IDENTIFIED BY '你的密码';
FLUSH PRIVILEGES;
```

重建后的 MySQL 默认 root 是 `'root'@'%'` 可以直接连，不用额外设置。

**Docker 权限：wk 用户需要 docker 组**

```bash
sudo usermod -aG docker wk
# 然后必须退出 SSH 重新登录，或执行 newgrp docker 刷新当前 shell
```

**Tunnel 脚本 `Start-Process` 参数冲突**

`-NoNewWindow` 和 `-WindowStyle Hidden` 在 PowerShell 5.1 不能同时使用。改为只用 `-WindowStyle Hidden`。

**MySQL 编码问题：TXT 文件编码与 MySQL 不一致导致乱码**

现象：上传 TXT 后，远程 MySQL 中 `novel_book_source.raw_text` 存的是乱码，后续 rag-agent 无法正确切章抽实体。

原因：
- 中文 TXT 文件常见编码为 GBK/GB18030
- Java 上传服务默认用 `new String(fileBytes, StandardCharsets.UTF_8)` 读取
- GBK 文件用 UTF-8 解码 → 乱码 → 存 MySQL → 后续全部脏数据

修复三处对齐：

1. **JDBC URL** 必须声明 UTF-8 连接：
   ```
   jdbc:mysql://.../novel_bridge?useUnicode=true&characterEncoding=UTF-8&connectionCollation=utf8mb4_unicode_ci
   ```

2. **上传接口** 新增 `encoding` 参数，支持指定文件编码：
   ```powershell
   curl -X POST .../upload -F "file=@book.txt" -F "encoding=GBK"
   ```

3. **Java 代码** 用 `new String(fileBytes, Charset.forName(encoding))` 替代硬编码 UTF-8。

2026-05-17 更新：建议统一用 UTF-8
- MySQL 建库是 `utf8mb4`，JDBC URL 已指定 `characterEncoding=UTF-8`
- 如果 TXT 文件本身也是 UTF-8，整个链路就全是 UTF-8，不需要额外指定 encoding
- `encoding` 参数作为安全网保留，但默认 UTF-8，只有遇到 GBK 文件才手动传 `encoding=GBK`
- 如果不确定 TXT 编码：用 VS Code 打开看右下角编码，或 `file book.txt` 查看

经验：
- 不要假设上传的 TXT 一定是 UTF-8，中文环境下 GBK/GB18030 非常常见
- `content_hash` 应在编码转换**前**计算（对原始字节做 SHA-256），这样同文件不同编码也能识别为不同版本
- `novel_book_source.encoding` 字段记录实际使用的编码，供下游 rag-agent 参考

**唯一索引冲突：重复上传同一文件**

现象：`Duplicate entry 'xxx' for key 'idx_source_hash'`，违反 `novel_book_source.content_hash` 唯一索引。

原因：`content_hash` 是文件的 SHA-256，相同文件会算出相同 hash。`schema.sql` 中 `content_hash` 是 `UNIQUE INDEX`，第二次插入直接报错。

处理（已在代码中处理，不依赖 DB 报错）：
```java
// 上传前先查 hash 是否存在
Optional<NovelBookSource> existing = bookSourceMapper.findByContentHash(contentHash);
if (existing.isPresent()) {
    // 直接抛异常，GlobalExceptionHandler 返回清晰提示
    throw new IllegalArgumentException("File already uploaded (source_id=" + ... + ")");
}
```

这样重复上传返回的是 400 + 明确提示"File already uploaded"，而不是 500 + 唯一索引冲突。

## 后续处理建议

1. 清理异常 `{rag-agent}` 目录。
2. 保留或卸载 `llama-cpp-python` 都可以，但不要再把它作为 Demo 5A 主路线。
3. 安装原生 `llama.cpp` 到 `/home/wk/novelbridge/apps/llama.cpp`。
4. 用原生 `llama-server` 替换 `python -m llama_cpp.server`。
5. 更新启动脚本，让它调用原生 `llama-server`。
6. Demo 5A 的 health check 先检查：
   - llama `/v1/models`
   - rag-agent `/health`
   - Neo4j HTTP
   - MySQL 连接
   - Chroma 数据目录可写
