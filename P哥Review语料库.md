# P哥 Review 语料库

这份文档不是新的原则手册，而是训练材料库。

主文档《架构师认知体系》沉淀稳定公理；本文件保存真实 review 语料、当时上下文、我们的 miss 和可迁移触发器。以后每补一条 P哥 comment，都优先补到这里；只有当多个案例反复指向同一个稳定模式时，再反哺主文档。

## 0. 抽取纪律

1. 原话优先。能保留 P哥原句时，不先改写成原则。
2. 每条语料必须带上下文。只记一句 comment 容易神化，必须说明当时改了什么、它为什么触发问题。
3. 记录 miss。comment 是答案，miss 才是我们和答案之间的距离。
4. 敏感信息不入库。历史会话里的 token、密码、完整 curl、内部账号密钥一律不保存。
5. 不把语料库当结论库。每条语料最后必须压成“下次 review 看到什么时触发什么问题”。
6. 区分直接原文和转述。GitLab thread / 聊天粘贴原文记为“评论原文”；只有用户概述时记为“用户转述”，不得把转述润色成引号内的伪原话。

## 1. 本轮已确认的信息来源

已扫来源：

- `/Users/houguanqun/.codex/session_index.jsonl`
- `/Users/houguanqun/.codex/sessions/**/*.jsonl`
- `/Users/houguanqun/.codex/logs_2.sqlite`
- GitLab 中能直接读取原始 thread 的 MR comment

本轮命中的 35 个候选会话，以及后续补充的 GitLab MR 原始评论，均按同一纪律完成来源审计。能确认评论、上下文和 miss 的内容已形成案例；只有转述而缺少完整语境的内容标为“背景证据”；只有 Codex 自评、实施过程或普通咨询的会话明确排除。第 4 节保留完整结案索引，便于追溯为什么入库或为什么不入库。

注意：关键词命中不等于 P哥语料。部分会话只是 Codex 自己做过 review，或者是我们转述“老板/P哥提到”但缺少原始 comment。前者排除；后者只有在上下文足以闭环时才能标成“用户转述”，不能冒充“评论原文”。

## 2. 案例模板

```md
## C-xxx <案例标题>

来源：
- 会话：
- 日期：
- 关联 MR / Issue：

评论原文 / 用户转述：
- ...

当时上下文：
- ...

P哥真正抓的问题：
- ...

我们当时的 miss：
- ...

可迁移触发器：
- 下次看到 ...，必须先问 ...

母题归属：
- ...
```

## 3. 已抽取语料

### C-001 Flow 异常到 GraphQL 错误契约

来源：
- 会话：`019ef32a-534c-7b42-93f5-af6908931d11`
- 文件：`/Users/houguanqun/.codex/sessions/2026/06/23/rollout-2026-06-23T14-28-17-019ef32a-534c-7b42-93f5-af6908931d11.jsonl`
- 日期：2026-06-23 至 2026-06-26
- 关联内容：Action / Function 异常契约，Flow exception 转 GraphQL error

P哥原话：

- “2xx 里的 xx 应当是表示任意数字而不是 xx 这个字面量”
- “这个结构我觉得有改进的空间，有几项可以考虑一下：自然兼容 ts 内置的 Error 结构；常用的属性应当在第一层；程序的判断尽量集中在一个字段上；公共的结构定义成对应的 BaseError 这样的基类，在我们自己的代码里不应该再出现原始的 new Error”
- “应该有一份描述整体异常结构的文档 + 然后加 GraphQL 侧处理异常的逻辑文档”
- “公共的 shared/error-utils.ts 里只放所有模块都要使用的内容；自己模块里的公共方法还可以有自己的 error-utils.ts”

当时上下文：

- 我们最初把 Flow 异常映射成 GraphQL `extensions.code = "FLOW_DECLARED_EXCEPTION"` 这类字符串。
- 后来按统一契约改成数字 code 和 `type = "200.xxx" / "400.xxx" / "500.xxx"`。
- 但仍在 GraphQL `extensions` 里塞了过多字段，且保留了 `exceptionType` 这种和 `type` 重复的表达。
- 文档一度被 GraphQL 标准错误形态牵着走，没有先回到企业内部错误契约的消费方式。

P哥真正抓的问题：

- 不是“GraphQL 里到底能不能用 extensions”，而是公共错误契约有没有一个清晰事实模型。
- `code` / `type` / `message` 是调用方最高频字段，应当自然兼容 TS `Error`，不能藏在只有 GraphQL 才懂的局部结构里。
- 程序分支判断要集中，不要让调用方在 `code`、`errorType`、`exceptionType`、`category` 之间猜哪个才是主判断字段。
- `BaseError` 不是类继承偏好，而是防止全仓到处 `new Error(message)` 造成不可编程错误的事实模型。
- `shared/error-utils.ts` 是高租金位置，只能放所有模块都会遵守的基础能力；Flow 的声明匹配、保留类型、脱敏白名单属于 Flow 模块本地公共能力。

我们当时的 miss：

- 把 GraphQL 协议当成了最终形态约束，忽略企业错误契约自身可以定义更适合调用方的一层结构。
- 误以为“字段都在 extensions 里”就是 GraphQL 正确姿势，没有从前端和下游服务怎么消费错误反推结构。
- 看到 `exceptionType` 时只把它当诊断字段，没意识到它和 `type` 已经表达同一个事实。
- 先写了 Flow 专属 mapper，后补 shared 基类，顺序上暴露了“从局部实现往上抽”的惯性。

可迁移触发器：

- 看到公共错误结构时，先问：如果它退化成普通 TS `Error`，`name/message/code/type` 分别在哪里？
- 看到两个字段都能用于分支时，先问：哪个字段是唯一判别轴？另一个是否只是重复表达？
- 看到 `shared` 新增能力时，先问：这个能力是不是所有模块都会用？如果只服务一个模块，它应该留在模块自己的 `error-utils.ts`。
- 看到协议适配层时，先问：这是内部事实模型，还是某个出口协议的序列化形态？

母题归属：

- 公共契约先建事实模型，再适配协议。
- shared 是高租金位置。
- Base class 表示事实模型，不表示继承癖。
- 程序判断集中在一个字段上。

### C-002 Operator 鉴权与 M2M scope

来源：
- 会话：`019ed44c-9f4b-7b83-b133-1bdb283808a2`
- 文件：`/Users/houguanqun/.codex/sessions/2026/06/17/rollout-2026-06-17T14-37-31-019ed44c-9f4b-7b83-b133-1bdb283808a2.jsonl`
- 日期：2026-06-17
- 关联内容：Operator 调用身份、IdaaS M2M token、scope 传播

P哥原话：

- “auth.eos.serviceScopes 这个配置项是用于 M2M App 创建之后设置可申请权限范围用的，如果用于调用 IdaasM2mAppService.getAccessToken(appId, serviceId, scopes) 的 scopes 参数功能上可以走通，但是通常会包含过于宽泛的权限，所以这个调用的 scopes 参数最好是限定到指定的资源上”
- “authUse 这个字段如果直接指定为 requestScopes 是不是更好？”
- “authUse 非空表示使用 RESOURCE_M2M，并且 authUse 的值用作 requestScopes？”
- “原来有一个 OPERATOR_ACTION_INVOKE，是要废弃掉吗？”

当时上下文：

- 我们在 Operator 调用链路里接入身份和 M2M token。
- 初版设计把配置里的 `serviceScopes` 当成运行时请求 token 的 scopes。
- 另有 `authUse` 字段表达鉴权策略，但字段名没有直接暴露它最终会作为 `requestScopes` 使用。
- 代码里出现 `OPERATOR_ACTION_INVOKE` 和新命名并存。

P哥真正抓的问题：

- 权限配置上限和运行时请求最小权限是两件事，不能因为“功能上能走通”就混用。
- 字段名应该揭示它的实际消费语义。如果最终用于请求 scopes，就不要命名成抽象的 `authUse`。
- 安全字段不能靠口头约定理解。名字一模糊，后续实现就会把策略、范围、请求动作混在一起。
- 老名字是否废弃必须显式收口，否则新旧概念并存会制造长期心智分叉。

我们当时的 miss：

- 把“能拿到 token”当成目标，没有先问 token 应该代表最小哪组资源权限。
- 把字段命名当成实现细节，没有看到它是安全语义的一部分。
- 对旧枚举名缺少生命周期意识，没有第一时间判断保留、迁移、兼容还是删除。

可迁移触发器：

- 看到 `scope` / `permission` / `auth` 字段时，必须分清：授权上限、运行时请求、策略判定、资源边界。
- 看到一个字段最终被当成另一个概念消费时，优先改名，让字段名等于消费语义。
- 看到旧枚举和新枚举并存时，必须问：旧的要废弃吗？兼容期多久？谁负责迁移？

母题归属：

- 安全契约必须最小权限。
- 字段名是契约，不是注释。
- 重命名必须有迁移叙事。

### C-003 最小运行时与高码定义依赖

来源：
- 会话：`019e9656-8d75-75e2-b82a-f7c794eee170`
- 文件：`/Users/houguanqun/.codex/sessions/2026/06/05/rollout-2026-06-05T13-51-55-019e9656-8d75-75e2-b82a-f7c794eee170.jsonl`
- 日期：2026-06-05
- 关联内容：SQL 脚本拆分、最小运行时、自举业务依赖

P哥原话：

- “这是拆分 SQL 脚本以区分最小运行时和自举（业务）的 MR，这里面有两个关键的改动”
- “非最小运行时依赖的字段（如 displayName 等）从代码里进行了移除”
- “GraphQL 接口受初始高码相关的 Object Type 的字段定义影响，修改成了完全从 ObjectType 表里的 properties 定义来进行呈现”
- “分支相关的一个 operator 上似乎也受初始高码定义的字段影响”
- “依赖不能是高码定义的那部分，依赖要在 ObjectType 表里所定义的 properties 为准”

当时上下文：

- core 正在把 SQL 初始化脚本拆成最小运行时和业务自举两层。
- GraphQL schema 生成逻辑一度依赖初始高码里的 ObjectType 字段定义。
- 某些 operator 也可能从高码定义拿字段，而不是从运行时 ObjectType.properties 拿字段。

P哥真正抓的问题：

- 最小运行时只能依赖自己必须拥有的事实，不能偷用业务自举层或高码层的字段定义。
- 运行时 schema 的事实来源必须是 ObjectType 表里的 properties，不是代码里某份“看起来一致”的初始定义。
- 删除 `displayName` 这类字段不是小清理，而是在把运行时从业务展示语义里解耦出来。

我们当时的 miss：

- 把“初始高码定义和运行时 properties 当前一致”当成可接受，没看到来源错了就是架构错了。
- 更关注脚本能否跑通，没有先画出最小运行时依赖边界。
- 对 branch operator 的同类依赖没有主动全局扫描。

可迁移触发器：

- 看到运行时代码读取模型字段时，必须问：这是 canonical metadata，还是初始化/示例/高码投影？
- 看到“目前两处值一样”时，必须问：哪一处是权威来源？另一处是否只是派生缓存？
- 看到一个边界修复时，必须横向查同类 operator 是否也越界。

母题归属：

- 最小运行时过滤器。
- 单一事实来源。
- 高码定义不能反向污染 runtime。

### C-004 demo 与生产代码隔离

来源：
- 会话：`019df1bd-c322-77e2-8b4c-65268b540d3a`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/04/rollout-2026-05-04T14-47-18-019df1bd-c322-77e2-8b4c-65268b540d3a.jsonl`
- 日期：2026-05-05
- 关联内容：objects runtime demo、初始化数据、Function 表依赖

P哥原话：

- “src 目录下应当只存在生产代码，任何演示/样例相关的内容应该都在 examples 目录里。这些 demo 类的东西必须在 src 目录里是因为有什么能力缺失吗？”
- “正式的初始化数据里有非主分支的吗？如果是测试/demo类数据，建议放到单独的一个 55-demo-data.sql 文件里”
- “初始化逻辑中应该只有 main 分支的逻辑”
- “我们的最小运行时实现应当不需要 Function 表，收敛一下吧。另外 Function 这块的处理在 demo 中还是要有的哈，但是在正式的哪里就不需要了，sql 脚本里也不要了”
- “这些应该用 lowerCamelCase，譬如改成 findManyCustomers / findUniqueCustomer / findFirstCustomer / aggregateCustomers”

当时上下文：

- objects runtime demo 代码、样例数据、正式 SQL 初始化混在一起。
- 正式初始化脚本里出现非 main 分支数据。
- 最小运行时里仍残留 Function 表依赖，但 demo 又确实需要展示 Function 相关能力。
- GraphQL schema 同时出现大写方法名和 lowerCamel 风格。

P哥真正抓的问题：

- demo 不是无害的。demo 一旦进入 `src` 或正式初始化脚本，就会被后来的人当成生产机制。
- 最小运行时不需要的表，即使 demo 需要，也不能留在正式 runtime 依赖里。
- 分支数据是运行时语义，不是初始化装饰。正式初始化必须只有 main 分支，否则会让 core 的起点变复杂。
- GraphQL 命名风格是 API 契约，不是审美问题。

我们当时的 miss：

- 把 demo 当作临时工程便利，没有意识到它会污染生产心智模型。
- 没有把“正式 runtime 需要”和“demo 展示需要”拆成两个目录、两套初始化路径。
- 看到了 Function 表“不一定需要”，但没有用最小运行时标准果断清掉。

可迁移触发器：

- 看到 `demo` / `showcase` / `sample` 进入 `src`，必须问：这是能力缺失导致必须放这里，还是只是放错地方？
- 看到正式初始化里有非 main 分支，必须问：这是 core 必需状态，还是 demo/测试状态？
- 看到 runtime 依赖某张表，必须问：没有它最小系统能不能执行？如果能，它不属于最小运行时。

母题归属：

- demo 和生产隔离。
- 最小运行时清场。
- 初始化数据是事实边界，不是便利垃圾桶。

### C-005 预置 CUD ActionType 不是表结构镜像

来源：
- 会话：`019dfaf8-e220-7320-8fb0-e0c231ba9ac8`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/06/rollout-2026-05-06T09-48-28-019dfaf8-e220-7320-8fb0-e0c231ba9ac8.jsonl`
- 日期：2026-05-06
- 关联内容：核心 ObjectType 的 Create / Update / Delete ActionType bootstrap

P哥原话：

- “这个 flow artifact 也需要初始化，存放在 FunctionBranchDetail 表里。flow 的配置里应该是配置的直接使用 CUD operator”
- “delete 操作不需要这么多参数吧？”
- “作为预置实现，rid 在 createXxx 时不传入，服务端自动生成（SQL Schema 里 DEFAULT 生成 uuid，基础类型里增加一个 UUID？），还有 createdAt 和 updatedAt 不传入”
- “createdAt 不传入”
- “如果我们内置 trigger 来更新，这里也不传入 updatedAt”
- “apiName 在更新时也不是必传的”
- “ObjectType 还有一个 titleKey，NOT NULL。在 create 的时候必传，但是 update 时是非必传”

当时上下文：

- 我们为 6 张核心表批量生成标准 CUD ActionType。
- 初版参数规则是“parameters 与目标 object type 的 properties 定义保持镜像一致”。
- 每个 ActionType 的 `flow_artifact_rid` 只是占位，没有对应真实 flow artifact。

P哥真正抓的问题：

- Action 参数不是数据库字段镜像。Create / Update / Delete 是三个不同意图，每个意图的参数集合不同。
- `rid`、`createdAt`、`updatedAt` 是服务端治理字段，不应该由调用方传。
- `apiName` 对 create 可能必填，对 update 不一定必填；`titleKey` create 必填，update 可选。参数必填性来自操作语义，不来自表字段 `NOT NULL` 的机械投影。
- 既然 ActionType 说 `operations.type = flow`，就必须有真实 flow artifact 承接，否则元数据契约是空的。

我们当时的 miss：

- 用表结构自动镜像 Action 参数，省了实现判断，但丢了操作语义。
- 以为 `flow_artifact_rid` 占位能先过，没看到它让契约声明和运行能力脱节。
- 对服务端管理字段缺少默认排除规则。

可迁移触发器：

- 看到 Action 参数从 ObjectType properties 自动生成时，必须先按操作分类：调用方输入、服务端生成、服务端维护、不可变字段、create 必填、update 可选、delete 只需定位键。
- 看到元数据声明使用某种执行机制时，必须检查该机制的 artifact 是否真实存在。
- 看到 `NOT NULL` 字段时，不能直接推导为 update 必填。

母题归属：

- API 参数表达操作语义，不是数据库字段镜像。
- 声明了能力就必须有可执行承载。
- 服务端治理字段不外包给调用方。

### C-006 Flow artifact 与 data/flows 目录

来源：
- 会话：`019dfaf8-e220-7320-8fb0-e0c231ba9ac8`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/06/rollout-2026-05-06T09-48-28-019dfaf8-e220-7320-8fb0-e0c231ba9ac8.jsonl`
- 日期：2026-05-06 至 2026-05-08
- 关联内容：预置 CUD / Query operator 的 Flow JSON 初始化

P哥原话：

- “还是要搞 flow，而且是要搞 redis json 的，用上 P哥的脚本，放到指定的目录”
- “在 sql/redis/flows 目录下放 flow 的 json 文件这个脚本会负责加载到 redis 里，json 文件的命名规则是 xxxx-{rid}.json”
- “Query 的也得提供 operator（就是咱们 findMany 什么的那些，包含聚合查询哈）”
- “Query 提供好 operator 后，也得搞成 flow”
- 后续修正：“这个目录更名了：data/flows”

当时上下文：

- CUD ActionType 先有 metadata，真实 Flow artifact 还没补齐。
- Query runtime 先通过 GraphQL 接口暴露，但没有作为 operator 和 flow 被统一初始化。
- 目录命名从 `sql/redis/flows` 变成 `data/flows`，文档和 SQL 注释仍有旧路径。

P哥真正抓的问题：

- 前端 mutation 入口背后必须有真实 flow，而不是只在元数据里写 `type = flow`。
- Query 不是接口特例。既然平台把能力沉淀成 operator/flow，就要把查询能力也纳入同一模型。
- 目录名是约定，不是无关注释。路径一错，后续加载脚本、文档、维护者都会分叉。

我们当时的 miss：

- 把“GraphQL 已能调用”当作能力完成，没有追到平台统一执行模型。
- 对路径注释的准确性不敏感，低估了初始化链路里目录约定的重要性。

可迁移触发器：

- 看到某能力既有 GraphQL 入口又有 operator/flow 模型时，必须问：它是不是被统一建模了，还是只在某个入口特例存在？
- 看到注释里的目录、脚本名、文件命名规则时，必须和实际加载脚本对齐。

母题归属：

- 能力要回到统一运行时模型。
- 文档路径也是契约。

### C-007 ValueType / RuntimePropertyDefinition 形态

来源：
- 会话：`019ea682-67ff-7283-a054-663766d75889`
- 文件：`/Users/houguanqun/.codex/sessions/2026/06/08/rollout-2026-06-08T17-13-44-019ea682-67ff-7283-a054-663766d75889.jsonl`
- 日期：2026-06-08
- 关联内容：runtime value type、索引、mask、PG 聚合类型处理

P哥原话：

- “这里不需要定义这么多吧？后续也很难收敛”
- “把 Value Type 放到 type 里面去”
- “node-postgres 这个库对 long/decimal 应该就是按照 string 来输入和输出的吧，这里不需要显式的 ::text 操作符？”
- “只要数据库 schema 正确，这些也不需要显式的数据类型操作符？”
- “有的地方是 DATETIME -> TIMESTAMP，有的地方是 TIMESTAMP -> DATETIME，应该只有一个方向譬如 DATETIME -> TIMESTAMP（或者干脆就没有 DATETIME 这个类型）；而在 PG 数据库里应该使用 TIMESTAMPTZ 数据类型”
- “我记得文档里是用派生的方式来组织不同 kind 的字段定义的？”
- “mask 应该属于 RuntimePropertyStorageDefinition。sensitive 是什么用途？”

当时上下文：

- 我们扩 RuntimePropertyDefinition，支持 bigint、decimal、encrypted、mask、filterable、unique、FTS 等能力。
- 初版把若干维度摊在并列字段里，也在 PG 查询聚合结果里加了显式类型 cast。
- DATETIME / TIMESTAMP 映射双向存在。
- `mask` 和 `sensitive` 的归属不清。

P哥真正抓的问题：

- ValueType 不应在外层无限增字段，而应该进入统一 `type` 结构，让不同 kind 派生自己的字段。
- 类型映射要单向可推导，不能同一系统里一会儿 DATETIME 到 TIMESTAMP，一会儿 TIMESTAMP 到 DATETIME。
- 如果数据库 schema 和 driver 已经给出正确行为，应用层不应再加显式 cast 复制一套类型系统。
- `mask` 是存储/展示治理的一部分，不能和抽象 security 标签随意并列；`sensitive` 如果没有清晰消费方，就不该出现。

我们当时的 miss：

- 看到新能力就加字段，没先问它属于哪个派生 kind。
- 用实现层 cast 补偿不确定性，而不是先确认 driver 和 schema 的事实行为。
- 把“可能有用的标签”加进模型，没有先找到消费方。

可迁移触发器：

- 看到模型字段快速变多，必须问：这是并列属性膨胀，还是应该改成判别联合/派生结构？
- 看到类型映射函数，必须问：单一方向是什么？有没有反向映射在表达另一套事实？
- 看到应用层补类型 cast，必须先确认数据库 schema 和 driver 是否已经承担了这个职责。
- 看到 `sensitive`、`mask`、`encrypted` 这类词，必须问：消费方是谁？运行时怎么用？归属 storage、security 还是 display？

母题归属：

- 模型形态先于字段堆叠。
- 类型系统必须单向可推导。
- 不重复底层已经承担的职责。

### C-008 Ontology edit endpoint guard

来源：
- 会话：`019ec9e3-c63b-7940-885f-d14826cdc6da`
- 文件：`/Users/houguanqun/.codex/sessions/2026/06/15/rollout-2026-06-15T14-06-48-019ec9e3-c63b-7940-885f-d14826cdc6da.jsonl`
- 日期：2026-06-15 至 2026-06-16
- 关联内容：Ontology edit GraphQL mutation，endpoint path 与 body 参数

P哥原话：

- “这个 ontologyRid 的参数跟其他的参数如 displayName 应该是同等地位的？”
- “如果这里是用来决定路由的，那应该使用 URL Path 里的 ontologyRid”
- “用方法名来判断感觉有点。。。不太可靠”

当时上下文：

- 为防止调用侧误用 core endpoint，我们尝试在 ontology-edit action 元数据中加入普通必填 `ontologyRid` 参数。
- GraphQL schema 按元数据暴露该参数，同时 runtime 又把它当作路由/作用域判断字段处理。
- 代码用 action 方法名正则判断是否 ontology edit action。

P哥真正抓的问题：

- 同一个字段不能同时扮演普通业务参数和路由控制参数。它的位置决定语义。
- 如果是路由，就应该来自 URL Path 这类外层上下文；如果是业务输入，就应当和 displayName 同等对待，不能被特殊删除。
- 方法名不是可靠语义来源。用 `createObjectType` 这类命名判断 action 类型，会把契约绑死在命名习惯上。

我们当时的 miss：

- 看到 `ontologyRid` 就下意识把它当 scope，但没有先区分“输入参数”和“路由上下文”。
- 用正则匹配方法名快速实现，没意识到它绕过了元数据事实模型。
- 文档里讲了 endpoint guard，但代码里没有把 guard 的事实来源建模清楚。

可迁移触发器：

- 看到一个字段既出现在 body 又影响路由/权限/租户隔离，必须先拆角色：数据参数、路径作用域、运行时上下文、权限约束。
- 看到用名称正则判断语义，必须问：有没有元数据字段或类型可以表达这件事？如果没有，是否应该补模型？

母题归属：

- 字段位置决定语义。
- 不用名称猜事实。
- Guard 逻辑要有模型来源。

### C-009 Hologres 测试脚本可读性

来源：
- 会话：`019f01b4-ade8-7672-9456-a2002882769e`
- 文件：`/Users/houguanqun/.codex/sessions/2026/06/26/rollout-2026-06-26T10-14-06-019f01b4-ade8-7672-9456-a2002882769e.jsonl`
- 日期：2026-06-26
- 关联内容：Hologres integrate 失败，测试脚本重构

P哥原话：

- “我看了下 hologres 相关的测试脚本，一些逻辑和处理方式不是很直观，这里面除了 SQL 兼容性的问题之外有什么需要特别注意的吗？我打算把这块重构一下”

当时上下文：

- Hologres 集成测试失败，涉及 `test_01_folder_policy_enforces_object_mutations`。
- 相关测试脚本为了兼容 Hologres 有不少特殊处理。
- P哥不是直接问失败原因，而是问“除了 SQL 兼容性，还有什么需要特别注意”。

P哥真正抓的问题：

- 测试脚本也是可维护系统的一部分，不只是验证工具。
- Backend-specific 兼容代码如果不直观，未来重构时很容易删掉隐性约束。
- 要把 Hologres 差异分层：SQL 方言差异、权限/策略语义差异、数据可见性/事务差异、测试 harness 差异。不能把所有特殊逻辑都叫“兼容性”。

我们当时的 miss：

- 第一反应是修失败用例，没有先把 Hologres 特殊处理背后的契约分类。
- 没有把测试中不可删的业务约束写成注释或 helper 名称。

可迁移触发器：

- 看到测试脚本里有 backend-specific 分支，必须问：这是 SQL 方言、存储行为、权限语义、事务隔离，还是测试环境限制？
- 看到 reviewer 说“不直观”，不能只解释现状，要把隐性约束改成显性结构。

母题归属：

- 测试是契约文档。
- 兼容性必须分类，不许糊成一团。

### C-010 Object Storage M2M 的复用边界

来源：
- MR：`eos-core-svc!564`
- 日期：2026-07-21 至 2026-07-22
- 关联内容：Object Storage Admin / UserEdit 出站 M2M、IDaaS 配置与换票服务

P哥原话：

- “用已经存在的 core 的应用身份啊”
- “应该已经有获取 accessToken 的方法了”
- “为啥会有这两个 scripts？”
- “配置完全又搞了一套？”
- “不在这个文件里增加这几个方法”
- “在这里只提供 readObjectServiceConfig() 返回类型定义为 ObjectServiceConfig”
- “不需要增加这个 Options，就是 appId 那个参数传进去就好了”
- “不需要增加 manager”
- “除了 `src/access/idaas/idaas-config.service.ts` 增加配置之外，`src/access/idaas` 目录下的其他文件应当是不需要修改的”

当时上下文：

- 第一版为 Object Storage 单独增加了一套身份配置、换票服务和 CI 脚本，没有复用仓库已有 IDaaS 能力。
- 第一轮整改删除平行配置和脚本后，又为了让 Core App 走现有服务，在通用 `IdaasM2mAppService` 中增加了 `useCoreIdentity` Options、独立 TokenManager、失效接口，并在配置服务暴露多个零散 getter。
- 这些改动功能上能换到 token，也增加了安全测试，但把单一调用方的特殊处理扩散到了通用 IDaaS 抽象。

P哥真正抓的问题：

- “复用已有能力”首先意味着调用方适配现有契约，而不是给被复用的通用服务增加特殊分支。
- 配置应以一个有语义的类型整体返回：Object Storage 需要的是 `ObjectServiceConfig`，不是三个可被任意组合的底层 getter。
- 最小改动不只是文件数量少，还包括不扩大公共 Options、缓存、失效接口等 API 面。
- Reviewer 会直接给出合理的 diff 边界：这个需求在 `src/access/idaas` 下只应修改配置服务，其余变化属于事实所有权越界。

我们当时的 miss：

- 第一版把“新调用目标”误判成“需要新身份体系”。
- 第一轮整改虽然接受了复用方向，却仍假设 Core App 必须走特殊密钥路径，因而继续修改通用服务，没有先验证“只传已有 appId”是否已经成立。
- 把定向失效、独立 manager 等安全增强当成顺手补强，没有意识到它们同时扩大了本次需求的抽象边界和评审面积。
- 配置 getter 按字段拆分，暴露了底层存储细节，没有形成调用方真正需要的配置对象。

可迁移触发器：

- 看到“复用已有 service / method”，先尝试只改调用方参数；只有现有契约无法表达稳定的第二类通用场景时，才扩展 provider。
- 新增 Options、manager、cache、invalidate API 前，必须证明它是通用不变量或至少有多个真实消费者；否则留在调用模块，或直接不增加。
- 一个消费者总是成组读取多个配置字段时，优先提供有业务语义的 typed config，而不是散落 getter。
- 开工前写出“预计哪些目录/文件不应有 diff”；实现后按该负面清单检查，防止修复过程中扩大边界。

母题归属：

- 清除平行体系。
- 复用发生在正确的一侧。
- 最小改动同时约束公共 API 面。
- 配置类型表达消费语义。

### C-011 LinkType 关系模型不能按场景堆两套字段

来源：
- 会话：`019e0a73-74d7-7011-8998-8f5f419507d2`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/09/rollout-2026-05-09T09-56-39-019e0a73-74d7-7011-8998-8f5f419507d2.jsonl`
- 日期：2026-05-09
- 关联内容：LinkType relation metadata、外键关系与 backing object 多对多

评论原文 / 用户转述：

- “LinkType 还得起到 prisma 里的 relation 的作用”
- “这俩字段是不是跟 left_object_type_key 和 right_object_type_key 是重复的？”
- “这个看起来好像上下是两套？不会同时存在？”
- “这个表结构会有点奇怪，有没有可能可以融合到一套字段上的。”

当时上下文：

- 初版 LinkType 表同时存在 `foreign_key_*` 一组字段和 `through_*` 一组字段，分别服务一对多与多对多。
- 模型还额外保存左右对象 key、GraphQL 左右字段名等信息，其中一部分可由 ObjectType 主键或关系方向推导。
- 每一种关系模式继续加自己的 nullable 列，功能上能覆盖场景，但一行数据只有一组字段真正生效。

P哥真正抓的问题：

- LinkType 描述的是一个关系事实，不应把不同实现模式各自铺成一组互斥列。
- 可由 ObjectType 主键、关系方向或命名规则推导出的字段，不应再成为独立事实。
- 一对一、一对多、多对多的差异应由清晰的判别字段和结构化配置表达，而不是让调用方根据“哪几列非空”猜模型。

我们当时的 miss：

- 从 SQL 存储便利出发设计列，没有先写出统一的关系语义模型。
- 把“能覆盖所有 cardinality”当成完整，忽略互斥字段组带来的非法组合和理解成本。
- 没有区分关系身份、物理承载和 GraphQL 展示名三类事实。

可迁移触发器：

- 看到一张表按场景出现多组互斥 nullable 字段时，先问：是否缺少判别联合或统一引用结构？
- 看到 `left/right key` 与 ObjectType 主键同时存在时，先问：它是独立事实，还是可推导缓存？
- 看到关系模型同时保存物理外键、关系身份和 API 字段名时，必须拆清事实层、存储层和出口层。

母题归属：

- 一个事实只保留一种 canonical 形态。
- 互斥场景用结构建模，不用空值组合建模。
- 不保存可稳定推导的重复事实。

### C-012 Function 契约属于版本，跨对象引用只认稳定 RID

来源：
- 会话：`019e1705-4882-7441-9fba-619a2034f817`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/11/rollout-2026-05-11T20-31-22-019e1705-4882-7441-9fba-619a2034f817.jsonl`
- 日期：2026-05-12 至 2026-05-13
- 关联内容：Function / ActionType I/O、Function 多版本、Flow artifact 引用

评论原文 / 用户转述：

- “签名可是不同版本会不一样的”
- “function 背后不一定是 flow”
- “不能用 functionRid 或 logicRid 当做 flow 的 artifactId，应该每个 function 的 version 都对应不同的 artifactId”
- “方法签名一般是‘方法名定义 + 参数列表定义’，所以这里叫 signature 有点牵强，建议和 actiontype 保持一致：改成‘参数定义’和‘返回值定义’两部分，而且签名是与版本强相关的。”
- “在 JSON 结构里，有 Rid 的地方就不要对应的 ApiName 了吧，要不然 ApiName 改了的话还得扫描所有的 JSON 进行变更。”

当时上下文：

- 初版把 Function 的 `signature` 和 implementation 放在较稳定的 Function 层，又同时保存 `functionRid`、`functionApiName`、`flowArtifactRid` 等引用。
- 设计默认 Function 背后是 Flow，容易把 Function 的业务身份和某一版执行制品绑定在一起。
- 参数约束最初放在 `constraints`，后来准备改为可扩展的 `validations` 结构。

P哥真正抓的问题：

- 参数定义、返回值定义和实现制品都会随版本变化，必须属于 Function version，而不是稳定 Function 身份。
- Function 是能力契约，Flow 只是可能的实现类型；不能让一种实现反向定义 Function 模型。
- 每个版本必须指向自己的 artifact，不能用稳定 Function RID 冒充版本制品 RID。
- JSON 内部引用应使用稳定 RID；可变 ApiName 只影响 GraphQL 等出口名称，不应扩散为内部引用一致性负担。

我们当时的 miss：

- 把“签名”当作稳定 Function 属性，没有先追问参数和返回值是否会随版本变化。
- 从当前 Flow 实现反推 Function 模型，混淆能力身份、版本契约和执行制品。
- 为方便展示同时保存 RID 和 ApiName，制造了重命名时的全量扫描成本。

可迁移触发器：

- 看到 `version` 时，必须列出哪些字段随版本变化：输入、输出、校验、实现类型、制品引用、兼容信息。
- 看到稳定对象 RID 被当成 artifact RID 时，必须拆开“能力是谁”和“这一版执行什么”。
- 看到 JSON 同时保存 RID 与 ApiName 时，先问 ApiName 是否只是可查询的展示投影。

母题归属：

- 版本拥有会变化的契约。
- 能力模型不依附单一执行引擎。
- 稳定引用与可变名称分离。

### C-013 Action operations 是动作语义，Flow 是执行投影

来源：
- 会话：`019e0bd2-8921-7f41-8e32-8143518aaac6`、`019e1fef-767d-7af2-b22e-b0cf0b366230`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/09/rollout-2026-05-09T16-20-07-019e0bd2-8921-7f41-8e32-8143518aaac6.jsonl`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/13/rollout-2026-05-13T14-04-07-019e1fef-767d-7af2-b22e-b0cf0b366230.jsonl`
- 日期：2026-05-09 至 2026-05-14
- 关联内容：ActionType operations、Flow operator 转换、旧结构兼容

评论原文 / 用户转述：

- “Action 的 operations 下为什么会有 flow 这种类型，和 Palantir 对不上”
- “operations 应该是个数组”
- 对“旧对象形态只做读取兼容”的批示：“不做兼容”
- “运行时不需要新旧转换，但是可以成为研发工具，辅助我们自己改写当前的 JSON Config”
- “FLOW 的这种……就不提供了……别的同学已经处理的那些统一用 Function 类型来接。”

当时上下文：

- 初版把 `operations` 建模为 `{ type: "flow" }` 一类执行方式，并在 ActionType 上直接挂 Flow artifact。
- 另一种思路是让 objects 自己执行 operations 数组，这又会重复实现 Flow 的顺序、结果和失败语义。
- 为平滑切换，runtime bootstrap 一度加入旧 seed 到新 operations 的转换。

P哥真正抓的问题：

- `operations` 应先表达 Action 做哪些原子操作；Flow 是这些 operations 的编译或执行承载，不是 operation 本身的业务类型。
- objects 不应为了支持 operations 再复制一套 Flow 编排语义；转换可以发生，但权威模型必须清楚。
- 建设期可重建数据时，不要把一次性 JSON 改写工具塞进 runtime 形成永久兼容层。
- 不能自然表达为原子 operation 的复杂执行，应通过 Function 等已有能力接入，不再造一个裸 FLOW 特例。

我们当时的 miss：

- 从当前执行入口反推 metadata，把“怎么执行”写进“动作是什么”。
- 为了迁移方便扩展 runtime，而不是把转换留在研发工具或一次性数据改写阶段。
- 同时保留 operations、Flow config、Function 三条表达路径，没有先指定权威体系。

可迁移触发器：

- 看到领域模型字段直接用执行引擎名作为 `type`，必须问：这是业务语义还是部署投影？
- 看到 runtime 新增旧结构转换时，必须先确认存量是否真需在线兼容；若可重建，优先离线改写。
- 看到模块准备复制编排引擎的顺序、结果、失败语义时，立即回查统一执行模型。

母题归属：

- 领域定义与执行投影分离。
- 建设期不把迁移工具固化成 runtime 兼容层。
- 复杂能力回到已有统一模型。

### C-014 RID 不承载可变化的结构语义

来源：
- 会话：`019e4d6b-279b-7732-9336-0111bdadc281`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/22/rollout-2026-05-22T10-02-08-019e4d6b-279b-7732-9336-0111bdadc281.jsonl`
- 日期：2026-05-22
- 关联内容：RID 格式、branch identity、外部 ID 契约

评论原文 / 用户转述：

- “Palantir 的 rid 里有分支信息，照抄就要在分支操作时更新引用关系；在字符串里进行结构化是个 anti-pattern。”

当时上下文：

- 团队在讨论是否采用 Palantir 风格多段 RID，以提升可读性并把 branch 等语义编码进字符串。
- EOS 当前事实更接近 `rid + branchRid` 的组合定位，且还有 Space、Project 等不受 branch 管理的资源。
- 如果把 branch 写进 RID，分支迁移、merge、revert 都可能要求改写引用。

P哥真正抓的问题：

- 标识符的首要职责是稳定身份，不是承载当前层级、分支或类型解释。
- branch 是独立事实，应由独立字段或上下文表达；把它编码进 RID 会让关系变化变成身份变化。
- 可读性不能用引用维护成本交换。需要展示时可以查询元数据或构造外部展示 ID，但不能污染 canonical RID。

我们当时的 miss：

- 被多段 RID 的可读性吸引，没有先模拟分支变化时的引用更新。
- 试图用一种字符串格式同时覆盖分支资源和非分支资源。
- 没有区分稳定内部 RID、组合定位键和面向人的展示标识。

可迁移触发器：

- 看到 ID 中准备编码类型、父级、租户、分支、状态时，必须问：这些事实变化时 ID 是否也要变化？
- 看到“更可读的 ID”方案时，必须计算 rename/move/merge/revert 的引用改写成本。
- 需要组合唯一性时，优先使用独立列和复合约束，不把结构塞进字符串。

母题归属：

- 身份与位置分离。
- 不在字符串里模拟结构化模型。
- 可读投影不能成为 canonical identity。

### C-015 LinkType 应引用主资源身份，不引用分支 Detail 行

来源：
- 会话：`019e5cc8-0ef5-7cd0-8a25-4b555f0d51f2`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/25/rollout-2026-05-25T09-37-55-019e5cc8-0ef5-7cd0-8a25-4b555f0d51f2.jsonl`
- 日期：2026-05-25
- 关联内容：LinkType 引用、ResourceGlobalBranchDetail 复合 ID、反向关系查询

评论原文 / 用户转述：

- “所以 LinkType 不应该和 xxxxxResourceGlobalBranchDetail.id 产生关系，因为它不是主表，应该和 Resource、Function 这种主表的 ID 关联。”
- “至于将两个 ID 拼接在一起，是考虑到后续如果有数据加工场景不支持联合主键，可以通过这种方式准确路找到数据。”

当时上下文：

- 派生 Detail 行的真实主键曾改成 `id = globalBranchRid/rid`。
- LinkType 关系字段仍保存业务资源 RID，查询实现却一度拿 Detail 的复合 `id` 去匹配，导致反向关系查不到。
- 团队因此讨论是否应让 LinkType 改为引用 Detail 复合 ID。

P哥真正抓的问题：

- Resource / Function 主表拥有稳定身份；`...ResourceGlobalBranchDetail` 只是某一 branch 下的版本或投影，不应反客为主成为关系身份。
- 复合字符串 ID 是为不支持联合主键的数据加工场景提供的定位手段，不会因此升级为领域关系的 canonical target。
- 查询自身一行用什么主键，与领域关系引用谁，是两件事。

我们当时的 miss：

- 因为 Detail 表使用复合主键，就顺势让关系 join 也围绕复合主键设计。
- 混淆“数据库如何唯一定位一行”和“领域关系指向哪个实体”。
- 修查询 bug 时差点反向修改模型真相，而不是修正 join 的字段选择。

可迁移触发器：

- 看到 relation 指向 `Detail`、`Snapshot`、`Version`、`Projection` 表时，必须问稳定主实体在哪里。
- 看到复合主键或拼接 ID 时，必须区分存储定位键、兼容传输键和领域身份。
- 修 join 不匹配时，先验证关系事实来源，不能为了迁就当前主键改写模型。

母题归属：

- 关系指向事实所有者。
- 主实体身份与分支版本身份分离。
- 存储定位方式不定义领域关系。

### C-016 Core 提供 DDL 原子能力，不替上层定义流程

来源：
- 会话：`019e5ea5-b85a-7923-9cd4-1c2cd49eb218`、`019e61e7-de10-72e1-9312-2337c3ac26d6`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/25/rollout-2026-05-25T18-19-39-019e5ea5-b85a-7923-9cd4-1c2cd49eb218.jsonl`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/26/rollout-2026-05-26T09-30-46-019e61e7-de10-72e1-9312-2337c3ac26d6.jsonl`
- 日期：2026-05-25 至 2026-05-26
- 关联内容：ObjectType schema 变更、generate/execute DDL、safe/unsafe、metadata CUD

评论原文 / 用户转述：

- “这是个大坑啊，肯定不能简单地 drop 重建，这个问题要作为 P0 任务尽快解决，这是 core-svc 里最关键的技术点。”
- “文档和 MR 描述里讨论了大量的 safe/unsafe 以及生产非生产，这个味道不太对。”
- “生产和非生产是需要满足的需求场景，但是对于 core 来说没有这个概念，而是是否提供增强流程控制的口子；对于 core 来说原子能力是实现的目标，流程控制不在 core 的职责范围之内。”
- “在 core 这一层不要担心执行失败，core 的任务是提供可能性。”
- “columnName 这块我们就不处理了……它主要是上游 backing Dataset 用的。”
- “针对 create/update/deleteObjectTypeResourceGlobalBranchDetail 这种 GraphQL CUD……只是写入 ObjectTypeResourceGlobalBranchDetail 行……没有这个表会报错，这不是我们关心的，就应该报错。”

当时上下文：

- 为保护数据，初版 DDL 方案引入 `SAFE_ONLY / ALLOW_UNSAFE`、生产/非生产策略、schema activation 状态和 apply 流程。
- `generateDDL`、`executeDDL` 与 GraphQL metadata CUD 一度被捆成一条事务编排链。
- 方案还试图管理 `columnName` rename，但该字段主要属于上游 backing Dataset。

P哥真正抓的问题：

- Core 应提供 compile / validate / execute 等可组合原子能力，说明变更和失败；是否批准、何时执行、怎么重试属于上层流程。
- “可能失败”不是 Core 收紧能力的理由。只要契约允许，上层可用自然失败建立自己的流程控制。
- Metadata CUD 与物理 DDL 是不同原子动作，不应为了制造一次“完整激活”把二者硬绑在 Core 内。
- Core 不能接管上游字段所有权；`columnName` 属于 backing Dataset，就不应在 ObjectType 变更里擅自 rename。

我们当时的 miss：

- 把运维环境和审批策略写进 Core 契约，试图让底层同时成为编排器。
- 为了“一次调用完整成功”把 metadata write、DDL、风险策略和状态机揉成一个 apply。
- 把 fail-close 理解成拒绝提供能力，而不是清晰暴露失败语义。
- 没有先确认 `columnName` 的事实所有者。

可迁移触发器：

- 看到底层模块出现 prod/dev、审批、队列、轮询、重试状态时，先问它是否越过原子能力边界。
- 看到一个 API 同时改 metadata 和外部物理资源时，必须证明二者属于同一事实与事务；否则拆成原子操作。
- 看到“为了避免失败所以禁止能力”时，先问能否用明确错误把流程选择留给上层。
- 看到 rename 时，先确认名字由谁拥有、谁有权修改。

母题归属：

- Core 定义能力，不定义使用流程。
- 原子能力与上层编排分离。
- 失败是契约结果，不自动等于能力不应提供。
- 事实所有权决定修改权。

### C-017 GraphQL schema 来自 metadata，不来自物理表

来源：
- 会话：`019e2975-d06c-7df0-9dde-b31f3952dbb3`
- 文件：`/Users/houguanqun/.codex/sessions/2026/05/15/rollout-2026-05-15T10-27-27-019e2975-d06c-7df0-9dde-b31f3952dbb3.jsonl`
- 日期：2026-05-15 至 2026-05-20
- 关联内容：GraphQL introspection、0 号本体、业务本体、branch/schema routing

评论原文 / 用户转述：

- “当前热载的暴露 GraphQL introspection 的过程是直接从表里搞的，直接读的底表，不要这样。”
- “应该从 0 号本体的 OT Detail 里的元数据信息（property）去映射出对应的 GraphQL。”
- “所有元数据的 schema 要从 0 号本体里出出来，而业务数据 schema 要从非 0 号本体出来。”
- “这个流程说明里一定要详细到如何得到表名、如何定位到某一行等这种细节，要不容易逻辑模糊。”
- 对 `resourceKind` 的质疑：“resourceKind 也是 resourceRid 吧？”

当时上下文：

- GraphQL schema 热载曾根据底层表结构生成，数据库 `jsonb` 等物理类型会直接影响 API 形态。
- 设计文档又增加 `resourceKind`、表级 ontology 定位等中间概念，却没有完整写出从请求到 registry、物理表、Detail 行的真实查找链。
- 当 metadata 已存在而业务表尚未创建时，团队倾向于不暴露 schema，避免查询失败。

P哥真正抓的问题：

- GraphQL 暴露的是本体定义，不是数据库当前长什么样；metadata 才是 schema 权威来源。
- 物理表尚未 ready 可以让业务查询自然失败，但不能反向让物理 readiness 决定定义是否存在。
- 路由文档必须闭环到真实定位键、表名和行，不能靠 `resourceKind` 这类未落地概念跳步。
- 元数据控制面和业务本体的数据面要分层，但每一层的事实来源必须唯一。

我们当时的 miss：

- 用数据库 introspection 省去 metadata 映射，导致存储实现反向定义 API。
- 把“查询可能报错”当成“不应暴露 schema”，混淆定义可见与执行就绪。
- 文档只画抽象 target，没有验证每一步在真实表结构中如何实现。

可迁移触发器：

- 看到 API schema 从物理表 introspection 生成时，必须问是否绕过了领域 metadata。
- 看到 readiness 决定 schema 可见性时，必须区分定义存在、制品就绪和执行成功。
- 看到路由设计出现抽象键时，必须用一个真实请求走到具体表名、主键和目标行。

母题归属：

- Metadata 是 API schema 的事实来源。
- 定义可见与物理就绪解耦。
- 抽象路由必须能还原到真实定位链。

### C-018 跨仓模型变更先改定义仓，再 handoff 到实现仓

来源：
- 会话：`019e9049-36d5-7553-8326-765281f46ea2`、`019e95cc-cdc6-7b60-8cb4-50b12d5beee4`
- 文件：`/Users/houguanqun/.codex/sessions/2026/06/04/rollout-2026-06-04T09-39-37-019e9049-36d5-7553-8326-765281f46ea2.jsonl`
- 文件：`/Users/houguanqun/.codex/sessions/2026/06/05/rollout-2026-06-05T11-21-27-019e95cc-cdc6-7b60-8cb4-50b12d5beee4.jsonl`
- 日期：2026-06-04 至 2026-06-05
- 关联内容：Issue 108、`valueType -> dataType`、eos-index / eos-core-svc 交付顺序

评论原文 / 用户转述：

- “这个修改得先改 eos/eos-index 里的文档，handoff 之后再改 eos/svc/eos-core-svc。”

当时上下文：

- `valueType -> dataType` 同时影响 eos-index 的本体定义/handoff 和 eos-core-svc 的 runtime、SQL、Flow config、存量数据。
- 如果 Core 先改，Index 的设计与 submodule 仍指向旧契约；如果只改 Index，集成测试又会因为 Core 尚未实现而失败。
- 最终交付需要定义先落位、实现依据 handoff 修改、实现合入后再刷新 Index 对 Core 的引用。

P哥真正抓的问题：

- 跨仓变更必须遵守契约所有权：定义仓先声明目标形态，实现仓消费 handoff，而不是两个仓各自猜同一个变更。
- “先改文档”不是文档流程主义，而是在建立后续代码、迁移和测试共同引用的版本化契约。
- CI 依赖顺序可以通过分阶段 MR 和引用更新解决，不能反过来取消事实所有权顺序。

我们当时的 miss：

- 容易把两个仓的改动当成同时机械替换，忽略谁先定义、谁后消费。
- 看到 Index pipeline 依赖 Core 时，差点把 pipeline 拓扑误认为契约所有权。
- 最初只盯 ObjectType properties，后来才发现 Flow config、UI schema、preview input 等嵌套存量也消费旧字段。

可迁移触发器：

- 看到跨仓字段或模型重命名时，先画：定义仓、handoff、实现仓、引用仓、存量迁移的顺序。
- 看到下游 CI 必须等待上游实现时，使用 staged MR / refs 更新解决，不改变契约归属。
- 迁移前按语义全局扫描所有消费者，不能只改最显眼的那张表或一个 JSON 路径。

母题归属：

- 契约所有权决定交付顺序。
- Handoff 是跨仓事实边界。
- Pipeline 依赖不定义模型归属。

### C-019 PostgreSQL / Hologres 是互斥 backend，不是主库加外挂

来源：
- 会话：`019e904c-f5ab-7c80-94e9-e0e69c2fd3c0`
- 文件：`/Users/houguanqun/.codex/sessions/2026/06/04/rollout-2026-06-04T09-43-43-019e904c-f5ab-7c80-94e9-e0e69c2fd3c0.jsonl`
- 日期：2026-06-04
- 关联内容：Hologres runtime backend、PG/Hologres 分流、Core 定位

评论原文 / 用户转述：

- “Hologres 和 PG 是同等地位的，而且是互斥的。”
- “在运行服务中，要么就是 PG，要么就是 Hologres，不会同时存在；只是有的地方必须用 PG，有的地方必须用 Hologres。”

当时上下文：

- 初版理解是 Core runtime metadata 继续固定走 PG，Hologres 只承载分析侧 Object Database，像一个外挂 AP 数据源。
- 这会让同一运行服务内长期存在两套存储路径，并让代码根据表或场景动态猜 backend。
- 实际目标是不同部署选择不同 backend，而不是单个部署同时拼装 PG 主路径和 Hologres 特例路径。

P哥真正抓的问题：

- PG 与 Hologres 是同一 storage port 的不同实现，架构关系是替换，不是主从叠加。
- backend 选择属于部署配置；业务代码应依赖统一端口，不应在运行过程中四处判断“这张表去哪里”。
- 只有底层差异进入 adapter；Core 的 ObjectType、Query、DDL 能力契约不因部署选择分裂成两套。

我们当时的 miss：

- 从现状“metadata 已在 PG”推导出永久架构，把迁移阶段的事实当成目标边界。
- 将 Hologres 视为附加能力，准备增加大量局部分流判断。
- 没有先确认 backend 是按请求、按表还是按部署选择。

可迁移触发器：

- 看到第二种存储接入时，先问它与第一种是替换、分片、主从、冷热分层还是双写，不能默认“外挂”。
- 如果 backend 在一个部署内互斥，必须用统一 port + 配置选实现，禁止业务层散落分支。
- 设计 adapter 前，先锁定选择粒度：部署、租户、表、请求还是操作。

母题归属：

- 可替换 backend 共享一个能力契约。
- 部署配置与业务语义分离。
- 迁移现状不能冒充目标架构。

### C-020 string 内部表示不需要再造 typed-bytes 协议

来源：
- GitLab MR：`eos-core-svc!521`
- 评论：`src/objects/security/object-plaintext-codec.ts:39`
- 日期：2026-07-23
- 关联内容：LiKey 加解密、属性类型到 bytes 的转换

评论原文：

- “如果值的内部表示已经使用 string 了，那其实就没有必要再按不同类型序列化为 bytes 了。原来提出要以 bytes 存储是因为原生类型的内部表示是 bytes 序列，以 bytes 的方式进行存储能够保存最原始的信息。如果内部存储都以 string 来存储取，那就还是以 string 的 bytes 来加解密就好了”
- 后续评论：“哦，plaintext 和 ciphertext 那也直接 string 吧。之前我说的只需 string 的 bytes，是指类的内部不需要区分数据类型了”

当时上下文：

- Object 加密链路在进入 LiKey 前，已经把 BOOLEAN、数值和 JSON-like 值规范化成 string。
- 初版整改又根据 schema 把这些 string 反向解析成 BOOLEAN byte、定长整数、IEEE-754 和 DECIMAL unscaled integer bytes，解密后再按 schema 解释回来。
- 这套 codec 新增了大量类型规则、测试向量和集成测试，但没有保存 string 之前已经丢失的“原生内部表示”。

P哥真正抓的问题：

- bytes 只有在承接上游真实原生表示时才保留了额外信息；从 canonical string 反向构造 typed bytes，只是增加第二套序列化协议。
- 序列化边界必须服从当前事实形态。当前事实是 string，就直接使用该 string 的 UTF-8 bytes 加解密。
- `plaintext` / `ciphertext` 在加解密端口和类内部仍应保持 string；UTF-8 bytes 与 Base64 转换属于 LiKey HTTP adapter 的传输职责，不应扩散成业务端口类型。
- 不能因为目标方案里出现“bytes”，就假设每种类型都必须拥有一套二进制布局；转换本身必须带来真实信息增益。

我们当时的 miss：

- 顺着“不同数据类型有不同的 bytes 转换方式”展开设计，没有先核实进入加密层时值的实际内部表示。
- 把跨语言、精度和 canonical 等问题都压进新 codec，扩大了 MR，却没有改变现有 GraphQL 或存储事实。
- 第一次删掉 typed codec 后仍把 `EncryptionServicePort` 改成 `Uint8Array`，说明只撤回了“按类型编码”，没有把 string 事实贯彻到端口边界。
- 用大量 round-trip 测试证明自建协议内部自洽，没先证明这套协议有必要存在。

可迁移触发器：

- 看到“转换为 bytes”时，先沿调用链确认源值此刻究竟是原生值、driver bytes，还是已经规范化的 string。
- 如果上游已经完成有损或规范化转换，禁止在下游反向发明一套 typed-bytes 协议来伪装“保留原始信息”。
- 新增序列化层前必须回答：它比当前 canonical 表示多保留了什么信息；如果答案是“没有”，直接复用当前表示的 bytes。
- 端口类型表达领域内部事实，adapter 才表达外部协议。业务内部是 string 时，不要仅因外部请求使用 Base64 就把端口改成 bytes。
- 看到大批 golden vectors 只验证新 codec 自己的 encode/decode 时，必须先问这个 codec 是否应当存在。

母题归属：

- 事实形态决定序列化边界。
- 不重复已经完成的类型转换。
- 复杂度必须换来真实信息增益。

### C-021 加密脱敏 MR：不能拿冻结的 spec 替代模型审查

来源：
- GitLab MR：`eos-core-svc!586`
- 评论位置：
  - `_bmad-output/implementation-artifacts/spec-234-encrypted-masked-read-plaintext.md:22`
  - `_bmad-output/implementation-artifacts/spec-234-encrypted-masked-write-storage.md:15`
  - `_bmad-output/implementation-artifacts/spec-234-encrypted-masked-write-storage.md:21`
  - `_bmad-output/implementation-artifacts/spec-234-encrypted-masked-write-storage.md:23`
- 日期：2026-07-28
- 关联内容：encrypted 字段持久化脱敏值、GraphQL `maskedValue/plaintextValue`、Access Policy、blind index

评论原文：

- “我感觉应该不需要单独的 plaintextRule，因为除了这个 rule 也没有别的 rule 了吧？加密字段和其他字段的区别是只支持判等，不支持针对 plantext 的非判等判断（这个逻辑是 __hash 物理字段支持的）”
- “这个 query token 是啥？”
- “还有个显示长度的规则：是按照固定长度来 mask，还是按照 plaintext 的长度来 mask”
- “因为内部都是 string 展示，其实bool、整型和 decimal 的脱敏也就支持了？”

当时上下文：

- 需求要求普通查询默认返回持久化脱敏值，只有调用方明确选择 `plaintextValue` 时才允许进入解密链路。
- 我们把“明文需要单独的权限控制点”推导成新的 `plaintextRule` 字段，并在 policy definition、validator、runtime result、query/relation 传递中建立了一条平行权限通道。
- 写入和读取 spec 又把能力冻结为“仅 encrypted String”，尽管现有加密入口已经会把 Boolean、数值、Decimal 和 JSON-like 值转换成 canonical string。
- mask 算法默认按明文 Unicode code point 数量生成同长度掩码，但固定长度还是跟随明文长度没有经过产品确认。
- `queryToken` 是既有内部命名，实际值由 HMAC 生成、持久化到 `__blind_idx` 并服务 `eq/in`；MR 文档没有解释它与 blind index / `__hash` 的关系。
- MR 共修改 52 个文件、约 3472 行，并通过 2549 个 Jest 用例及 PostgreSQL、Hologres、LiKey 门禁。内部 review 曾据此给出 Clean 结论。

P哥真正抓的问题（根据评论归纳，不是原话）：

- “独立控制点”不自动等于“再增加一个可配置规则字段”。如果既有 `rule` 已能唯一表达字段授权，显式 selection、解密调用和审计可以是独立运行时路径，但不应再造第二个 authoring truth。
- encrypted 与普通字段的稳定差异首先是查询能力：明文不能直接参与非等值判断，等值查询由 hash / blind index 投影承接；不需要为此再复制一套 field rule。
- 脱敏展示消费的是 canonical string，Boolean、Integer、Decimal 是否能脱敏，不应被原始 `dataType` 的分支人为限制；类型差异主要体现在 `plaintextValue` 的恢复和 GraphQL 输出类型。
- mask 显示长度是会影响信息泄漏和业务展示的策略语义，不是实现者可以默默选定的循环边界。
- 名称必须让评审者和调用方知道它表示什么。`queryToken`、blind index、`__hash` 指向同一能力时，必须统一主名并明确物理映射，不能依赖内部口头知识。

我们当时的 miss：

- **权威倒置**：先把自己的推导写进 `frozen-after-approval`，再让 review 以 spec 为正确答案。review 验证了代码是否符合 spec，却没有验证 spec 是否符合原始沟通。
- **对象审错**：重点检查了权限旁路、投影、后端一致性和测试，没有对 `plaintextRule` 这个新增模型字段先做“删掉会不会丢失信息”的存在性审查。
- **减法做反**：该删除的平行权限字段被保留；本可复用 canonical string 的非 String 类型反而被砍掉。把“不要过度设计”误解为减少交付范围，而不是减少概念和分叉。
- **切片造成假闭环**：写入 spec 被当成已经结案的第一切片，最终整体 review 实际集中在后续读取链路；P哥的三条评论恰好落在此前被视为已冻结的写入 spec。
- **测试替代判断**：大量测试只能证明错误前提被一致实现，不能证明前提本身正确。
- **未决项伪装成事实**：mask 长度没有证据，也没有标为 decision-needed，却被直接写成“按明文长度”。
- **错误背书**：在未经 P哥本人确认时，spec 写了“按 P哥复审”“按 P哥标准复核”，把内部推断包装成了外部认可。

可迁移触发器：

- 看到 `frozen`、`approved`、`locked` 一类标记时，先逐项列证据：P哥/用户直接确认、Issue 明确要求、现有代码事实、还是 Codex 推导。最后一种只能标为待确认，不能冻结。
- 每新增一个 policy 字段、结果列表、selection 参数或并行传递链，先做删除测试：删掉它后，能否由现有 rule + 请求意图 + 运行时状态唯一推导？能则删除。
- “不要过度设计”必须同时做两次检查：有没有增加新概念；有没有用缩小类型范围掩盖本来可以自然复用的完整能力。
- review 至少分两遍：第一遍只审 Issue/spec/公共模型，不看测试绿不绿；第二遍才审实现、边界和测试。第一遍不通过，禁止进入第二遍的 Clean 结论。
- 测试报告必须分成两句话：“契约依据已确认”和“实现符合契约”。只能证明后一句时，不得写“整体 review 通过”。
- 多切片 MR 的最终 review 必须重新审全部切片的公共契约，不能把早期 spec 当作可信基线。
- “按 P哥标准”只能描述使用了哪组检查动作，不能写成“P哥已复审”；只有真实评论或明确确认才能归因给 P哥。

母题归属：

- 冻结是变更控制，不是真值证明。
- 先审模型，再审实现。
- 减法减少的是概念，不是完整性。
- 测试证明一致性，不替代需求判断。
- 独立控制点不等于第二事实源。

### C-022 静态配置不应混入动态 Secret 缓存

来源：
- 用户转述的 P哥私下留言（两张截图）
- GitLab MR `eos-core-svc!521` 后续评论
- 关联 MR：`eos-core-svc!521`
- 代码位置：`src/access/idaas/idaas-secret-provider.service.ts`
- 日期：2026-07-28、2026-07-29
- 关联内容：Core M2M 静态 Secret、动态 IDaaS Secret、`getCachedSecret`、`materialized`

评论原文与用户转述：

- “这个 `shouldMaterialize` 的参数其实不必要添加。”
- “这里的这个静态配置的 secret 不用进入 cache，内部 cache 只用来缓存那些动态获取的。”
- 后续 GitLab 评论：“跟 `getServiceSecret` 一样的写法就可以吧。放到 materialized 里，后面的getMaterializedSecretSingle/getMaterializedSecretMultiple 都不用特殊逻辑处理”

当时上下文：

- `getCachedSecret` 原本负责远程动态 Secret 的 Promise 去重、TTL 和同步物化结果。
- 为支持 Core App 的 `auth.clientSecret`，实现把静态配置 Secret 也写入 `materialized`，并删除同 key 的动态 cache。
- 为避免进行中的动态请求稍后覆盖静态 Secret，又给通用 `getCachedSecret` 增加了 `shouldMaterialize` 回调。
- 于是一个本可直接读取配置的分支，反过来污染了动态缓存抽象，并新增了身份切换竞态测试来证明补丁参数有效。
- 第一轮整改又把“不进入 cache”误解成“不进入 materialized”，让同步 getter 直接读取 Apollo 配置，新增了第二套取值路径。

P哥真正抓的问题：

- 静态配置和动态远程结果有不同的事实来源与生命周期，不应放入同一个 cache。
- `cache` 与 `materialized` 不是同一个职责：前者只负责动态请求的 Promise 去重和 TTL；后者是异步获取完成后交给同步 SecretLoader 的已加载快照，静态和动态 Secret 都可以写入。
- 静态 Secret 应在 `getServiceSecret` / `getM2mAppSecret` 中从当前配置读取并写入 `materialized`；`getMaterializedSecretSingle` / `Multiple` 只按既有 key 读取快照，不应再理解配置来源。
- `shouldMaterialize` 不是通用能力，而是混合两类来源后产生的补偿参数。正确动作是恢复边界，不是让公共缓存方法理解更多例外。
- 配置轮换通过下一次异步 getter 重新物化生效，不需要让同步 getter 实时读取配置，也不需要通过动态 cache 模拟。

我们当时的 miss：

- 未确认“同一 key 在运行时切换静态/动态身份”是否为当前需求，就围绕这个假设场景增加条件参数。
- 把避免旧 Promise 覆盖静态值当成并发问题，却没有先问静态值为什么会进入动态缓存。
- 测试数量随补偿逻辑增长，但测试证明的是复杂分支自洽，不是缓存边界正确。
- 第一轮修正把两个 Map 概念混成了一个“缓存”，删除 `materialized` 写入后又让同步 getter 直读配置，说明只做了词面替换，没有先定义两个容器的职责。

可迁移触发器：

- 每向 cache 放入一种新来源的数据，先核对它是否和现有成员共享获取方式、失效条件与权威来源；任一不同就应先分流。
- 看到多个 Map 时先分别写出职责，不要因它们都驻留内存就统称为 cache；请求缓存与同步消费快照可以接纳不同来源。
- 公共方法新增 `shouldXxx` / `skipXxx` 回调来照顾单个调用方时，先做删除测试：调用方能否在进入公共方法前直接处理例外。
- 静态配置已有热更新或环境覆盖机制时，不要复制进带 TTL 的动态请求 cache；若下游 SDK 只能同步取值，则在异步边界完成一次明确物化。
- 修竞态前先检查竞态是否由错误共享状态制造；能删除共享状态时，优先删除。

母题归属：

- 不同事实来源不共享同一缓存语义。
- 请求缓存与消费快照必须分清。
- 删除补偿参数，恢复单一职责。
- 配置是静态凭证的权威来源。

## 4. 来源审计与结案索引

以下 35 个候选会话与后续 GitLab MR 来源均已逐条审计。状态只允许三种：

- **已入库**：有足够原话和上下文，已形成独立案例。
- **已并入**：有价值，但与已有案例同一母题，不重复造案例。
- **已排除**：只有 Codex 自评、普通实施/咨询、二手概述不足以闭环，或关键证据只存在于已不可访问的图片中。

| 会话文件 | 审计结论 | 去向 / 原因 |
| --- | --- | --- |
| `2026/04/17/rollout-2026-04-17T17-32-06-019d9ac8-86ea-78c1-be92-79f610f7db8e.jsonl` | 已排除 | submitBundle 与 bundle 模板实施会话，没有可确认的 P哥 comment。 |
| `2026/04/28/rollout-2026-04-28T17-13-25-019dd35d-6085-7103-8d53-4fde85bfabf7.jsonl` | 已排除 | 用户要求 Codex review objects 详设，属于自评与改稿，不是 P哥语料。 |
| `2026/04/29/rollout-2026-04-29T16-51-10-019dd86f-5e18-7590-bd07-4861fafdcf01.jsonl` | 已排除 | objects runtime 实施、demo、测试与 pipeline 跟进，没有 P哥原始 comment。 |
| `2026/05/04/rollout-2026-05-04T14-47-18-019df1bd-c322-77e2-8b4c-65268b540d3a.jsonl` | 已入库 | C-004：demo / 生产隔离、Function 表与 GraphQL 命名。 |
| `2026/05/06/rollout-2026-05-06T09-48-28-019dfaf8-e220-7320-8fb0-e0c231ba9ac8.jsonl` | 已入库 | C-005、C-006：CUD ActionType 与 Flow artifact。 |
| `2026/05/07/rollout-2026-05-07T14-16-42-019e0114-d194-78c0-a3bc-9eb7308f5bb4.jsonl` | 已排除 | 只有“老板建议数据库生成 UUID v7”的用户转述，缺少原始评论、diff 和后续 review 闭环，暂不神化为原则。 |
| `2026/05/08/rollout-2026-05-08T14-00-39-019e062c-7ed8-7e02-8b3b-2b169304bcc8.jsonl` | 已排除 | branch resource orchestration 修复、测试、MR 流程，没有 P哥 comment。 |
| `2026/05/09/rollout-2026-05-09T09-56-39-019e0a73-74d7-7011-8998-8f5f419507d2.jsonl` | 已入库 | C-011：LinkType 关系模型与重复字段。 |
| `2026/05/09/rollout-2026-05-09T16-20-07-019e0bd2-8921-7f41-8e32-8143518aaac6.jsonl` | 已入库 | C-013：Action operations 与 Flow 执行投影。 |
| `2026/05/11/rollout-2026-05-11T20-31-22-019e1705-4882-7441-9fba-619a2034f817.jsonl` | 已入库 | C-012：Function 版本契约与稳定 RID 引用。 |
| `2026/05/13/rollout-2026-05-13T14-04-07-019e1fef-767d-7af2-b22e-b0cf0b366230.jsonl` | 已并入 | C-012、C-013：不做 runtime 兼容、validations、Function / Flow 边界。 |
| `2026/05/15/rollout-2026-05-15T10-27-27-019e2975-d06c-7df0-9dde-b31f3952dbb3.jsonl` | 已入库 | C-017：metadata 驱动 GraphQL schema 与真实路由闭环。 |
| `2026/05/18/rollout-2026-05-18T15-11-01-019e39ec-801f-7b11-8309-b51d8a6138c2.jsonl` | 已排除 | MR 113 中只有 Codex 自评 finding，没有 P哥原始 comment。 |
| `2026/05/19/rollout-2026-05-19T10-06-48-019e3dfc-59e8-76b0-847d-5c50c8419257.jsonl` | 已排除 | Issue 66 方案、实施和用户自带 review 清单；其中“读写路由一致”只有二手引用，缺少原始语境。 |
| `2026/05/21/rollout-2026-05-21T10-45-01-019e486c-0daa-7711-bd49-8f63a847662d.jsonl` | 已排除 | `plural_api_name` 是用户方案且随后撤回，无法确认来自 P哥。 |
| `2026/05/22/rollout-2026-05-22T10-02-08-019e4d6b-279b-7732-9336-0111bdadc281.jsonl` | 已入库 | C-014：RID 不编码 branch 等结构语义。 |
| `2026/05/25/rollout-2026-05-25T09-37-55-019e5cc8-0ef5-7cd0-8a25-4b555f0d51f2.jsonl` | 已入库 | C-015：关系引用主资源身份，不引用 Detail 行。 |
| `2026/05/25/rollout-2026-05-25T18-19-39-019e5ea5-b85a-7923-9cd4-1c2cd49eb218.jsonl` | 已入库 | C-016：DDL 不能 drop 重建；compile 与 execute 分离。 |
| `2026/05/26/rollout-2026-05-26T09-30-46-019e61e7-de10-72e1-9312-2337c3ac26d6.jsonl` | 已并入 | C-016：Core 原子能力、流程归属、metadata CUD 与 DDL 解耦。 |
| `2026/05/28/rollout-2026-05-28T17-39-18-019e6df3-db13-7411-bf64-e23c4af4707b.jsonl` | 已排除 | “缺少语义类型/订阅能力”是架构输入和后续讨论，不是针对具体方案或 diff 的 review 闭环。 |
| `2026/06/01/rollout-2026-06-01T09-52-43-019e80e2-2136-76b2-aa2a-cfa78395f899.jsonl` | 已并入 | C-007：Type / ValueType、派生 kind、driver / schema 职责；其余为同一母题的多轮 comment。 |
| `2026/06/04/rollout-2026-06-04T09-39-37-019e9049-36d5-7553-8326-765281f46ea2.jsonl` | 已入库 | C-018：先改定义仓，handoff 后改实现仓。 |
| `2026/06/04/rollout-2026-06-04T09-43-43-019e904c-f5ab-7c80-94e9-e0e69c2fd3c0.jsonl` | 已入库 | C-019：PG / Hologres 是互斥 backend。 |
| `2026/06/05/rollout-2026-06-05T11-21-27-019e95cc-cdc6-7b60-8cb4-50b12d5beee4.jsonl` | 已并入 | C-018：与 06-04 会话为同一 Issue 108 / handoff 链路的继续执行。 |
| `2026/06/05/rollout-2026-06-05T13-51-55-019e9656-8d75-75e2-b82a-f7c794eee170.jsonl` | 已入库 | C-003：最小运行时、高码依赖与 SQL 拆分。 |
| `2026/06/08/rollout-2026-06-08T17-13-44-019ea682-67ff-7283-a054-663766d75889.jsonl` | 已入库 | C-007：ValueType / RuntimePropertyDefinition 形态。 |
| `2026/06/15/rollout-2026-06-15T14-06-48-019ec9e3-c63b-7940-885f-d14826cdc6da.jsonl` | 已入库 | C-008：Ontology edit endpoint guard。 |
| `2026/06/16/rollout-2026-06-16T09-38-02-019ece14-135c-7302-b46b-2b5c2b719adf.jsonl` | 已排除 | 关键内容只在已不可访问的截图中，文字仅说“包括之前 P哥要求”，无法可靠还原原话。 |
| `2026/06/17/rollout-2026-06-17T14-37-31-019ed44c-9f4b-7b83-b133-1bdb283808a2.jsonl` | 已入库 | C-002：Operator 鉴权与最小 scopes。 |
| `2026/06/22/rollout-2026-06-22T12-05-05-019eed80-dc79-7003-8097-975bc0e37b74.jsonl` | 已排除 | Action / Function return type 的用户咨询与实现，没有 P哥原始 comment。 |
| `2026/06/23/rollout-2026-06-23T10-27-24-019ef24d-c936-7c81-9dec-384d534b8923.jsonl` | 已并入 | 作为 C-003 的旁证：P哥追问高码 `Resource.trashStatus` 为何影响 route；缺少完整原始 thread，不独立成案。 |
| `2026/06/23/rollout-2026-06-23T14-28-17-019ef32a-534c-7b42-93f5-af6908931d11.jsonl` | 已入库 | C-001：Flow 异常到 GraphQL 错误契约。 |
| `2026/06/25/rollout-2026-06-25T09-32-25-019efc68-2a84-7a51-bdce-b845549df416.jsonl` | 已排除 | AI 协作方法文章的创作与 Codex/Claude 自评，不是 P哥具体 review 语料。 |
| `2026/06/26/rollout-2026-06-26T10-09-40-019f01b0-9f56-7c00-99d1-da38c15ce6e1.jsonl` | 已排除 | cognitive-os 评估与证据整理，和 P哥/EOS review 无关。 |
| `2026/06/26/rollout-2026-06-26T10-14-06-019f01b4-ade8-7672-9456-a2002882769e.jsonl` | 已入库 | C-009：Hologres 测试脚本可读性与兼容性分类。 |
| `eos-core-svc!521`（2026-07-23、2026-07-28、2026-07-29） | 已入库 | C-020：string 内部表示不需要再造 typed-bytes 协议；C-022：静态配置不进入动态 Secret cache，但仍由异步 getter 写入 `materialized`。 |
| `eos-core-svc!586`（2026-07-28） | 已入库 | C-021：冻结 spec 前提、平行 `plaintextRule`、mask 长度和非 String 复用。 |

## 5. 本轮新增的训练判断

35 个候选会话与后续 GitLab MR 来源结案后，可以看到 P哥 review 的几个稳定动作。这里记录的是跨案例反复出现的判断方式，不是把每条 comment 再换一种说法重复一遍。

晋升状态：

| 语料库判断 | 主文档处理 |
| --- | --- |
| 5.1 事实属于哪里 | 已由 A1 / A7 / R2 和第十一章“上下游”“事实模型”覆盖，暂不单独晋升 |
| 5.2 不接受功能上能走通 | 已晋升为主文档 11.11“功能-模型轴” |
| 5.3 命名是契约完整性 | 已由 A5 / 11.1 / 11.10 覆盖，后续案例足够多时再单独拆出 |
| 5.4 自动镜像要回到语义建模 | 已由 R2 / 11.5 / 11.11 覆盖 |
| 5.5 清除平行体系 | 已由 A1 / A5 / 11.1 / 11.10 覆盖 |
| 5.6 身份、位置和版本分离 | 已由 A2 / A5 / R2 覆盖；C-012、C-014、C-015 作为训练语料保留 |
| 5.7 Core 提供能力，上层定义流程 | 已由 A1 / A7 / 11.11 覆盖；C-016 作为 DDL 反例保留 |
| 5.8 定义可见与物理就绪解耦 | 已由 A4 / A7 / R4 覆盖；C-003、C-017 提供运行时案例 |
| 5.9 backend 关系必须先定性 | 已由 A1 / A7 / R2 覆盖；C-019 补充“替换而非外挂”案例 |
| 5.10 契约所有权决定跨仓顺序 | 已由 A1 / A5 / R2 覆盖；C-018 作为 handoff 案例保留 |
| 5.11 冻结不能替代验真 | 已补入主文档 10.11、10.12、11.12 与 12.6，作为 review 流程护栏；C-021 保留完整校准证据 |

### 5.1 他不是先问“能不能工作”，而是先问“事实属于哪里”

典型例子：

- `ontologyRid` 如果用于路由，就不该伪装成普通 body 参数。
- `serviceScopes` 是 M2M App 可申请范围，不是运行时请求 scopes。
- `ObjectType.properties` 是 runtime schema 权威来源，高码定义不是。
- `mask` 如果影响存储/展示治理，就不该随意放在 security 旁边。

训练触发器：

> 每看到一个字段，先不要问怎么用，先问它表示哪类事实：输入、路由、权限、存储、展示、派生、诊断、治理。

### 5.2 他不接受“功能上能走通”的成功

典型例子：

- 用宽泛 `serviceScopes` 拿 token 功能能走通，但最小权限错了。
- CUD ActionType 有 `flow_artifact_rid` 占位功能能建 schema，但真实 flow 不存在。
- GraphQL 能暴露 query，但 Query operator 没统一进 flow 模型。
- 应用层 cast 能让测试过，但可能重复了 driver 和 DB schema 的职责。

训练触发器：

> 每当方案说“可以先这样走通”，必须追问：它是不是绕过了应该存在的模型、artifact、权限边界或单一事实来源？

### 5.3 他把命名当成契约完整性

典型例子：

- `authUse` 如果实际是 request scopes，就应该叫 `requestScopes`。
- `OPERATOR_ACTION_INVOKE` 和新命名并存，必须确认废弃策略。
- `findManyCustomers` 这类 GraphQL 方法名要 lowerCamel，不是随意拼。
- `data/flows` 路径改名后，注释和脚本也要一起改。

训练触发器：

> 每看到名字不准确，不要当小建议。名字是调用方理解和未来实现的第一层契约。

### 5.4 他总是把“自动镜像”打回“语义建模”

典型例子：

- Action 参数不能机械镜像表字段。
- update 必填性不能机械来自 `NOT NULL`。
- RuntimePropertyDefinition 不能靠平铺字段一直扩。
- GraphQL schema 不能直接受高码初始字段影响。

训练触发器：

> 每当我们想从 A 自动生成 B，必须先写出 A 到 B 的语义规则。没有规则的自动生成，只是在复制复杂度。

### 5.5 他在 review 里不断清除“平行体系”

典型例子：

- demo 能力不能留在生产 `src`。
- Flow 的模块规则不能塞进 shared。
- Query 不能只有 GraphQL 特例，应该统一进 operator/flow。
- GraphQL 错误结构不能只有 Flow 自己的局部写法，必须回到 BaseError。
- Object Storage 需要换票时，应由调用方把 appId 传给现有 `getAccessToken`，而不是给通用服务再加身份 Options 和 manager。

训练触发器：

> 看到两个地方都能表达同一种能力，就必须问：哪个是权威体系？另一个是适配、缓存、demo，还是该删除？

### 5.6 他会把身份、位置、版本拆成三个问题

典型例子：

- RID 只表示稳定身份，不把 branch 编进字符串。
- `rid + branchRid` 可以定位版本，但 LinkType 仍应引用 Resource / Function 主身份。
- Function 的输入、输出和 artifact 属于 version，不属于稳定 Function 身份。
- ApiName 是可变出口名，不与 RID 一起复制进所有 JSON 引用。

训练触发器：

> 每看到一个 ID，分别问：它在标识谁、它现在位于哪里、它是哪一版。一个字段同时回答三个问题，通常就是耦合源。

### 5.7 他会把 Core 从“替大家做决定”拉回“提供可组合能力”

典型例子：

- DDL compile / validate / execute 是 Core 原子能力，生产审批、重试和发布状态属于上层。
- metadata CUD 可以只写定义；物理表不存在时查询报错，不需要 Core 伪造一套激活流程。
- “可能失败”不能成为删除能力的理由，失败类型本身就是契约的一部分。

训练触发器：

> 看到底层模块出现环境、审批、队列、轮询、重试和发布状态时，先问：这是能力不可缺少的语义，还是上层流程被下沉了？

### 5.8 他会区分“定义已经存在”和“执行制品已经就绪”

典型例子：

- GraphQL schema 来自 ObjectType metadata，不由物理表 introspection 决定。
- metadata 已存在而物理表未建，schema 仍可见；真正查询时可以明确失败。
- Action 声明使用 Flow 时，真实 artifact 必须存在；不能用占位 RID 冒充就绪。
- 高码初始定义不是 runtime schema 权威来源。

训练触发器：

> 对每项能力分别标记：定义是否存在、制品是否就绪、执行是否成功。不要用一个 `ready` 或一张物理表同时替代三种事实。

### 5.9 他会先定清两个 backend 的架构关系

典型例子：

- PG 与 Hologres 在目标架构中是互斥 backend，不是 PG 主路径加 Hologres 外挂。
- backend 按部署配置选择后，业务代码只依赖统一 port。
- driver / schema 已承担的类型行为，不在应用层再复制一套 cast。

训练触发器：

> 接入第二个存储、队列或执行引擎时，第一问不是“在哪里加 if”，而是两者究竟是替换、分片、主从、冷热分层还是双写。

### 5.10 他用事实所有权决定跨仓改动顺序

典型例子：

- `valueType -> dataType` 先在 eos-index 定义和 handoff 中落位，再由 eos-core-svc 实现。
- Core 合入后，Index 再刷新 submodule / refs，让 CI 对齐真实实现。
- Pipeline 先后依赖不会改变谁拥有契约定义。

训练触发器：

> 跨仓改一个模型时，先写出定义仓、handoff、实现仓、引用仓和存量迁移五个节点；不要把“哪个 pipeline 先绿”误当成“谁先定义事实”。

### 5.11 冻结不能替代验真

C-021 暴露的不是一个新架构母题，而是我们的 review 流程漏洞：把自己写的 spec 标成 frozen 后，后续审查者会自然地把它当作不可质疑的权威输入。

需要永久保留的区分是：

```text
需求事实：有直接评论、明确验收项或可核验代码事实支撑。
设计决策：在多个可行方案中已经获得人类确认。
实现假设：为了继续编码暂时选择，仍可能被推翻。
```

只有前两类可以冻结。实现假设必须显式标为 `decision-needed`，否则冻结动作只是把不确定性藏起来。

训练触发器：

> 每次准备写 `frozen/approved/locked`，逐条附证据来源；每次准备给出 Clean 结论，先脱离 spec 重新审一次 Issue、原始 comment 和新增公共字段。测试再多，也不能把实现假设升级成需求事实。

## 6. 后续维护协议

当前 35 个候选会话及已登记的 GitLab MR 来源已经结案，不再保留“下次再挖”的悬空清单。以后只有出现新的 MR comment、聊天原文或可访问截图时才追加：

1. 先登记来源，并标注“直接原话 / 用户转述 / Codex 推断”。
2. 只把直接原话或有完整上下文的可靠转述写进案例；图片不可访问时不得凭记忆补句子。
3. 过滤 token、密码、完整请求和内部账号密钥。
4. 补齐上下文、真正问题、我们的 miss、可迁移触发器，缺一项就先留在来源索引。
5. 与已有案例同一母题时更新原案例或标“已并入”，不为数量重复造案例。
6. 一个新母题至少出现 3 次，并且跨不同改动仍成立，再考虑反哺《架构师认知体系》。

结案原则：

> 没有证据的内容明确排除，比留下悬空项更完整；语料库的完整性是每条来源都有结论，不是每条来源都必须产出一条原则。
