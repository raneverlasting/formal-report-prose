#!/usr/bin/env python3
"""Deterministic prose linter for formal Chinese writing.

The linter reports lexical and formatting symptoms. It does not rewrite text.
Exit codes:
  0  no errors (warnings allowed unless --strict)
  1  errors found, or warnings found with --strict
  2  usage or decoding failure
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Rule:
    id: str
    pattern: str
    severity: str
    message: str
    hint: str


@dataclass(frozen=True)
class Finding:
    line: int
    column: int
    rule_id: str
    severity: str
    message: str
    hint: str
    match: str


RULES: tuple[Rule, ...] = (
    # Rhetorical contrast and negative parallelism.
    Rule(
        "contrast.buzhi",
        r"不是[^。！？\n]{0,60}?(?:而是|，是)",
        "error",
        "禁用修辞对比：不是 A，而是 B。",
        "拆成两句正面陈述，或直接陈述 B，把 A 降为背景。",
    ),
    Rule(
        "contrast.bingfei",
        r"并非[^。！？\n]{0,60}?而是",
        "error",
        "禁用修辞对比：并非 A，而是 B。",
        "拆成两句正面陈述。",
    ),
    Rule(
        "contrast.yuqishuo",
        r"与其说[^。！？\n]{0,40}?不如说",
        "error",
        "禁用修辞对比：与其说 A，不如说 B。",
        "直接陈述判断，删掉铺垫。",
    ),
    Rule(
        "contrast.buzaiyu",
        r"不在于[^。！？\n]{0,40}?而在于",
        "error",
        "禁用修辞对比：不在于 A，而在于 B。",
        "直接写出 B，A 若重要就单独成句。",
    ),
    Rule(
        "contrast.erfei",
        r"而非",
        "error",
        "出现对比收尾：A，而非 B。",
        "拆成两句，或只保留 B。",
    ),
    # Boundary claims built from negation.
    Rule(
        "boundary.kanzuo",
        r"不能(?:简单)?(?:地)?(?:被)?(?:把[^。！？\n]{0,20}?)?(?:看作|视为|等同于|归结为|理解为)",
        "error",
        "用否定句做边界限定。",
        "改成正面适用范围：适用于 X；Y 另行处理。",
    ),
    Rule(
        "boundary.budengyu",
        r"不等于",
        "error",
        "用否定句做边界限定。",
        "写出两个概念各自的定义或适用条件。",
    ),
    Rule(
        "boundary.weiyi",
        r"(?:并不意味着|并不代表|并不能说明)",
        "error",
        "用否定句做边界限定。",
        "直接说明这项事实能支持什么结论。",
    ),
    Rule(
        "boundary.buba",
        r"不把[^。！？\n]{0,20}?(?:当作|视为|看作)",
        "error",
        "用否定句做边界限定。",
        "改写为正面的使用范围。",
    ),
    # Empty signposts and summaries.
    Rule(
        "filler.signpost",
        r"(?:需要注意的是|值得注意的是|需要指出的是|值得一提的是|需要强调的是|必须指出的是)",
        "error",
        "空洞提示语，删掉后信息不变。",
        "直接写事实。",
    ),
    Rule(
        "filler.conclusion",
        r"(?:综上所述|总而言之|总的来说|归根结底|由此可见)",
        "warning",
        "机械总结。",
        "删掉总结句，或把它换成具体的下一步动作。",
    ),
    Rule(
        "filler.empty",
        r"(?:众所周知|毋庸置疑|不可否认|不难发现|不难看出)",
        "error",
        "用共识或显而易见替代论证。",
        "给出具体来源、数据或机制。",
    ),
    # Chat traces and sycophancy.
    Rule(
        "chat.sycophancy",
        r"(?:好问题|当然可以|没问题[，,]?我|希望对你有帮助|希望这能帮到你)",
        "error",
        "聊天式迎合，正式文本中删除。",
        "直接进入正文。",
    ),
    Rule(
        "chat.offer",
        r"(?:如需(?:要)?(?:进一步|更多)|请随时(?:告诉|联系)|随时告诉我|需要我(?:帮|为|继续)|要不要我)",
        "error",
        "主动提供后续服务，属于聊天痕迹。",
        "答完即止；用户需要时会再问。",
    ),
    Rule(
        "chat.meta",
        r"(?:作为一个?(?:AI|人工智能|语言模型)|作为语言模型|我的训练数据|截至我的知识|根据我的训练)",
        "error",
        "身份声明或知识截止声明。",
        "删掉身份，改为具体资料范围和时间。",
    ),
    # Generic closers and inflated claims.
    Rule(
        "closer.generic",
        r"(?:未来可期|前景(?:广阔|光明)|迈出了(?:坚实|重要)的一步|具有(?:重要|深远)意义|意义重大|仍有待(?:观察|时间)|需要理性看待|不能一概而论|让我们拭目以待|时间会证明)",
        "error",
        "空洞收尾或机械平衡。",
        "停在最后一个事实、决定或动作上。",
    ),
    Rule(
        "inflated.hype",
        r"(?:革命性|颠覆性|划时代|前所未有|完美|极致|里程碑)",
        "warning",
        "夸张评价，证据通常撑不住。",
        "换成具体变化、数字或影响范围。",
    ),
    Rule(
        "inflated.jargon",
        r"(?:赋能|闭环|抓手|生态位|全方位|深层次|持续迭代|降本增效|组合拳|护城河)",
        "warning",
        "大词或行业黑话，可能掩盖具体动作。",
        "换成谁做了什么、产生什么结果。",
    ),
    # Formatting tells.
    Rule(
        "format.bold_label",
        r"^\s*[-*+]\s+\*\*[^*]+\*\*\s*[：:]",
        "warning",
        "粗体标签式列表。",
        "合并成段落，或改为普通列表，每项先给事实。",
    ),
    Rule(
        "format.emoji",
        r"[\U0001F300-\U0001FAFF\u2600-\u27BF]",
        "error",
        "表情符号。",
        "删除。",
    ),
    Rule(
        "format.exclamation",
        r"！",
        "warning",
        "感叹号。",
        "改为句号；确需强调时用事实和数字。",
    ),
    # Hedging.
    Rule(
        "hedge.stack",
        r"(?:可能|或许|也许|大概|似乎|一定程度上|某种程度上|某种意义上)[^。！？\n]{0,25}?(?:可能|或许|也许|大概|似乎|一定程度上|某种程度上|某种意义上)",
        "warning",
        "模糊限定词叠用。",
        "写明缺哪项事实、影响哪个结论、用什么补。",
    ),
    Rule(
        "hedge.vague",
        r"(?:一定程度上|某种程度上|某种意义上)",
        "warning",
        "模糊限定。",
        "给出具体幅度、条件或范围。",
    ),
    # Rhetorical questions and cliché openings.
    Rule(
        "rhetoric.question",
        r"(?:难道|何尝|岂不|你有没有|你是否想过)",
        "error",
        "反问句或假对话开场。",
        "直接给问题、数据、结论。",
    ),
    Rule(
        "opening.cliche",
        r"^(?:随着[^。！？\n]{0,40}(?:的发展|的进步|的普及)|在当今[^。！？\n]{0,30}(?:时代|背景下)|近年来[，,])",
        "warning",
        "时代背景式开场。",
        "从具体事实、冲突或结论起笔。",
    ),
)


def _sanitize(text: str, skip_quotes: bool) -> str:
    """Blank out fenced code, inline code, and optionally blockquotes.

    Character offsets and newlines are preserved so regex matches still map
    back to the original line and column.
    """
    out: list[str] = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        newline = line[len(body):]
        stripped = body.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append(" " * len(body) + newline)
            continue
        if in_fence or (skip_quotes and stripped.startswith(">")):
            out.append(" " * len(body) + newline)
            continue
        masked = re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), body)
        out.append(masked + newline)
    return "".join(out)


def _line_column(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    previous = text.rfind("\n", 0, index)
    column = index - previous
    return line, column


def _line_start(text: str, line_index: int) -> int:
    offset = 0
    for index, line in enumerate(text.splitlines(keepends=True)):
        if index == line_index:
            return offset
        offset += len(line)
    return offset


def _add(
    findings: list[Finding],
    text: str,
    rule: Rule,
    start: int,
    match: str,
) -> None:
    line, column = _line_column(text, start)
    findings.append(
        Finding(
            line=line,
            column=column,
            rule_id=rule.id,
            severity=rule.severity,
            message=rule.message,
            hint=rule.hint,
            match=match,
        )
    )


def lint_text(text: str, skip_quotes: bool = False) -> list[Finding]:
    """Return findings for the supplied text, ordered by position."""
    sanitized = _sanitize(text, skip_quotes=skip_quotes)
    findings: list[Finding] = []

    for rule in RULES:
        flags = re.MULTILINE
        for match in re.finditer(rule.pattern, sanitized, flags):
            if not match.group(0).strip():
                continue
            _add(findings, sanitized, rule, match.start(), match.group(0))

    # Document-level checks.
    content_lines = [
        (index, line)
        for index, line in enumerate(sanitized.splitlines())
        if line.strip()
    ]
    if content_lines:
        first_index, first_line = content_lines[0]
        last_index, last_line = content_lines[-1]
        if first_line.rstrip().endswith(("？", "?")):
            _add(
                findings,
                sanitized,
                Rule(
                    "opening.question",
                    "",
                    "warning",
                    "以问句开场。",
                    "直接给答案或结论。",
                ),
                _line_start(sanitized, first_index),
                first_line.strip(),
            )
        if last_line.rstrip().endswith(("？", "?")):
            _add(
                findings,
                sanitized,
                Rule(
                    "closing.question",
                    "",
                    "warning",
                    "以问句收尾，像聊天。",
                    "停在事实、决定或动作上。",
                ),
                _line_start(sanitized, last_index),
                last_line.strip(),
            )

    triad = re.search(
        r"首先[，,][\s\S]{0,120}?其次[，,][\s\S]{0,120}?最后[，,]",
        sanitized,
    )
    if triad:
        _add(
            findings,
            sanitized,
            Rule(
                "structure.triad",
                "",
                "warning",
                "首先/其次/最后式骨架。",
                "按结论、依据、动作组织；过渡用内容关系。",
            ),
            triad.start(),
            triad.group(0)[:40],
        )

    dash_positions = [m.start() for m in re.finditer(r"——|—", sanitized)]
    if len(dash_positions) > 2:
        _add(
            findings,
            sanitized,
            Rule(
                "format.dash",
                "",
                "warning",
                "破折号密度偏高。",
                "改用逗号、句号或冒号。",
            ),
            dash_positions[0],
            "——",
        )

    ellipsis_positions = [m.start() for m in re.finditer(r"……", sanitized)]
    if len(ellipsis_positions) > 2:
        _add(
            findings,
            sanitized,
            Rule(
                "format.ellipsis",
                "",
                "warning",
                "省略号密度偏高。",
                "删掉停顿，直接写下一句。",
            ),
            ellipsis_positions[0],
            "……",
        )

    deduped: list[Finding] = []
    seen: set[tuple[int, int, str]] = set()
    for finding in sorted(findings, key=lambda f: (f.line, f.column, f.rule_id)):
        key = (finding.line, finding.column, finding.rule_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped


def _format_text(path: str, findings: Iterable[Finding]) -> str:
    lines: list[str] = []
    for finding in findings:
        lines.append(
            f"{path}:{finding.line}:{finding.column} "
            f"{finding.severity} {finding.rule_id}: {finding.message}"
        )
        lines.append(f"  match: {finding.match.strip()[:120]}")
        lines.append(f"  fix:   {finding.hint}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan Chinese prose for AI-writing and defensive-writing tells."
    )
    parser.add_argument("path", nargs="?", default="-", help="UTF-8 file, or - for stdin")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    parser.add_argument("--skip-quotes", action="store_true", help="ignore blockquotes")
    parser.add_argument("--no-warnings", action="store_true", help="hide warnings")
    args = parser.parse_args(argv)

    try:
        if args.path == "-":
            raw = sys.stdin.buffer.read()
        else:
            raw = Path(args.path).read_bytes()
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"lint_prose: {exc}", file=sys.stderr)
        return 2

    findings = lint_text(text, skip_quotes=args.skip_quotes)
    if args.no_warnings:
        findings = [f for f in findings if f.severity == "error"]

    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")

    if args.json:
        payload = {
            "path": args.path,
            "errors": errors,
            "warnings": warnings,
            "findings": [asdict(f) for f in findings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if findings:
            print(_format_text(args.path, findings))
            print()
        print(f"{errors} error(s), {warnings} warning(s)")

    if errors:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
