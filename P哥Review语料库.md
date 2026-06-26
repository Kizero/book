# P哥 Review 语料库

这份文档不是新的原则手册，而是训练材料库。

主文档《架构师认知体系》沉淀稳定公理；本文件保存真实 review 语料、当时上下文、我们的 miss 和可迁移触发器。以后每补一条 P哥 comment，都优先补到这里；只有当多个案例反复指向同一个稳定模式时，再反哺主文档。

## 0. 抽取纪律

1. 原话优先。能保留 P哥原句时，不先改写成原则。
2. 每条语料必须带上下文。只记一句 comment 容易神化，必须说明当时改了什么、它为什么触发问题。
3. 记录 miss。comment 是答案，miss 才是我们和答案之间的距离。
4. 敏感信息不入库。历史会话里的 token、密码、完整 curl、内部账号密钥一律不保存。
5. 不把语料库当结论库。每条语料最后必须压成“下次 review 看到什么时触发什么问题”。

## 1. 本轮已确认的信息来源

已扫来源：

- `/Users/houguanqun/.codex/session_index.jsonl`
- `/Users/houguanqun/.codex/sessions/**/*.jsonl`
- `/Users/houguanqun/.codex/logs_2.sqlite`

本轮命中的候选会话文件约 35 个，第一批只入库已经能确认主题、原话和上下文的案例。剩余会话列在第 4 节，后续按“逐案校准”继续挖。

注意：关键词命中不等于 P哥语料。部分会话只是 Codex 自己做过 review，或者是我们转述“老板/P哥提到”但缺少原始 comment。此类内容只能先列为候选，不能直接写进“P哥原话”。

## 2. 案例模板

```md
## C-xxx <案例标题>

来源：
- 会话：
- 日期：
- 关联 MR / Issue：

P哥原话：
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

## 4. 待继续深挖的会话索引

以下是本轮关键词扫描命中的候选会话。它们还没有逐条完成“原话、上下文、miss、触发器”的闭环，后续应逐个补案例。

| 会话文件 | 已知主题 |
| --- | --- |
| `2026/04/17/rollout-2026-04-17T17-32-06-019d9ac8-86ea-78c1-be92-79f610f7db8e.jsonl` | eos-deploy-svc MR、submitBundle、bundle 模板模式 |
| `2026/04/28/rollout-2026-04-28T17-13-25-019dd35d-6085-7103-8d53-4fde85bfabf7.jsonl` | 待抽取 |
| `2026/04/29/rollout-2026-04-29T16-51-10-019dd86f-5e18-7590-bd07-4861fafdcf01.jsonl` | 待抽取 |
| `2026/05/04/rollout-2026-05-04T14-47-18-019df1bd-c322-77e2-8b4c-65268b540d3a.jsonl` | demo/生产隔离、Function 表、GraphQL 命名 |
| `2026/05/06/rollout-2026-05-06T09-48-28-019dfaf8-e220-7320-8fb0-e0c231ba9ac8.jsonl` | 预置 CUD ActionType、Flow artifact、data/flows |
| `2026/05/07/rollout-2026-05-07T14-16-42-019e0114-d194-78c0-a3bc-9eb7308f5bb4.jsonl` | 待抽取 |
| `2026/05/08/rollout-2026-05-08T14-00-39-019e062c-7ed8-7e02-8b3b-2b169304bcc8.jsonl` | 待抽取 |
| `2026/05/09/rollout-2026-05-09T09-56-39-019e0a73-74d7-7011-8998-8f5f419507d2.jsonl` | 待抽取 |
| `2026/05/09/rollout-2026-05-09T16-20-07-019e0bd2-8921-7f41-8e32-8143518aaac6.jsonl` | 待抽取 |
| `2026/05/11/rollout-2026-05-11T20-31-22-019e1705-4882-7441-9fba-619a2034f817.jsonl` | 待抽取 |
| `2026/05/13/rollout-2026-05-13T14-04-07-019e1fef-767d-7af2-b22e-b0cf0b366230.jsonl` | 待抽取 |
| `2026/05/15/rollout-2026-05-15T10-27-27-019e2975-d06c-7df0-9dde-b31f3952dbb3.jsonl` | 分支 Detail 表、迁移、global branch |
| `2026/05/18/rollout-2026-05-18T15-11-01-019e39ec-801f-7b11-8309-b51d8a6138c2.jsonl` | MR 113 review，当前看到的是 Codex 自评，需要继续找是否有 P哥原始 comment |
| `2026/05/19/rollout-2026-05-19T10-06-48-019e3dfc-59e8-76b0-847d-5c50c8419257.jsonl` | 待抽取 |
| `2026/05/21/rollout-2026-05-21T10-45-01-019e486c-0daa-7711-bd49-8f63a847662d.jsonl` | plural_api_name / GraphQL 复数命名，需要继续确认是否为 P哥原始观点 |
| `2026/05/22/rollout-2026-05-22T10-02-08-019e4d6b-279b-7732-9336-0111bdadc281.jsonl` | 待抽取 |
| `2026/05/25/rollout-2026-05-25T09-37-55-019e5cc8-0ef5-7cd0-8a25-4b555f0d51f2.jsonl` | 待抽取 |
| `2026/05/25/rollout-2026-05-25T18-19-39-019e5ea5-b85a-7923-9cd4-1c2cd49eb218.jsonl` | 待抽取 |
| `2026/05/26/rollout-2026-05-26T09-30-46-019e61e7-de10-72e1-9312-2337c3ac26d6.jsonl` | 待抽取 |
| `2026/05/28/rollout-2026-05-28T17-39-18-019e6df3-db13-7411-bf64-e23c4af4707b.jsonl` | 待抽取 |
| `2026/06/01/rollout-2026-06-01T09-52-43-019e80e2-2136-76b2-aa2a-cfa78395f899.jsonl` | objects 数据类型与索引方向 |
| `2026/06/04/rollout-2026-06-04T09-39-37-019e9049-36d5-7553-8326-765281f46ea2.jsonl` | Hologres 接入 |
| `2026/06/04/rollout-2026-06-04T09-43-43-019e904c-f5ab-7c80-94e9-e0e69c2fd3c0.jsonl` | Hologres 接入 |
| `2026/06/05/rollout-2026-06-05T11-21-27-019e95cc-cdc6-7b60-8cb4-50b12d5beee4.jsonl` | 待抽取 |
| `2026/06/05/rollout-2026-06-05T13-51-55-019e9656-8d75-75e2-b82a-f7c794eee170.jsonl` | 最小运行时、高码依赖、SQL 拆分 |
| `2026/06/08/rollout-2026-06-08T17-13-44-019ea682-67ff-7283-a054-663766d75889.jsonl` | ValueType、RuntimePropertyDefinition |
| `2026/06/15/rollout-2026-06-15T14-06-48-019ec9e3-c63b-7940-885f-d14826cdc6da.jsonl` | Ontology edit endpoint guard |
| `2026/06/16/rollout-2026-06-16T09-38-02-019ece14-135c-7302-b46b-2b5c2b719adf.jsonl` | Resource.trashStatus 等 |
| `2026/06/17/rollout-2026-06-17T14-37-31-019ed44c-9f4b-7b83-b133-1bdb283808a2.jsonl` | Operator 鉴权与 scopes |
| `2026/06/22/rollout-2026-06-22T12-05-05-019eed80-dc79-7003-8097-975bc0e37b74.jsonl` | 待抽取 |
| `2026/06/23/rollout-2026-06-23T10-27-24-019ef24d-c936-7c81-9dec-384d534b8923.jsonl` | Resource.trashStatus，已确认 P哥触发点，但缺少 route 过滤上下文 |
| `2026/06/23/rollout-2026-06-23T14-28-17-019ef32a-534c-7b42-93f5-af6908931d11.jsonl` | Flow 异常契约 |
| `2026/06/25/rollout-2026-06-25T09-32-25-019efc68-2a84-7a51-bdce-b845549df416.jsonl` | AI 协作方法论、DMS/DCS 迭代 |
| `2026/06/26/rollout-2026-06-26T10-09-40-019f01b0-9f56-7c00-99d1-da38c15ce6e1.jsonl` | 待抽取 |
| `2026/06/26/rollout-2026-06-26T10-14-06-019f01b4-ade8-7672-9456-a2002882769e.jsonl` | Hologres 测试重构 |

## 5. 本轮新增的训练判断

这次挖完第一批语料后，可以看到 P哥 review 的几个稳定动作，比主文档之前写得更具体。

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

训练触发器：

> 看到两个地方都能表达同一种能力，就必须问：哪个是权威体系？另一个是适配、缓存、demo，还是该删除？

## 6. 下一轮挖掘协议

每次只处理 1 到 2 个会话，按下面步骤做：

1. 从第 4 节选一个候选会话。
2. 只抽用户消息里 P哥/陈鹏/老板 COMMENT 的段落。
3. 过滤 token、密码、完整请求。
4. 对每条 comment 补齐上下文、P哥真正抓的问题、我们的 miss。
5. 如果一个新母题出现 3 次以上，再更新《架构师认知体系》主文档。

推荐下一批优先深挖：

- `019e39ec-801f-7b11-8309-b51d8a6138c2`：MR 113，先区分 Codex 自评和 P哥 comment，不能混记。
- `019e486c-0daa-7711-bd49-8f63a847662d`：MR 149，重点确认 `plural_api_name` 是否来自 P哥原话，以及它背后的 API 命名事实模型。
- `019e2975-d06c-7df0-9dde-b31f3952dbb3`：分支 Detail 表与迁移，可能补强 branch/global branch 母题。
- `019ef24d-c936-7c81-9dec-384d534b8923`：Resource.trashStatus，适合训练“一个字段背后到底承载什么业务状态”。
