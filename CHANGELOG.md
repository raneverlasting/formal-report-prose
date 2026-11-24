# 更新日志

## v1.0.0 — 2025-11-25

首个发布版本。

### 内容

- `SKILL.md`：触发描述、语气契约、6 条硬规则、三遍改稿流程、正反示例。
- `references/rewrite-rules.md`：30 类 AI 痕迹与防御性写作模式，每条给信号、问题、改法和示例。
- `scripts/lint_prose.py`：确定性扫描器。词句规则覆盖修辞对比、否定式边界、空洞提示与总结、聊天痕迹、身份声明、空洞收尾、夸张评价、格式、模糊限定；文档级检查覆盖问句开场与收尾、三段式骨架、破折号与省略号密度。支持 `--json`、`--strict`、`--skip-quotes`、`--no-warnings`，退出码 0、1、2。
- `tests/cases.md`：8 个验收案例，覆盖季度报告、项目复盘、裁员决策、错误前提纠错、信息不足、敏感话题、改稿、正式邮件。
- `tests/test_lint_prose.py`：14 个单元测试，覆盖规则命中、代码块与行内代码跳过、引用跳过、行列号、CLI 退出码。
- `install.ps1`：安装到 `$HOME\.dsh\skills\formal-report-prose`，安装前备份；`-GlobalRules` 写入 `$HOME\.dsh\AGENTS.md` 托管区块；`-DryRun` 只打印计划。
- `README.md`：安装、使用、改写对照、扫描器、测试、设计说明。

### 验证

- `python -m unittest discover -s tests -p "test_*.py"`：14 项通过。
- `python scripts/lint_prose.py tests/cases.md --skip-quotes`：0 error，0 warning。
- `python scripts/lint_prose.py README.md --skip-quotes`：0 error，0 warning。

### 已知边界

- 扫描器只认句式和格式。论证是否成立、数字是否可靠、语气是否得体仍由作者判断。
- 规则针对中文正式文体。其他语言和文体需要重写案例与格式规范。
