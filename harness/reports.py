"""Send a script's diagnostics report to the repo's `decomp-reports` branch, where
Claude can read it: no copying and pasting.

A script announces its report by printing a line `DIAGNOSTICS: <path to .md>`.
The report is committed under reports/<project>/<time>.md (and reports/LATEST.md)
on the `decomp-reports` branch of the same GitHub repo the app updates from,
using a separate local clone (~/AIHarness/.reports-repo), so the app's own
checkout is never touched. The branch is never merged into main, so updates
don't download reports.
"""
import re
import shutil
import subprocess
import threading
from pathlib import Path

from .config import DATA_DIR, ROOT, settings

BRANCH = "decomp-reports"
CLONE = DATA_DIR / ".reports-repo"
MARKER = re.compile(r"DIAGNOSTICS: (.+\.md)\s*$")
_lock = threading.Lock()


def find_report(text: str):
    """The last report a run announced, if the file is still there."""
    found = None
    for line in text.splitlines():
        m = MARKER.search(line.strip())
        if m:
            found = m.group(1).strip()
    return Path(found) if found and Path(found).is_file() else None


def _git(cwd, *args, timeout=120):
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                       timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def _remote():
    """The app's own GitHub remote, with the token from Settings if one is set."""
    code, url = _git(ROOT, "remote", "get-url", "origin")
    if code != 0 or not url:
        raise RuntimeError("the app isn't a git checkout with an 'origin' remote")
    url = url.strip()
    m = re.match(r"(?:https://(?:[^@/]+@)?github\.com/|git@github\.com:)([^/]+)/(.+?)(?:\.git)?$", url)
    slug = f"{m.group(1)}/{m.group(2)}" if m else None
    token = settings.get("github_token").strip()
    if token and slug:
        url = f"https://x-access-token:{token}@github.com/{slug}.git"
    return url, slug


def _project(report: Path) -> str:
    # <workdir>/diagnostics/report-....md -> the workdir's name
    name = report.parent.parent.name if report.parent.name == "diagnostics" else report.parent.name
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-") or "project"


def send(report: Path) -> dict:
    """Commit the report to the decomp-reports branch and push it."""
    with _lock:
        try:
            url, slug = _remote()
            if not (CLONE / ".git").exists():
                if CLONE.exists():
                    shutil.rmtree(CLONE)
                CLONE.mkdir(parents=True)
                _git(CLONE, "init", "-q")
                _git(CLONE, "remote", "add", "origin", url)
            _git(CLONE, "remote", "set-url", "origin", url)
            code, out = _git(CLONE, "fetch", "-q", "--depth", "1", "origin", BRANCH)
            if code == 0:
                _git(CLONE, "checkout", "-q", "-B", BRANCH, "FETCH_HEAD")
            else:                                       # first report: a new, empty branch
                _git(CLONE, "checkout", "-q", "--orphan", BRANCH)
                _git(CLONE, "rm", "-rqf", "--ignore-unmatch", ".")
            project = _project(report)
            rel = Path("reports") / project / report.name
            dest = CLONE / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(report, dest)
            shutil.copyfile(report, CLONE / "reports" / "LATEST.md")
            (CLONE / "reports" / "LATEST.txt").write_text(f"{rel.as_posix()}\n")
            _git(CLONE, "add", "-A")
            code, out = _git(CLONE, "-c", "user.name=AI Harness", "-c",
                             "user.email=ai-harness@localhost", "commit", "-q", "-m",
                             f"Report: {project} {report.stem}")
            if code != 0 and "nothing to commit" not in out:
                return {"ok": False, "error": out[-800:]}
            for _ in range(3):
                code, out = _git(CLONE, "push", "-q", "origin", f"HEAD:{BRANCH}", timeout=300)
                if code == 0:
                    break
                # someone else pushed a report meanwhile: put ours on top and retry
                if _git(CLONE, "fetch", "-q", "origin", BRANCH)[0] == 0:
                    _git(CLONE, "rebase", "-q", "FETCH_HEAD")
            if code != 0:
                return {"ok": False, "error": _push_help(out)}
            link = (f"https://github.com/{slug}/blob/{BRANCH}/{rel.as_posix()}" if slug
                    else rel.as_posix())
            return {"ok": True, "path": rel.as_posix(), "url": link}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _push_help(out: str) -> str:
    tok = settings.get("github_token").strip()
    out = out.replace(tok, "***") if tok else out
    if re.search(r"auth|denied|403|could not read Username|permission", out, re.I):
        return ("GitHub didn't accept the push. Add a GitHub token in Settings → Reports "
                "(a fine-grained token with Contents: read and write on this repo), or sign "
                "git in to GitHub on this Mac. Git said: " + out[-400:])
    return out[-800:]
