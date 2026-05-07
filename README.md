# 数据集服务平台 — 整体架构

## 一、系统总览

平台由四个相对独立、共享同一套存储与权限模型的子系统组成：

| 子系统 | 角色 | 主要使用者 |
|---|---|---|
| **数据 API**（Data API） | 鉴权 + 302 重定向，直连 S3/COS 下载 Gzip 压缩数据 | 第三方开发者（带 API Key 调用） |
| **数据采集**（Crawler Pipeline） | Scheduler 触发 → SQS 派发 → Lambda 爬取 → S3 落盘 | 平台内部，自动运行 |
| **管理后端**（Admin Console） | 查看订阅情况、数据集情况、用量统计、运营干预 | 平台运营 / 管理员 |
| **用户控制台**（User Console） | 注册登录、API Key 管理、用量查看、购买数据集 | 注册用户（数据消费方） |

---

## 二、整体架构图（C4 Container 视角）

```mermaid
graph TB
    %% ========== 外部角色 ==========
    Dev["👨‍💻 开发者<br/>(API 消费者)"]
    User["🙋 注册用户<br/>(数据集订阅方)"]
    Admin["👮 运营/管理员"]
    Source["🌐 数据源网站"]
    Pay["💳 支付网关<br/>(Stripe / 微信 / 支付宝)"]

    %% ========== 数据 API 子系统 ==========
    subgraph DataAPI["📦 子系统 1: 数据 API (详见 data-api.md)"]
        APIGW["API Gateway<br/>x-api-key 校验 + 限流"]
        AuthFn["Lambda: Auth & Redirect<br/>校验前缀权限<br/>生成 Presigned URL<br/>302 跳转"]
    end

    %% ========== 用户控制台子系统 ==========
    subgraph UserConsole["🖥️ 子系统 2: 用户控制台"]
        UserWeb["Web 前端<br/>(React / Next.js)"]
        UserAPI["API Gateway<br/>(JWT / Cognito)"]
        UserFn["Lambda: 用户业务<br/>· 注册 / 登录<br/>· API Key CRUD<br/>· 用量查询<br/>· 数据集订阅 / 购买"]
    end

    %% ========== 管理后端子系统 ==========
    subgraph AdminConsole["🛠️ 子系统 3: 管理后端"]
        AdminWeb["Web 前端<br/>(管理面板)"]
        AdminAPI["API Gateway<br/>(SSO / RBAC)"]
        AdminFn["Lambda: 管理业务<br/>· 用户/订阅总览<br/>· 数据集元数据维护<br/>· 用量与计费报表<br/>· 爬虫任务监控"]
    end

    %% ========== 数据采集子系统 ==========
    subgraph Crawler["🕷️ 子系统 4: 数据采集 Pipeline"]
        Sched["EventBridge<br/>Scheduler<br/>(Cron)"]
        Dispatch["Lambda: Dispatcher<br/>展开任务"]
        Queue["SQS: Crawl Queue<br/>(+ DLQ)"]
        Worker["Lambda: Crawler Worker<br/>抓取 → 清洗 → Gzip"]
    end

    %% ========== 共享存储/数据层 ==========
    subgraph Storage["🗄️ 共享存储层"]
        S3Raw[("S3: raw/<br/>原始抓取")]
        S3Pub[("S3: datasets/<br/>Gzip 压缩成品")]
        DDBKey[("DynamoDB:<br/>ApiKey ↔ 前缀权限")]
        DDBUser[("DynamoDB:<br/>Users / Subscriptions")]
        DDBMeta[("DynamoDB:<br/>Dataset Metadata")]
        DDBUsage[("DynamoDB / Timestream:<br/>Usage / Billing")]
    end

    %% ========== 观测性 ==========
    subgraph Obs["📊 可观测性"]
        Logs["CloudWatch Logs"]
        Metrics["CloudWatch Metrics"]
        Alarm["Alarm / SNS"]
    end

    %% ========== 数据 API 流量 ==========
    Dev -->|"GET /get/{path}<br/>x-api-key"| APIGW
    APIGW --> AuthFn
    AuthFn -->|查权限| DDBKey
    AuthFn -->|生成 Presigned URL| S3Pub
    AuthFn -.->|"302 → Presigned URL"| Dev
    Dev -.->|"直连下载 Gzip"| S3Pub
    AuthFn -->|写入调用日志| DDBUsage

    %% ========== 用户控制台流量 ==========
    User --> UserWeb
    UserWeb --> UserAPI --> UserFn
    UserFn <--> DDBUser
    UserFn <--> DDBKey
    UserFn --> DDBUsage
    UserFn --> DDBMeta
    UserFn -->|创建订单| Pay
    Pay -.->|Webhook| UserFn

    %% ========== 管理后端流量 ==========
    Admin --> AdminWeb
    AdminWeb --> AdminAPI --> AdminFn
    AdminFn --> DDBUser
    AdminFn --> DDBKey
    AdminFn --> DDBMeta
    AdminFn --> DDBUsage
    AdminFn -->|查看任务/重试| Queue

    %% ========== 爬虫流量 ==========
    Sched -->|定时触发| Dispatch
    Dispatch -->|读取任务清单| DDBMeta
    Dispatch -->|分片入队| Queue
    Queue -->|消费| Worker
    Worker -->|HTTP 抓取| Source
    Worker -->|落盘原始| S3Raw
    Worker -->|"产出 .gz 成品"| S3Pub
    Worker -->|更新版本/统计| DDBMeta

    %% ========== 观测 ==========
    AuthFn -.-> Logs
    UserFn -.-> Logs
    AdminFn -.-> Logs
    Worker -.-> Logs
    Dispatch -.-> Logs
    Logs --> Metrics --> Alarm

    %% ========== 样式 ==========
    classDef ext fill:#fff5e6,stroke:#e08e0b,color:#000
    classDef store fill:#eef7ff,stroke:#2b6cb0,color:#000
    classDef fn fill:#f0fff4,stroke:#2f855a,color:#000
    classDef gw fill:#fef5ff,stroke:#805ad5,color:#000
    class Dev,User,Admin,Source,Pay ext
    class S3Raw,S3Pub,DDBKey,DDBUser,DDBMeta,DDBUsage store
    class AuthFn,UserFn,AdminFn,Dispatch,Worker fn
    class APIGW,UserAPI,AdminAPI gw
```

---

## 三、关键时序图

### 3.1 开发者下载数据集（Data API 主链路）

```mermaid
sequenceDiagram
    autonumber
    participant C as 开发者客户端
    participant GW as API Gateway
    participant L as Auth Lambda
    participant D as DynamoDB(ApiKey)
    participant S as S3 (.gz)
    participant U as DynamoDB(Usage)

    C->>GW: GET /get/{path}<br/>x-api-key: xxx
    GW->>GW: API Key 是否存在 / 限流
    GW->>L: 触发函数
    L->>D: 查询 key → 桶 + 允许前缀
    L->>L: 校验 path 是否匹配前缀
    L->>S: GeneratePresignedUrl(15min)
    L-->>U: 异步写一条调用记录 (key, path, ts, bytes估算)
    L-->>C: 302 Location: <presigned URL>
    C->>S: GET <presigned URL>
    S-->>C: Gzip 文件 (Content-Encoding: gzip)
    C->>C: 网络库自动解压
```

### 3.2 数据采集 Pipeline

```mermaid
sequenceDiagram
    autonumber
    participant Cron as EventBridge Scheduler
    participant Dis as Dispatcher Lambda
    participant Q as SQS
    participant W as Worker Lambda
    participant Web as 数据源
    participant S3 as S3
    participant Meta as DynamoDB(Meta)

    Cron->>Dis: 定时触发 (e.g. 每小时)
    Dis->>Meta: 读取需要更新的 dataset 列表
    Dis->>Q: 批量 SendMessage (每条=一个抓取任务)
    Q->>W: 触发 (batchSize=N, 并发可控)
    W->>Web: HTTP 抓取
    W->>W: 清洗 + Gzip 压缩
    W->>S3: PutObject path/file.gz<br/>Content-Encoding: gzip
    W->>Meta: 更新版本号 / 行数 / 大小 / lastRunAt
    Note over Q,W: 失败自动重试,<br/>超过阈值进入 DLQ,<br/>管理后端可查看并重放
```

### 3.3 用户购买数据集

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant Web as 用户控制台
    participant Fn as User Lambda
    participant Sub as DynamoDB(Subscriptions)
    participant Key as DynamoDB(ApiKey)
    participant Pay as 支付网关

    U->>Web: 选择数据集 → 下单
    Web->>Fn: POST /orders
    Fn->>Pay: 创建支付会话
    Pay-->>U: 跳转支付页
    U->>Pay: 完成支付
    Pay-->>Fn: Webhook (signed)
    Fn->>Sub: 写订阅记录 (userId, datasetId, 有效期)
    Fn->>Key: 给该用户的 ApiKey 追加 allowed_prefixes
    Fn-->>Web: 通知 / 订单完成
```

---

## 四、数据模型一览（DynamoDB 主要表）

| 表 | PK / SK | 关键字段 | 谁在写 | 谁在读 |
|---|---|---|---|---|
| `ApiKeys` | PK=`apiKey` | bucket, allowed_prefixes[], userId, status, rateLimit | User Console / Admin | Auth Lambda |
| `Users` | PK=`userId` | email, plan, createdAt | User Console | Admin / User |
| `Subscriptions` | PK=`userId` SK=`datasetId` | startAt, expireAt, source(order/trial) | User Console (支付回调) | All |
| `Datasets` | PK=`datasetId` | name, prefix, schema, version, sizeBytes, rowCount, lastRunAt | Crawler Worker / Admin | All |
| `Usage` | PK=`apiKey` SK=`yyyymmddhh#requestId` | path, bytes, status | Auth Lambda | Admin / User Console |

> Usage 表数据量大、写多读少，可改为 **Timestream / Kinesis Firehose → S3 + Athena**。

---

## 五、设计原则与边界

1. **完全 Serverless**：所有计算节点都是 Lambda，按调用计费、自动扩缩容、零运维。
2. **存储即数据合约**：`S3 datasets/{datasetId}/...` 的前缀就是权限模型的最小单位，API Key 持有"前缀白名单"即可。
3. **下载链路与业务链路解耦**：Data API 路径只做"鉴权 + 重定向"，不经手字节流，成本和延迟最低（详见 `data-api.md` 第五节成本对比）。
4. **管理后端只读为主**：通过共享 DynamoDB 表观察用户/订阅/数据集/用量；写操作仅限运营修订（封禁、重置 Key、重放 SQS）。
5. **DLQ + 监控闭环**：爬虫失败不丢，统一进入 DLQ；管理后端提供"查看 / 重放 / 标记已处理"。

---

## 六、双云对齐（与 data-api.md 保持一致）

| 角色 | AWS | 腾讯云 |
|---|---|---|
| 对象存储 | S3 | COS |
| 函数计算 | Lambda | SCF |
| API 入口 | API Gateway | API 网关 |
| 队列 | SQS | CMQ / TDMQ |
| 调度 | EventBridge Scheduler | 定时触发器 |
| 元数据 KV | DynamoDB | TcaplusDB / Redis |
| 指标日志 | CloudWatch | CLS + 云监控 |

> 整体拓扑双云 1:1 对应，迁移成本仅是"换 SDK 客户端"。
