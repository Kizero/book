可以，这个清单我建议以后作为“动代码前强制 preflight”。它不是针对某个 case，而是一套通用工程门禁：任何复杂实现，尤其是设计文档已经评审过的任务，都先过这一遍。过不了，就先别写代码。

**开工前总原则**

一句话：先把“最终设计”翻译成“代码约束”，再动手。

以后你可以直接这样要求我：

```text
先不要写代码。请按《实现前工程清单》做 preflight：
1. 明确事实源、边界、禁止项、legacy/canonical 映射、adapter 抽象、测试门禁。
2. 每项标注 ✓ 已确认 / ? 不确定 / ✗ 缺失。
3. 凡是 ? 或 ✗，说明是否阻塞实现；如果不阻塞，说明为什么。
4. 输出后等我确认，再开始改代码。
```

**一、信息完整性门禁**

每次开工前先列：

| 检查项 | 必须回答 |
|---|---|
| 目标能力 | 这次到底交付什么用户/系统能力？ |
| 非目标 | 明确不做什么，哪些“顺手改”禁止做？ |
| 设计依据 | 最终设计文档是哪几份？关键章节是什么？ |
| 代码事实 | 当前 main 的真实代码结构是什么？不能凭记忆。 |
| 外部事实 | 是否依赖 PG/Hologres/LiKey/IDaaS/Flow/前端等外部契约？ |
| 验收方式 | 这次靠哪些测试/快照/CI 证明？ |
| 未确认项 | 哪些信息缺失？缺失是否阻塞？ |

硬规则：  
如果“目标能力”和“非目标”说不清，不能写代码。  
如果设计依据没引用到具体文档/章节，不能写代码。  
如果当前代码没读，只凭上下文记忆，不能写代码。

**二、事实源门禁**

任何实现都要先回答：

| 问题 | 判断标准 |
|---|---|
| 这个事实在系统里唯一归属哪里？ | 只能有一个权威字段、接口、表或 adapter。 |
| 有没有第二套表达？ | 有就必须说明是兼容输入、缓存、索引、还是错误冗余。 |
| 这个派生值能否从权威值计算出来？ | 能算出来就不应作为第二事实源保存。 |
| 这个字段是用户声明，还是 runtime 派生？ | 用户声明和系统派生不能混在一个字段里。 |
| 这个字段是 core 能力，还是上层流程？ | core 不保存上层业务流程状态。 |

以后我必须输出类似：

```text
事实源判断：
- Object property 数据类型权威：dataType: TypeDefinition
- 旧字符串 dataType：仅 metadata 输入兼容，不是运行时权威
- GraphQL scalar：由 normalized TypeDefinition 派生
- SQL column type：由 normalized TypeDefinition 派生
- 禁止新增 property.type，因为它会形成第二事实源
```

**三、命名与概念门禁**

所有新增名字都要过这个检查：

| 检查项 | 必须回答 |
|---|---|
| 名字是否和已有概念冲突？ | 如 type / dataType / valueType / valueDomain。 |
| 名字是否过宽？ | `type`、`status`、`scope`、`mode` 这类词要特别小心。 |
| 名字是否暴露了实现细节？ | PG、branch、parser、job 等是否应该留在 adapter 或编排层。 |
| 名字是否绑定了单一场景？ | merge、branch、online 等是否其实是通用能力的一种用法。 |
| 名字是否暗示了未实现能力？ | 例如 sensitive、mask、encrypted 字段如果没有 runtime 消费方，要谨慎。 |

硬规则：  
如果一个名字未来会让人问“范围到底多大”，先不要用。  
如果只是为了当前实现方便起名，不能进核心 interface。

**四、Legacy → Canonical 门禁**

凡是涉及旧字段、旧枚举、旧 schema，都必须画单向链路：

```text
legacy input -> canonical model -> persistence -> runtime consumption -> compatibility output
```

必须回答：

| 检查项 | 必须回答 |
|---|---|
| legacy 是什么？ | 旧字段/旧枚举/旧 API 形态。 |
| canonical 是什么？ | 新模型唯一权威。 |
| 兼容方向是什么？ | 只能单向，不能来回互转。 |
| 未知 legacy 值怎么办？ | 默认 fail-closed，不能静默降级。 |
| 新能力能否反向投影到旧字段？ | 能则 dual-write；不能则 publish 阻塞或要求消费者迁移。 |
| 什么时候删除兼容？ | 必须有独立 checklist，不能顺手删。 |

坏味道：  
`DATETIME -> TIMESTAMP` 同时又 `TIMESTAMP -> DATETIME`。  
`LONG/DECIMAL` 伪装成 `NUMBER`。  
未知类型默认成 `OBJECT/JSON/STRING`。

**五、层次边界门禁**

每个设计决策必须归层：

| 层 | 可以做什么 | 不该做什么 |
|---|---|---|
| metadata | 定义能力、字段、约束、声明 | 定义发布流程、轮询流程、业务分支策略 |
| normalizer | 兼容升级、默认值、展开 shortcut、记录 explain | 偷偷改变语义、不产出可观测 decision |
| validator | fail-fast / fail-closed | 自动修复业务错误 |
| DDL adapter | 生成 storage-specific DDL | 把 PG 事实写成 core 通用事实 |
| query compiler | 编译查询表达式 | 决定业务流程是否允许 |
| core service | 提供 primitive/capability | 维护上层 workflow 状态 |
| manager/上层 | 编排流程、重试、发布、等待 | 要求 core 为流程造状态字段 |

硬规则：  
core 尽量定义“能力是否存在”，不要定义“流程应该怎么跑”。  
PG/Hologres 差异必须在 adapter，不要污染 core interface。

**六、Adapter 与存储门禁**

任何 SQL、错误码、索引、FTS、driver 行为，都要先问：

| 检查项 | 必须回答 |
|---|---|
| 这是 core 通用能力，还是 PG 特性？ | PG 特性进 PG adapter。 |
| Hologres 是否会不同？ | 会不同就必须抽象 capability。 |
| 是否依赖 driver 默认行为？ | 要引用库契约或用测试证明。 |
| 是否新增了 cast/operator/function？ | 必须说明为什么 schema 本身不够。 |
| 错误码是否 storage-specific？ | `23505` 只能在 PG adapter 内映射成 `UNIQUE_VIOLATION`。 |
| 探测是运行时动态，还是配置能力？ | 能配置就优先配置，避免运行时漂移决定功能暴露。 |

坏味道：  
在 core 里写 `23505`。  
在 core 里写 `zhparser`。  
为了 GraphQL 输出，在 SQL 里加 `::text`。  
为了当前 PG 方便，把 Hologres 未来堵死。

**七、API 兼容门禁**

任何 GraphQL/API/schema 变化都要检查：

| 检查项 | 必须回答 |
|---|---|
| 已发布字段形态是否变化？ | `Int/Float/JSON number -> String` 是 breaking。 |
| 新字段和旧字段是否共存？ | 存量不能悄悄变。 |
| 客户端是否需要同步升级？ | 前端/Flow/AIP Logic 是否受影响。 |
| 是否需要 schema diff 快照？ | 涉及 GraphQL 必须考虑。 |
| 是否有版本化/迁移路径？ | 没有就不能原地改已发布形态。 |

硬规则：  
“正确”不等于“不 breaking”。  
修精度问题也不能偷改已发布 API。

**八、Normalizer 可观测性门禁**

如果 normalizer 自动做任何事，必须能解释：

| 自动行为 | 必须产出 decision |
|---|---|
| legacy 字段升级 | 从什么值升级成什么结构，依据是什么 |
| 默认值填充 | 为什么填，默认值来源是什么 |
| shortcut 展开 | 用户写了什么，展开成什么 |
| 冲突拒绝 | 哪个输入冲突，稳定错误码是什么 |
| 兼容投影 | 哪些能投影，哪些不能投影 |
| blocked publish | 阻塞原因、责任方、解除条件 |

硬规则：  
不能让用户只看到“配置了但没生效”。  
所有自动展开都要进入 preview / snapshot / diagnostics。

**九、字段新增门禁**

新增字段前必须回答 7 个问题：

1. 这个字段是不是唯一事实源？
2. 能不能从已有字段推导？
3. 是用户输入，还是 runtime 派生？
4. 当前 MR 有没有消费方？
5. 没有这个字段，功能是否无法实现？
6. 未来删除它是否困难？
7. 这个字段名会不会和未来概念冲突？

只要第 2 题答案是“能推导”，默认不新增。  
只要第 4 题答案是“没有消费方”，默认不新增。  
只要第 7 题答案是“可能冲突”，先换名或不加。

**十、测试设计门禁**

每次实现前先列测试矩阵：

| 测试层 | 必须覆盖 |
|---|---|
| unit | normalizer、validator、mapper、compiler 的纯逻辑 |
| snapshot/golden | schema、DDL preview、normalizer decisions |
| integration | DB DDL、driver 输入输出、adapter 错误映射 |
| regression | 存量旧 metadata 行为 |
| negative | 未知值、缺必填、非法组合、不可逆兼容 |
| no-op | 不在范围内的能力不能被意外打开 |

每个 MR 至少回答：

```text
这次哪些风险用单元测试证明？
哪些必须靠集成测试证明？
哪些本地跑不了，交给 CI？
哪些风险目前没有测试，为什么可以接受？
```

**十一、实现顺序门禁**

复杂任务不能上来就改业务代码。顺序固定：

1. 读最终设计文档和相关代码。
2. 输出 preflight 清单。
3. 你确认。
4. 先改类型/interface。
5. 再改 normalizer/validator。
6. 再改消费方。
7. 再改测试。
8. 再跑局部测试。
9. 再跑全量验证。
10. 最后更新 MR 描述。

如果中途发现设计与代码事实冲突，停止并重新输出差异，不继续硬写。

**十二、P哥式自检**

以后实现前我必须问自己：

| 自检问题 | 如果答案是“是” |
|---|---|
| 我是不是把使用方流程写进 core 了？ | 停，改成 primitive/capability。 |
| 我是不是新增了第二事实源？ | 停，改成派生或兼容 adapter。 |
| 我是不是为了一个场景起了通用字段？ | 停，重新命名或下沉。 |
| 我是不是把 PG 特性写进通用接口？ | 停，放到 adapter。 |
| 我是不是新增了没有消费方的字段？ | 停，删掉或 gated。 |
| 我是不是凭记忆实现旧版方案？ | 停，重新读最终文档。 |
| 我是不是用测试守护本该结构保证的事情？ | 优先结构收敛，再补测试。 |
| 我是不是把 API breaking change 说成 bug fix？ | 停，走兼容评审。 |

**十三、开工前输出模板**

你以后可以让我每次先填这个：

```text
【实现前工程清单】

【目标】
本 MR 交付：
不交付：

【设计依据】
- 文档：
- 关键章节：
- 必须遵守的设计句子：

【代码事实】
- 当前权威字段/接口：
- 当前消费方：
- 当前兼容字段：
- 当前测试入口：

【事实源判断】
- 唯一事实源：
- 派生输出：
- 兼容输入：
- 禁止新增的第二事实源：

【Legacy / Canonical 映射】
legacy:
canonical:
persistence:
runtime:
API:
unknown legacy 行为：

【层次边界】
metadata:
normalizer:
validator:
adapter:
query/compiler:
上层 manager:

【禁止项】
- 不做：
- 不新增：
- 不修改：
- 不假设：

【Adapter 判断】
PG-specific:
Hologres 可能差异:
core 抽象:
需要配置还是探测:

【API 兼容】
是否影响已发布 schema：
是否需要 schema diff：
是否 breaking：
迁移策略：

【测试计划】
单元测试：
快照/golden：
集成测试：
负向测试：
本地不能跑的验证：

【阻塞项】
✓ 已确认：
? 不确定：
✗ 缺失：
是否允许开工：
```

**十四、真正的执行标准**

以后不是“我觉得差不多可以写了”才开工，而是：

- 没有唯一事实源，不开工。
- legacy/canonical 方向不清，不开工。
- 不知道哪些字段禁止新增，不开工。
- 不知道 PG/Hologres 边界，不开工。
- 没有测试矩阵，不开工。
- 不能解释为什么需要新增字段，不新增。
- 不能解释为什么需要 SQL cast，不加 cast。
- 没有消费方的 future field，不加。
- 文档与代码事实冲突，先汇报，不硬写。

这个清单以后我也会内化成默认动作。你每次只要提醒一句“先跑实现前工程清单”，我就应该先停下来，把这些内容填完，再进入代码。
