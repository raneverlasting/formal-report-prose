# formal-report-prose

一套中文正式汇报写作 skill。目标是把 AI 腔、客服话术、防御性写作清理掉，让文本像做过这件事的人在汇报：结论先行，依据具体，边界清楚，答完即止。

## 包含内容

```
formal-report-prose/
├── SKILL.md                     # 触发、语气契约、硬规则、三遍改稿
├── global-rules.md              # 可写入全局 AGENTS.md 的常驻规则
├── references/
│   └── rewrite-rules.md         # 30 类 AI 痕迹与防御性写作模式
├── scripts/
│   └── lint_prose.py            # 确定性扫描器
├── tests/
│   ├── cases.md                 # 8 个验收案例
│   └── test_lint_prose.py       # 扫描器单元测试
├── install.ps1                  # 安装与全局规则写入
├── CHANGELOG.md                 # 版本记录
└── README.md
```

## 安装

### 先试运行

```powershell
cd .agents\skills\formal-report-prose
.\install.ps1 -DryRun
```

### 安装到用户 skill 目录

```powershell
.\install.ps1
```

默认目标：`$HOME\.dsh\skills\formal-report-prose`。目标已存在时，脚本先复制一份带时间戳的备份，再替换。

如果系统禁止运行脚本，使用：

```powershell
pwsh -ExecutionPolicy Bypass -File .\install.ps1
```

### 写入全局规则

```powershell
.\install.ps1 -GlobalRules
```

默认写入 `$HOME\.dsh\AGENTS.md`，用 `<!-- formal-report-prose:start -->` 和 `<!-- formal-report-prose:end -->` 包住。重复执行会替换这一段，不会重复追加。原文件会先备份。

如果只想安装 skill、不改全局规则，省略 `-GlobalRules`。

## 使用

skill 由描述自动触发，适用于中文报告、经营分析、项目复盘、方案说明、汇报材料、正式邮件，以及“去 AI 味”“正式汇报口吻”“报告体”这类请求。

也可以显式调用：

```
用 formal-report-prose 改写下面这段。
```

改稿任务只输出正文。需要看改动说明时，单独说明。

## 改写对照

输入取自 `tests/cases.md` 案例 7，典型的 AI 客服口径。先用扫描器定位问题，再按规则改写。

**输入**

> 随着 AI 技术的快速发展，越来越多的企业开始关注 AI 客服。值得注意的是，这不仅是技术问题，更是管理问题。我们不能把 AI 客服简单地看作降本工具，也不能指望它一次性解决所有问题。当然，这并不意味着人工客服没有价值。真正的关键在于，不是用 AI 替代人，而是让人做更有价值的事。综上所述，企业需要理性看待 AI 客服，未来可期。

```
$ python scripts/lint_prose.py draft.md
draft.md:1:33 error filler.signpost: 空洞提示语，删掉后信息不变。
  match: 值得注意的是
  fix:   直接写事实。
draft.md:1:58 error boundary.kanzuo: 用否定句做边界限定。
  match: 不能把 AI 客服简单地看作
  fix:   改成正面适用范围：适用于 X；Y 另行处理。
draft.md:1:97 error boundary.weiyi: 用否定句做边界限定。
  match: 并不意味着
  fix:   直接说明这项事实能支持什么结论。
draft.md:1:119 error contrast.buzhi: 禁用修辞对比：不是 A，而是 B。
  match: 不是用 AI 替代人，而是
  fix:   拆成两句正面陈述，或直接陈述 B，把 A 降为背景。
draft.md:1:142 warning filler.conclusion: 机械总结。
  match: 综上所述
  fix:   删掉总结句，或把它换成具体的下一步动作。
draft.md:1:149 error closer.generic: 空洞收尾或机械平衡。
  match: 需要理性看待
  fix:   停在最后一个事实、决定或动作上。
draft.md:1:162 error closer.generic: 空洞收尾或机械平衡。
  match: 未来可期
  fix:   停在最后一个事实、决定或动作上。

6 error(s), 1 warning(s)
```

**改写**

> AI 客服能不能省人力成本，取决于知识库覆盖多少常见问题、转人工规则在哪些条件下生效、上线后有没有质检修正答错的对话。这三项没配好，客户会在同一类问题上重复进线。
>
> 人力配置随之调整：重复度高、流程固定的咨询交给 AI，投诉、退款和复杂故障留给人工。切换按咨询类型分批做，每批上线后看一次解决率和满意度，再决定是否扩大范围。

复扫 `0 error(s), 0 warning(s)`，退出码 0。案例 7 要求把“技术问题、管理问题”这类判断落到知识库维护、转人工规则和质检上；改写只做这一步，没有补充解决率、成本节省一类原文没有的数字。

## 扫描器

```powershell
python scripts/lint_prose.py draft.md
python scripts/lint_prose.py draft.md --json
python scripts/lint_prose.py draft.md --strict
python scripts/lint_prose.py draft.md --skip-quotes
```

- 默认输出 `文件:行:列 级别 规则: 说明`，并给匹配文本和改法。
- `--json` 输出机器可读结果。
- `--strict` 让 warning 也返回退出码 1。
- `--skip-quotes` 跳过 `>` 引用块，适合审阅带原文引用的改稿。
- 代码块和行内代码默认跳过。

退出码：`0` 无 error；`1` 有 error，或 `--strict` 下有 warning；`2` 文件读取或解码失败。

扫描器只报症状，不改稿。规则命中后结合语境判断；引用原文和示例不参与扫描时加 `--skip-quotes`。

## 测试

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

八个验收案例在 `tests/cases.md`，覆盖季度报告、项目复盘、裁员决策、错误前提纠错、信息不足、敏感话题、改稿、正式邮件。每个案例列出合格条件和硬性失败信号。

## 设计说明

**两条禁令转成动作。** `不是 A 而是 B`要求拆成两句正面陈述；`不能/不等于`要求写成“适用于 X；Y 另行处理”。只告诉模型“不要这样写”，它容易换个说法继续绕；给出替代句式，行为才稳定。

**保留 humanizer-zh 的模式清单，换掉声音建议。** humanizer-zh 的 24 类模式仍然有效，但它鼓励第一人称、幽默、情绪和“凌乱感”，这些会破坏正式汇报的克制。本 skill 把“人味”定义为具体、判断、责任和节奏，删掉 50 分自评，避免机械优化。

**扫描器只做确定性检查。** 句式、标点、表情、聊天痕迹可以机器识别；论证是否成立、数字是否可靠、语气是否得体，仍由作者判断。扫描器负责不漏掉已知模式，作者负责不把它当唯一标准。

**常驻规则和 skill 分工。** 七条常驻规则进入全局 `AGENTS.md`，负责日常对话的底线；完整 skill 负责正式成稿和改稿，包含案例、规则库和扫描器。两层都装，日常回答和长文写作才不会脱节。

## 调整规则

新增扫描规则：编辑 `scripts/lint_prose.py` 的 `RULES`，补一条单元测试，再跑测试。规则 id 用 `类别.名称`，severity 取 `error` 或 `warning`。

新增改写模式：编辑 `references/rewrite-rules.md`，保持“信号、问题、改法、例”的结构。示例中的数字标明“示意”，避免被当成真实数据。

调整常驻规则：编辑 `global-rules.md`，重新执行 `.\install.ps1 -GlobalRules`。脚本会替换托管区块，不碰文件其他内容。
