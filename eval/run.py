"""Run prepared assessments sequentially through the installed Codex CLI."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def agent_options(model, effort):
    """Explicit settings keep ignored user config from disabling the Windows sandbox."""
    options = ["--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
               "--sandbox", "workspace-write", "--model", model,
               "-c", f'model_reasoning_effort="{effort}"',
               "-c", "plugins._default.enabled=false", "-c", 'web_search="disabled"',
               "--json", "--color", "never"]
    if os.name == "nt":
        options += ["-c", 'windows.sandbox="elevated"']
    return options


def run_one(folder, executable, model, seconds, effort="medium"):
    status_path = folder / "execution.json"
    if status_path.exists():
        raise ValueError("Run already attempted; prepare a fresh workspace rather than reusing patched files")
    command = [executable, "exec", *agent_options(model, effort),
               "-C", str(folder / "workspace"), "-o", str(folder / "last-message.txt"), "-"]
    started = time.monotonic()
    status = {"model_requested": model, "reasoning_effort": effort, "time_limit_seconds": seconds,
              "sandbox": "workspace-write", "windows_sandbox": "elevated" if os.name == "nt" else None,
              "web_search": "disabled", "plugins_default_enabled": False, "status": "running"}
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    with (folder / "events.jsonl").open("w", encoding="utf-8") as events, (folder / "stderr.txt").open("w", encoding="utf-8") as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=events, stderr=errors,
                                   text=True, encoding="utf-8", start_new_session=(os.name != "nt"))
        try:
            process.communicate((folder / "prompt.txt").read_text(encoding="utf-8"), timeout=seconds)
            status.update(status="completed" if process.returncode == 0 else "failed", exit_code=process.returncode)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=15)
            status.update(status="timed_out", exit_code=process.returncode)
    status["elapsed_seconds"] = round(time.monotonic() - started, 2)
    if status["status"] == "completed" and not (folder / "workspace/report.md").is_file():
        status.update(status="incomplete", reason="Agent exited without the requested report; inspect transcript before scoring")
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prepared", type=Path)
    parser.add_argument("--model", required=True, help="Use the same available model for every run")
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--run-id", help="Execute just one prepared run, e.g. 1-baseline")
    args = parser.parse_args()
    executable = shutil.which("codex")
    if not executable or args.seconds < 1:
        parser.error("An installed Codex CLI and a positive time budget are required")
    manifest = json.loads((args.prepared / "manifest.json").read_text())
    protocol = {"model_requested": args.model, "reasoning_effort": args.reasoning_effort,
                "seconds": args.seconds, "agent_options": agent_options(args.model, args.reasoning_effort),
                "cli_version": subprocess.check_output([executable, "--version"], text=True).strip()}
    protocol_path = args.prepared / "protocol.json"
    if protocol_path.exists():
        if json.loads(protocol_path.read_text()) != protocol:
            parser.error("Prepared suite already uses a different protocol; prepare fresh workspaces")
    else:
        with protocol_path.open("x", encoding="utf-8") as stream:
            json.dump(protocol, stream, indent=2)
    runs = [r for r in manifest["runs"] if args.run_id is None or r["id"] == args.run_id]
    if not runs:
        parser.error("Unknown run ID")
    for run in runs:
        result = run_one(args.prepared.resolve() / run["id"], executable, args.model, args.seconds, args.reasoning_effort)
        print(f"{run['id']}: {result['status']}", flush=True)
        if result["status"] in ("failed", "incomplete"):
            parser.exit(1, "Execution failed; inspect local logs before scheduling further runs.\n")
