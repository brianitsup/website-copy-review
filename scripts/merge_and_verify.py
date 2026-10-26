#!/usr/bin/env python3
"""Merge extraction agents' JSON, assign Ref codes, and verify every string against its source.

Usage:
  merge_and_verify.py --extract-dir DIR --pages pages.json --repo REPO_ROOT --out OUT_DIR
                      [--snapshot-dir DIR] [--accept accepted.json]

Inputs
  DIR/*.json     each a JSON array of extraction objects (see references/extraction-brief.md)
  pages.json     page order + metadata (see assets/pages.example.json)
  accepted.json  optional {"REF": "reason"} for residue confirmed by hand

Outputs (in OUT_DIR)
  items.json                 merged items with "ref", "page", "match" fields
  copy-review-manifest.csv   ref,page_key,page,section,element,file,line,chars,constrained,text
  verification.md            human-readable verification report

Exit code 0 only when every item is matched (or accepted) and all structural checks pass.
"""
import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path

REQUIRED = ["file", "line", "page_key", "section", "element", "text"]
BR_RE = re.compile(r"<br\s*/?>", re.I)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def collapse(s: str) -> str:
    return WS_RE.sub(" ", s).strip()


def norm_raw(s: str) -> str:
    return collapse(html.unescape(s))


def norm_tags(s: str) -> str:
    s = BR_RE.sub(" / ", s)
    s = TAG_RE.sub(" ", s)
    s = html.unescape(s)
    s = collapse(s)
    # tag removal can leave a space before punctuation: "<strong>Hi</strong>, there"
    return re.sub(r" ([,.;:!?)])", r"\1", s)


def norm_squash(s: str) -> str:
    s = BR_RE.sub("/", s)
    s = TAG_RE.sub("", s)
    return WS_RE.sub("", html.unescape(s))


def text_squash(t: str) -> str:
    return WS_RE.sub("", t)


def find_line(source: str, needle: str):
    """Best-effort 1-based line of the first raw occurrence (needle already collapsed)."""
    first = needle.split(" ")[0] if needle else ""
    if not first:
        return None
    src_lines = source.splitlines()
    for i, line in enumerate(src_lines, 1):
        if first in html.unescape(line):
            window = collapse(html.unescape(" ".join(src_lines[i - 1 : i + 15])))
            if needle in window:
                return i
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract-dir", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--snapshot-dir")
    ap.add_argument("--accept")
    args = ap.parse_args()

    repo = Path(args.repo)
    snap = Path(args.snapshot_dir) if args.snapshot_dir else None
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(Path(args.pages).read_text())
    pages = cfg["pages"]
    page_order = [p["key"] for p in pages]
    page_by_key = {p["key"]: p for p in pages}
    accepted = json.loads(Path(args.accept).read_text()) if args.accept else {}

    problems = []  # structural failures
    raw_items = []
    for f in sorted(Path(args.extract_dir).glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            problems.append(f"{f.name}: invalid JSON ({e})")
            continue
        if not isinstance(data, list):
            problems.append(f"{f.name}: top level is not a JSON array")
            continue
        for i, it in enumerate(data):
            missing = [k for k in REQUIRED if k not in it]
            if missing:
                problems.append(f"{f.name}[{i}]: missing fields {missing}")
                continue
            it["_src"] = f"{f.name}[{i}]"
            raw_items.append(it)

    # structural checks
    for it in raw_items:
        it["text"] = collapse(str(it["text"]))
        if not it["text"]:
            problems.append(f"{it['_src']}: empty text")
        if it["page_key"] not in page_by_key:
            problems.append(f"{it['_src']}: page_key {it['page_key']!r} not in pages.json")
    unused = [k for k in page_order if not any(i["page_key"] == k for i in raw_items)]

    # merge in page order, stable within page
    items = []
    for key in page_order:
        group = [i for i in raw_items if i["page_key"] == key]
        width = max(2, len(str(len(group))))
        for n, it in enumerate(group, 1):
            it["ref"] = f"{key}-{n:0{width}d}"
            it["page"] = page_by_key[key]["title"]
            it["chars"] = len(it["text"])
            it["has_dynamic"] = bool(it.get("has_dynamic")) or bool(
                re.search(r"\{\{.*?\}\}|\$\{.*?\}|\{t\(|<\?php", it["text"])
            )
            it["constrained"] = bool(it.get("constrained"))
            items.append(it)

    refs = [i["ref"] for i in items]
    dupes = sorted({r for r in refs if refs.count(r) > 1})
    if dupes:
        problems.append(f"duplicate refs: {dupes}")

    # verification against source
    cache = {}
    counts = {"raw": 0, "tag-stripped": 0, "squashed": 0, "accepted": 0, "UNMATCHED": 0, "FILE MISSING": 0}
    line_warnings = []
    for it in items:
        path = repo / it["file"]
        if not path.is_file() and snap is not None and (snap / it["file"]).is_file():
            path = snap / it["file"]
        if not path.is_file():
            it["match"] = "FILE MISSING"
        else:
            if path not in cache:
                src = path.read_text(errors="replace")
                cache[path] = (src, norm_raw(src), norm_tags(src), norm_squash(src))
            src, r, t, s = cache[path]
            txt = it["text"]
            if txt in r:
                it["match"] = "raw"
                ln = find_line(src, txt)
                if ln and abs(ln - int(it["line"] or 0)) > 10:
                    line_warnings.append(f"{it['ref']}: reported line {it['line']}, found near {ln}")
            elif norm_tags(txt) in t:
                it["match"] = "tag-stripped"
            elif text_squash(txt) in s:
                it["match"] = "squashed"
            else:
                it["match"] = "UNMATCHED"
        if it["match"] in ("UNMATCHED", "FILE MISSING") and it["ref"] in accepted:
            it["match"] = "accepted"
            it["accept_reason"] = accepted[it["ref"]]
        counts[it["match"]] += 1

    # outputs
    clean = [{k: v for k, v in i.items() if not k.startswith("_")} for i in items]
    (out / "items.json").write_text(json.dumps(clean, indent=2, ensure_ascii=False))
    with open(out / "copy-review-manifest.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        cols = ["ref", "page_key", "page", "section", "element", "file", "line", "chars", "constrained", "text"]
        w.writerow(cols)
        for i in clean:
            w.writerow([i[c] for c in cols])

    bad = [i for i in items if i["match"] in ("UNMATCHED", "FILE MISSING")]
    lines = ["# Copy extraction verification", ""]
    lines.append(f"Items: **{len(items)}** across **{len(page_order) - len(unused)}** pages")
    lines.append("")
    lines.append("| Match level | Items |")
    lines.append("|---|---|")
    for k, v in counts.items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("## Per page")
    lines.append("")
    lines.append("| Key | Page | Items |")
    lines.append("|---|---|---|")
    for key in page_order:
        lines.append(f"| {key} | {page_by_key[key]['title']} | {sum(1 for i in items if i['page_key'] == key)} |")
    if unused:
        lines += ["", f"Pages in pages.json with no items: {', '.join(unused)}"]
    if problems:
        lines += ["", "## Structural problems", ""] + [f"- {p}" for p in problems]
    if bad:
        lines += ["", "## Unresolved — open the source and inspect", ""]
        lines += [f"- `{i['ref']}` {i['match']} — {i['file']}:{i['line']} — \"{i['text'][:120]}\"" for i in bad]
    acc = [i for i in items if i["match"] == "accepted"]
    if acc:
        lines += ["", "## Accepted after manual inspection", ""]
        lines += [f"- `{i['ref']}` — {i['accept_reason']}" for i in acc]
    if line_warnings:
        lines += ["", "## Line number drift (informational)", ""] + [f"- {w}" for w in line_warnings]
    (out / "verification.md").write_text("\n".join(lines) + "\n")

    print("\n".join(lines))
    ok = not problems and not bad
    print("\nRESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
