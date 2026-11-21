"""TEMPORARY (PR #495): run reqstool-regression fixtures with this branch and with main, compare outputs."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*m")
FIXTURES = ["parent", "ecosystems/java", "ecosystems/python", "ecosystems/typescript"]
COMMANDS = [["status"], ["report", "--format", "asciidoc"], ["report", "--format", "markdown"], ["export"]]


def norm(o):
    if isinstance(o, dict):
        return {k: norm(v) for k, v in sorted(o.items())}
    if isinstance(o, list):
        return sorted((norm(x) for x in o), key=lambda x: json.dumps(x, sort_keys=True))
    return o


def run(src_root: Path, label: str, out_dir: Path, regression: Path) -> dict:
    env = dict(os.environ, PYTHONPATH=str(src_root / "src"), PYTHONIOENCODING="utf-8", NO_COLOR="1")
    results = {}
    for fixture in FIXTURES:
        for cmd in COMMANDS:
            key = f"{fixture.replace('/', '_')}-{'_'.join(cmd).replace('--format_', '')}"
            p = subprocess.run(
                [sys.executable, "-m", "reqstool.command", *cmd, "local", "-p", str(regression / "fixtures" / fixture)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
            )
            text = ANSI.sub("", p.stdout)
            (out_dir / label).mkdir(parents=True, exist_ok=True)
            (out_dir / label / f"{key}.txt").write_text(f"{text}\n--- stderr ---\n{ANSI.sub('', p.stderr)}\nexit={p.returncode}\n", encoding="utf-8")
            if cmd == ["export"] and p.returncode == 0:
                text = json.dumps(norm(json.loads(text)), sort_keys=True)
            results[key] = (p.returncode, text)
    return results


def main():
    branch_root, main_root, regression, out_dir = (Path(a).resolve() for a in sys.argv[1:5])
    branch = run(branch_root, "branch", out_dir, regression)
    base = run(main_root, "main", out_dir, regression)
    failed = False
    for key in branch:
        b_rc, b_out = branch[key]
        m_rc, m_out = base[key]
        same = (b_rc, b_out) == (m_rc, m_out)
        print(f"{key:45} branch exit={b_rc:<3} main exit={m_rc:<3} {'IDENTICAL' if same else 'DIFFERENT'}")
        if not b_out.strip():
            failed = True
        if not same and sys.platform != "win32":
            failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
