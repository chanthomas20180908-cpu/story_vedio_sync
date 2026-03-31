from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Iterable, Optional


ALLOWED_SUFFIXES = {".md", ".txt"}


@dataclass(frozen=True)
class RunResult:
    run_id: str
    run_dir: Path
    input_path: Path
    log_path: Path
    zip_path: Optional[Path]
    return_code: int
    results_dirs: list[Path]


def _now_run_id() -> str:
    # Example: 20260331_180912_123
    t = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    ms = int((time.time() * 1000) % 1000)
    return f"{t}_{ms:03d}"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _venv_python(repo_root: Path) -> Path:
    p = repo_root / ".venv" / "bin" / "python3"
    return p


def validate_and_copy_input(uploaded_path: str | os.PathLike[str], run_dir: Path) -> Path:
    src = Path(uploaded_path)
    if not src.exists() or not src.is_file():
        raise ValueError("上传文件不存在或不是文件")

    suffix = src.suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("只支持 .md / .txt 文件")

    in_dir = run_dir / "input"
    in_dir.mkdir(parents=True, exist_ok=True)

    # Keep original suffix; normalize name.
    dst = in_dir / f"input{suffix}"
    shutil.copyfile(src, dst)
    return dst


def _snapshot_dirs(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    return {p for p in root.glob("**/*") if p.is_dir()}


def _pick_new_or_recent_dirs(before: set[Path], after: set[Path]) -> list[Path]:
    created = sorted(after - before)
    if created:
        # Prefer top-level-ish created dirs
        return created

    # Fallback: pick most recently modified directories
    def mtime(p: Path) -> float:
        try:
            return p.stat().st_mtime
        except FileNotFoundError:
            return 0.0

    return sorted(list(after), key=mtime, reverse=True)[:5]


def _zip_results(run_dir: Path, results_dirs: Iterable[Path], log_path: Path) -> Optional[Path]:
    out_dir = run_dir / "downloads"
    out_dir.mkdir(parents=True, exist_ok=True)

    staging = run_dir / "_zip_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    # Put log + a pointer file.
    if log_path.exists():
        shutil.copyfile(log_path, staging / "run.log")

    results_list = list(results_dirs)
    (staging / "RESULTS_DIRS.txt").write_text(
        "\n".join(str(p) for p in results_list), encoding="utf-8"
    )

    # Copy directories (best-effort). Keep simple and predictable.
    copied_any = False
    for i, d in enumerate(results_list, start=1):
        if not d.exists() or not d.is_dir():
            continue
        dst = staging / f"results_{i}"
        try:
            shutil.copytree(d, dst, dirs_exist_ok=True)
            copied_any = True
        except Exception:
            # If copying fails (very large dirs / permissions), still produce zip with log.
            pass

    if not copied_any and not log_path.exists():
        return None

    zip_base = out_dir / "results"
    zip_path_str = shutil.make_archive(str(zip_base), "zip", root_dir=staging)
    return Path(zip_path_str)


def run_case_kesulu_001(
    uploaded_path: str | os.PathLike[str],
    provider: str = "cloubic",
) -> Generator[str, None, RunResult]:
    """Run the existing CLI via subprocess and yield log lines.

    Yields:
        log lines (already newline-stripped)

    Returns:
        RunResult
    """
    repo_root = _repo_root()
    run_id = _now_run_id()
    run_dir = repo_root / "data" / "web_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    log_path = run_dir / "run.log"

    input_path = validate_and_copy_input(uploaded_path, run_dir=run_dir)

    data_results_root = repo_root / "data" / "Data_results"
    before_dirs = _snapshot_dirs(data_results_root)

    py = _venv_python(repo_root)
    if not py.exists():
        # Fallback to system python3 path in PATH
        py = Path("python3")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root)

    cmd = [
        str(py),
        "-m",
        "workflow.story_video_001.cases.case_kesulu_001",
        "--input",
        str(input_path),
        "--provider",
        provider,
    ]

    yield f"run_id={run_id}"
    yield f"cmd={' '.join(cmd)}"

    with open(log_path, "w", encoding="utf-8") as lf:
        lf.write(f"run_id={run_id}\n")
        lf.write(f"repo_root={repo_root}\n")
        lf.write(f"input_path={input_path}\n")
        lf.write(f"provider={provider}\n")
        lf.write(f"cmd={' '.join(cmd)}\n")
        lf.write("\n")
        lf.flush()

        p = subprocess.Popen(
            cmd,
            cwd=str(repo_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        assert p.stdout is not None
        for line in p.stdout:
            s = line.rstrip("\n")
            lf.write(line)
            lf.flush()
            yield s

        rc = p.wait()
        yield f"\n[done] return_code={rc}"

    after_dirs = _snapshot_dirs(data_results_root)
    results_dirs = _pick_new_or_recent_dirs(before_dirs, after_dirs)
    zip_path = _zip_results(run_dir, results_dirs=results_dirs, log_path=log_path)

    return RunResult(
        run_id=run_id,
        run_dir=run_dir,
        input_path=input_path,
        log_path=log_path,
        zip_path=zip_path,
        return_code=rc,
        results_dirs=results_dirs,
    )
