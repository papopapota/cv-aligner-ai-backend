import subprocess
import sys
from pathlib import Path

_LEAF_END = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.")


def _is_relevant_python(path: Path) -> bool:
    return path.suffix == ".py" and path.parts[0] in {"src", "tests"}


def _module_reference(module: str) -> str:
    return f"src.{module}"


def _tests_referencing(test_root: Path, module: str) -> list[Path]:
    reference = _module_reference(module)
    matches: list[Path] = []
    for candidate in test_root.rglob("test_*.py"):
        try:
            content = candidate.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in content.splitlines():
            if reference not in line:
                continue
            rest = line.partition(reference)[2]
            if rest and rest[0] in _LEAF_END:
                continue
            matches.append(candidate)
            break
    return matches


def _collect_targets(files: list[str]) -> list[Path]:
    targets: list[Path] = []
    test_root = Path("tests")
    for raw in files:
        path = Path(raw)
        if not _is_relevant_python(path):
            continue
        if path.parts[0] == "tests":
            targets.append(path)
            continue
        if path.name == "__init__.py":
            continue
        rel = Path(*path.parts[1:])
        mirror = Path("tests", rel.parent, f"test_{rel.name}")
        if mirror.is_file():
            targets.append(mirror)
            continue
        targets.extend(_tests_referencing(test_root, ".".join(rel.with_suffix("").parts)))
    return sorted(set(targets))


def main() -> int:
    targets = _collect_targets(sys.argv[1:])
    if not targets:
        return 0
    return subprocess.call([sys.executable, "-m", "pytest", "-q", *(str(t) for t in targets)])


if __name__ == "__main__":
    raise SystemExit(main())