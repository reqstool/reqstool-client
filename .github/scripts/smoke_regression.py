"""Run the installed reqstool CLI over the reqstool-regression fixtures and record normalised output.

Usage: smoke_regression.py <reqstool-regression checkout> <output dir>

One ``<fixture>-<command>.txt`` per run holds stdout, stderr and the exit code, with ANSI codes stripped and
line endings normalised so the files from different operating systems can be compared byte for byte. A
separate job diffs them against the Linux run. Exits non-zero only if the CLI produced no output at all.
"""

import json
import locale
import re
import subprocess
import sys
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*m")
FIXTURES = ["parent", "ecosystems/java", "ecosystems/python", "ecosystems/typescript"]
COMMANDS = {
    "status": ["status"],
    "report-asciidoc": ["report", "--format", "asciidoc"],
    "report-markdown": ["report", "--format", "markdown"],
    "export": ["export"],
}


def decode(raw: bytes) -> str:
    """Decode CLI output as the user would see it: UTF-8, else the console/locale code page.

    On Windows the CLI writes redirected ``status`` output in cp1252 (``·`` is 0xB7), while ``report`` is UTF-8.
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode(locale.getpreferredencoding(False), errors="replace")


def normalise(text: str) -> str:
    return ANSI.sub("", text).replace("\r\n", "\n")


def canonical(value):
    """Order-insensitive form of parsed JSON: ``export`` emits sets in an unstable order from run to run."""
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return sorted((canonical(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True))
    return value


def normalise_export(text: str) -> str:
    try:
        return json.dumps(canonical(json.loads(text)), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    except ValueError:
        return normalise(text)


def main() -> int:
    regression, out_dir = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    empty = []
    for fixture in FIXTURES:
        for name, args in COMMANDS.items():
            # Same entry point as the installed `reqstool` script, without depending on PATH.
            cmd = [
                sys.executable,
                "-m",
                "reqstool.command",
                *args,
                "local",
                "-p",
                str(regression / "fixtures" / fixture),
            ]
            p = subprocess.run(cmd, capture_output=True)
            out, err = decode(p.stdout), decode(p.stderr)
            key = f"{fixture.replace('/', '_')}-{name}"
            stdout = normalise_export(out) if name == "export" else normalise(out)
            body = f"{stdout}\n--- stderr ---\n{normalise(err)}\nexit={p.returncode}\n"
            (out_dir / f"{key}.txt").write_text(body, encoding="utf-8", newline="\n")
            print(f"{key:45} exit={p.returncode}")
            if not out.strip():
                empty.append(key)
                lines = [line for line in normalise(err).splitlines() if line.strip()]
                print(f"    no output; last stderr line: {lines[-1] if lines else '(none)'}")
    if empty:
        print(f"No output from: {', '.join(empty)}", file=sys.stderr)
    return 1 if empty else 0


if __name__ == "__main__":
    sys.exit(main())
