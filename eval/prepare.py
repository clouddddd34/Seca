"""Prepare isolated benchmark inputs; never copies evaluator answers or tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_FILES = ("app.py", "run.py", "requirements.txt", "README.md")
ARMS = ("baseline", "seca", "competitor")


def prepare(output, competitor, binary, fixture=None, task_path=None):
    fixture = Path(fixture) if fixture is not None else ROOT / "eval/fixture"
    task_path = Path(task_path) if task_path is not None else ROOT / "eval/task.txt"
    fixture_files = tuple(name for name in FIXTURE_FILES if (fixture / name).is_file())
    output, competitor, binary = output.resolve(), competitor.resolve(), binary.resolve()
    if output.exists():
        raise ValueError("Output must be a new directory")
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Use a destination outside the Seca repository")
    if output == competitor or competitor in output.parents:
        raise ValueError("Use a destination outside the competitor checkout")
    if not binary.is_file():
        raise ValueError("Build seca before preparing runs")
    if not (competitor / "skills/owasp-audit/SKILL.md").is_file():
        raise ValueError("Competitor checkout must include skills/owasp-audit/SKILL.md")
    license_text = (competitor / "LICENSE").read_text(encoding="utf-8")
    if "MIT License" not in license_text:
        raise ValueError("Competitor license changed; review it before copying")
    commit = subprocess.check_output(["git", "-C", str(competitor), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(competitor), "status", "--porcelain"], text=True)
    if dirty.strip():
        raise ValueError("Use an unmodified competitor checkout")
    task = task_path.read_text(encoding="utf-8")
    output.mkdir(parents=True)
    manifest = {"competitor_commit": commit, "competitor_url": "https://github.com/briiirussell/cybersecurity-skills",
                "task_sha256": hashlib.sha256(task.encode()).hexdigest(),
                "skill_sha256": {str(path.relative_to(ROOT / "security-audit")).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in sorted((ROOT / "security-audit").rglob('*')) if path.is_file()},
                "fixture_sha256": {name: hashlib.sha256((fixture / name).read_bytes()).hexdigest()
                                   for name in fixture_files},
                "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "runs": []}
    # Rotate order across repetitions to reduce a simple ordering effect.
    for repetition in range(3):
        for arm in ARMS[repetition:] + ARMS[:repetition]:
            name = f"{repetition + 1}-{arm}"
            work = output / name / "workspace"
            (work / "app").mkdir(parents=True)
            for filename in fixture_files:
                shutil.copy2(fixture / filename, work / "app" / filename)
            (work / "tools").mkdir()
            shutil.copy2(binary, work / "tools" / binary.name)
            prefix = "Do not invoke a security skill in this run.\n"
            if arm == "seca":
                shutil.copytree(ROOT / "security-audit", work / "assigned-skill")
                prefix = "Read assigned-skill/SKILL.md and apply that skill to the task below.\n"
            elif arm == "competitor":
                # Preserve relative links, companion skills, and upstream notices.
                for folder in ("skills", "shared", "scripts", "templates"):
                    if (competitor / folder).exists():
                        shutil.copytree(competitor / folder, work / "competitor" / folder)
                shutil.copy2(competitor / "LICENSE", work / "competitor/LICENSE")
                prefix = "Read competitor/skills/owasp-audit/SKILL.md and apply that skill to the task below.\n"
            (output / name / "prompt.txt").write_text(prefix + task, encoding="utf-8")
            manifest["runs"].append({"id": name, "arm": arm, "repetition": repetition + 1})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--competitor", type=Path, required=True)
    parser.add_argument("--binary", type=Path, default=ROOT / "target/debug" / ("seca.exe" if os.name == "nt" else "seca"))
    args = parser.parse_args()
    try:
        result = prepare(args.output, args.competitor, args.binary)
        print(f"Prepared {len(result['runs'])} fresh workspaces; no assessments executed.")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Preparation failed: {error}\n")
