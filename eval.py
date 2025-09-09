#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch runner to test multiple LLM-generated Isabelle lemma variants.

- Reads a JSONL file where each line is a JSON object containing:
    {
      "input": "<original lemma header ...>",
      "gt": "...",
      "baseline_output": "```isabelle\nlemma ...\n...\n```",
      "cot_output": "```isabelle\nlemma ...\n...\n```",
      "fs_baseline_output": "```isabelle\nlemma ...\n...\n```",
      "fs_cot_output": "```isabelle\nlemma ...\n...\n```"
    }

- For each available output variant (baseline_output, cot_output, fs_baseline_output, fs_cot_output),
  it replaces the corresponding lemma block in the target .thy file, runs
    isabelle build -d <ROOT> -b <SESSION>
  collects success/failure, and restores the file to its original state after each attempt.

Usage:
  python3 try_lemma_variants.py \
      --jsonl ./results.jsonl \
      --thy ./CorresK_Lemmas.thy \
      --session CorresK \
      --root . \
      --out ./build_report.jsonl
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

VARIANT_KEYS = ["baseline_output", "cot_output"]

CODE_FENCE_RE = re.compile(r"```isabelle\s*(.*?)```", re.S)
LEMMA_NAME_RE = re.compile(r"\blemma\s+([A-Za-z0-9_']+)")
# Matches from "lemma <name>" up to next "lemma <something>" OR "end" at start of line.
LEMMA_BLOCK_RE_TMPL = r"(?s)(^|\n)(lemma\s+{name}\b.*?)(?=\nlemma\s|\nend\s*$)"

def extract_isabelle_code(s: str) -> str:
    if not s:
        return ""
    m = CODE_FENCE_RE.search(s)
    code = m.group(1) if m else s
    print(code)
    return code.strip()

def lemma_name_from_code(code: str) -> str | None:
    m = LEMMA_NAME_RE.search(code)
    return m.group(1) if m else None

def lemma_name_from_input(inp: str) -> str | None:
    if not inp:
        return None
    m = LEMMA_NAME_RE.search(inp)
    return m.group(1) if m else None

def replace_lemma_block(thy_text: str, lemma_name: str, new_block: str) -> tuple[str, bool]:
    """
    Replace the lemma block named `lemma_name` with `new_block`.
    Returns (new_text, replaced?)
    """
    pattern = re.compile(LEMMA_BLOCK_RE_TMPL.format(name=re.escape(lemma_name)))
    m = pattern.search(thy_text)
    if not m:
        return thy_text, False

    prefix = thy_text[:m.start(2)]
    suffix = thy_text[m.end(2):]
    # Ensure new block ends with a newline
    if not new_block.endswith("\n"):
        new_block = new_block + "\n"
    return prefix + new_block + suffix, True

def run_isabelle_build(root: Path, session: str, extra_args: list[str] | None = None, timeout: int = 1800):
    cmd = ["isabelle", "build", "-d", str(root), "-b", session]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr

def tail(s: str, n: int = 2000) -> str:
    if len(s) <= n:
        return s
    return s[-n:]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True, help="Input JSONL with lemma candidates")
    ap.add_argument("--thy", required=True, help="Target .thy file to patch")
    ap.add_argument("--session", required=True, help="Isabelle session name, e.g., CorresK")
    ap.add_argument("--root", default=".", help="Isabelle project root for -d")
    ap.add_argument("--out", default="./build_report.jsonl", help="Output JSONL report path")
    ap.add_argument("--timeout", type=int, default=1800, help="Build timeout in seconds")
    ap.add_argument("--stop_on_success", action="store_true", help="Stop iterating variants for an item once one succeeds")
    ap.add_argument("--dry_run", action="store_true", help="Do not run build; just show planned replacements")
    args = ap.parse_args()

    jsonl_path = Path(args.jsonl)
    thy_path = Path(args.thy)
    root_path = Path(args.root).resolve()
    out_path = Path(args.out)

    thy_orig = thy_path.read_text(encoding="utf-8")

    with jsonl_path.open("r", encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
        for line_no, line in enumerate(fin, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception as e:
                fout.write(json.dumps({
                    "line": line_no,
                    "error": f"invalid json: {e}"
                }, ensure_ascii=False) + "\n")
                continue

            inp = item.get("input", "")
            # Prefer lemma name from code; fallback to input.
            lemma_name_hint = lemma_name_from_input(inp)

            variants = []
            for k in VARIANT_KEYS:
                if k in item and item[k]:
                    code = extract_isabelle_code(item[k])
                    if code:
                        # Try to extract lemma name from the code block itself
                        name_in_code = lemma_name_from_code(code)
                        lemma_name = name_in_code or lemma_name_hint
                        variants.append((k, lemma_name, code))

            if not variants:
                fout.write(json.dumps({
                    "line": line_no,
                    "input_lemma_guess": lemma_name_hint,
                    "result": "no_variants"
                }, ensure_ascii=False) + "\n")
                continue

            for variant_key, lemma_name, code_block in variants:
                if not lemma_name:
                    fout.write(json.dumps({
                        "line": line_no,
                        "variant": variant_key,
                        "error": "lemma_name_not_found"
                    }, ensure_ascii=False) + "\n")
                    continue

                # Prepare replacement text
                new_thy_text, ok = replace_lemma_block(thy_orig, lemma_name, code_block)
                if not ok:
                    fout.write(json.dumps({
                        "line": line_no,
                        "variant": variant_key,
                        "lemma": lemma_name,
                        "error": f"lemma_block_not_found_in_file: {thy_path.name}"
                    }, ensure_ascii=False) + "\n")
                    continue

                # Write temp file to avoid clobbering original in case of crash
                try:
                    backup_path = None
                    # Save backup once per variant attempt
                    backup_path = thy_path.with_suffix(".thy.bak_tmp")
                    backup_path.write_text(thy_orig, encoding="utf-8")

                    # Write the replaced .thy
                    thy_path.write_text(new_thy_text, encoding="utf-8")

                    if args.dry_run:
                        result = {
                            "time": datetime.utcnow().isoformat() + "Z",
                            "line": line_no,
                            "variant": variant_key,
                            "lemma": lemma_name,
                            "status": "dry_run",
                        }
                        fout.write(json.dumps(result, ensure_ascii=False) + "\n")
                        # Restore original
                        thy_path.write_text(thy_orig, encoding="utf-8")
                        if args.stop_on_success:
                            break
                        continue

                    # Run build
                    rc, out, err = run_isabelle_build(root=root_path, session=args.session, timeout=args.timeout)

                    success = (rc == 0) and (f"Finished {args.session}" in out)

                    result = {
                        "time": datetime.utcnow().isoformat() + "Z",
                        "line": line_no,
                        "variant": variant_key,
                        "lemma": lemma_name,
                        "returncode": rc,
                        "stdout_tail": tail(out, 4000),
                        "stderr_tail": tail(err, 4000),
                        "success": success,
                        "thy": str(thy_path),
                        "session": args.session,
                    }
                    
                    fout.write(json.dumps(result, ensure_ascii=False) + "\n")
                    fout.flush()

                    # Restore original .thy
                    thy_path.write_text(thy_orig, encoding="utf-8")
                    if backup_path and backup_path.exists():
                        backup_path.unlink(missing_ok=True)

                    # Stop early if requested and success
                    if args.stop_on_success and rc == 0:
                        break

                except subprocess.TimeoutExpired as te:
                    # Restore and report timeout
                    thy_path.write_text(thy_orig, encoding="utf-8")
                    fout.write(json.dumps({
                        "time": datetime.utcnow().isoformat() + "Z",
                        "line": line_no,
                        "variant": variant_key,
                        "lemma": lemma_name,
                        "error": f"timeout: {te}",
                        "thy": str(thy_path),
                        "session": args.session,
                    }, ensure_ascii=False) + "\n")
                except Exception as e:
                    # Restore and report generic error
                    try:
                        thy_path.write_text(thy_orig, encoding="utf-8")
                    except Exception:
                        pass
                    fout.write(json.dumps({
                        "time": datetime.utcnow().isoformat() + "Z",
                        "line": line_no,
                        "variant": variant_key,
                        "lemma": lemma_name,
                        "error": f"{type(e).__name__}: {e}",
                        "thy": str(thy_path),
                        "session": args.session,
                    }, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
