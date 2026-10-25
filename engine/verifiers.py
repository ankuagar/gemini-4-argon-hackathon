"""
engine/verifiers.py
Real toolchain verification suites for all 3 Proving Grounds:
1. superset_ts6: TypeScript compiler (`tsc --noEmit` + build), Node contract test runner, strictness escape scanner (`any`, `@ts-ignore`), and public symbol contract verifier.
2. c_to_rust_framecodec: Clang C reference build, Cargo build & `cargo test`, `unsafe` & raw pointer AST/token audit, and Live C-vs-Rust Differential Fuzzer (100+ randomized & edge-case inputs).
3. py_v1_to_v2: `mypy --strict` static type checker, `pytest -W error` (zero deprecation warnings allowed), and Pydantic v1 legacy symbol scanner.
"""
from __future__ import annotations

import os
import random
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT_DIR = Path("/Users/user/gemini-4-argon-hackathon")
TSC_BIN = ROOT_DIR / "node_modules" / ".bin" / "tsc"
PYTHON_BIN = ROOT_DIR / "venv" / "bin" / "python"
PYTEST_BIN = ROOT_DIR / "venv" / "bin" / "pytest"
MYPY_BIN = ROOT_DIR / "venv" / "bin" / "mypy"
CARGO_HOME = ROOT_DIR / ".cargo"
RUSTUP_HOME = ROOT_DIR / ".rustup"


def _get_rust_env() -> Dict[str, str]:
    env = os.environ.copy()
    cargo_bin = str(CARGO_HOME / "bin")
    if CARGO_HOME.exists():
        env["CARGO_HOME"] = str(CARGO_HOME)
    if RUSTUP_HOME.exists():
        env["RUSTUP_HOME"] = str(RUSTUP_HOME)
    env["PATH"] = f"{cargo_bin}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:{env.get('PATH', '')}"
    return env


@dataclass
class VerificationReport:
    benchmark_id: str
    passed: bool
    compile_errors: int
    tests_passed: int
    tests_total: int
    escape_hatches: int
    escape_details: List[str] = field(default_factory=list)
    fuzz_total: int = 0
    fuzz_passed: int = 0
    fuzz_divergences: int = 0
    fuzz_details: List[str] = field(default_factory=list)
    interface_integrity_pct: float = 100.0
    safe_code_pct: float = 100.0
    raw_diagnostics: str = ""
    per_file_errors: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def verify_superset_ts6(workspace: Path) -> VerificationReport:
    """Run TypeScript 6/7 strict compiler, contract test suite, and escape-hatch audit."""
    diagnostics: List[str] = []
    per_file_errors: Dict[str, int] = {}

    # 1. Run tsc --noEmit
    proc = subprocess.run(
        [str(TSC_BIN), "-p", "tsconfig.json", "--noEmit", "--pretty", "false"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=30,
    )
    tsc_out = (proc.stdout + "\n" + proc.stderr).strip()
    error_lines = [line for line in tsc_out.splitlines() if ": error TS" in line]
    compile_errors = len(error_lines)

    for line in error_lines:
        file_part = line.split("(")[0].strip()
        per_file_errors[file_part] = per_file_errors.get(file_part, 0) + 1

    if compile_errors > 0:
        diagnostics.append(f"=== TypeScript Strict Compiler Errors ({compile_errors}) ===\n" + "\n".join(error_lines[:40]))

    # 2. Check for forbidden strictness escapes in source files
    escape_details: List[str] = []
    ts_files = list((workspace / "packages").rglob("*.ts")) + list((workspace / "src").rglob("*.ts"))
    for fpath in ts_files:
        rel = str(fpath.relative_to(workspace))
        content = fpath.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                if "@ts-ignore" in stripped or "@ts-expect-error" in stripped or "@ts-nocheck" in stripped:
                    escape_details.append(f"{rel}:{lineno}: Forbidden directive in '{stripped}'")
                continue
            if re.search(r":\s*any\b|\bas\s+any\b|<any>", line):
                escape_details.append(f"{rel}:{lineno}: Forbidden `any` type escape: '{stripped}'")

    tsconfig_text = (workspace / "tsconfig.json").read_text(encoding="utf-8")
    if '"strict": false' in tsconfig_text or '"exactOptionalPropertyTypes": false' in tsconfig_text:
        escape_details.append("tsconfig.json: Relaxed strictness flags are forbidden")

    if escape_details:
        diagnostics.append("=== Forbidden Type Escapes ===\n" + "\n".join(escape_details))

    # 3. Check public interface symbols across packages
    required_exports = [
        ("packages/superset-ui-core/src/query/types/QueryFormData.ts", ["normalizeMetricLabel", "createSimpleFilter", "QueryFormData", "AdhocFilter"]),
        ("packages/superset-ui-core/src/connection/SupersetClientClass.ts", ["SupersetClientClass", "ClientConfig", "RequestConfig"]),
        ("packages/superset-ui-core/src/chart/models/ChartProps.ts", ["ChartProps", "ChartPropsConfig"]),
        ("packages/superset-ui-chart-controls/src/shared-controls/components/ColumnConfigControl.ts", ["resolveColumnConfigs", "getPrimaryColumnSpec"]),
        ("src/dashboard/reducers/dashboardState.ts", ["dashboardStateReducer", "buildEffectiveSliceFormData"]),
        ("src/explore/controlUtils/getFormDataFromControls.ts", ["getFormDataFromControls", "hasControlValidationErrors"]),
    ]
    total_symbols = 0
    present_symbols = 0
    for rel_path, symbols in required_exports:
        fp = workspace / rel_path
        txt = fp.read_text(encoding="utf-8") if fp.exists() else ""
        for sym in symbols:
            total_symbols += 1
            if re.search(rf"\bexport\b.*\b{sym}\b", txt):
                present_symbols += 1
            else:
                diagnostics.append(f"Missing public contract export `{sym}` in {rel_path}")

    interface_integrity_pct = round((present_symbols / max(total_symbols, 1)) * 100.0, 1)

    # 4. Build and run runtime contract tests
    tests_total = 5
    tests_passed = 0
    if compile_errors == 0:
        build_proc = subprocess.run(
            [str(TSC_BIN), "-p", "tsconfig.json"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=30,
        )
        test_js = workspace / "dist" / "tests" / "superset_contracts.test.js"
        if build_proc.returncode == 0 and test_js.exists():
            run_proc = subprocess.run(
                ["node", str(test_js)],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=15,
            )
            if run_proc.returncode == 0 and "ALL_SUPERSET_CONTRACT_TESTS_PASSED" in run_proc.stdout:
                tests_passed = 5
            else:
                diagnostics.append(
                    "=== Runtime Contract Test Failure ===\n"
                    + (run_proc.stdout + "\n" + run_proc.stderr).strip()
                )
        else:
            diagnostics.append("=== Build Output Failure ===\n" + (build_proc.stdout + "\n" + build_proc.stderr).strip())

    passed = (
        compile_errors == 0
        and tests_passed == tests_total
        and len(escape_details) == 0
        and interface_integrity_pct == 100.0
    )

    return VerificationReport(
        benchmark_id="superset_ts6",
        passed=passed,
        compile_errors=compile_errors,
        tests_passed=tests_passed,
        tests_total=tests_total,
        escape_hatches=len(escape_details),
        escape_details=escape_details,
        fuzz_total=tests_total,
        fuzz_passed=tests_passed,
        fuzz_divergences=tests_total - tests_passed,
        interface_integrity_pct=interface_integrity_pct,
        safe_code_pct=max(0.0, 100.0 - len(escape_details) * 12.5),
        raw_diagnostics="\n\n".join(diagnostics),
        per_file_errors=per_file_errors,
    )


def _generate_fuzz_vectors() -> List[Tuple[str, List[str]]]:
    """Generate 80 deterministic + randomized + adversarial vectors for C vs Rust differential fuzzing."""
    rng = random.Random(20261025)
    vectors: List[Tuple[str, List[str]]] = []

    # 1. Edge case encode vectors
    edge_payloads = [
        b"",
        b"A",
        b"AAAA",
        b"AAAAAAAAAAAA",
        b"\xff",
        b"\xff\xff\xff\xff\xff",
        b"\x00\xff\x00\xff\xfa\xce",
        b"Hello Gemini 4 Argon! " * 8,
        bytes([0x42] * 300),  # Run > 255 boundary
        bytes(range(256)),
    ]
    for idx, payload in enumerate(edge_payloads):
        for flags in (0, 1):
            vectors.append(
                (
                    f"edge_encode_{idx}_f{flags}",
                    ["encode", str((idx % 3) + 1), str(flags), str(100 + idx), payload.hex()],
                )
            )

    # 2. Randomized encode vectors (varying entropy & RLE runs)
    for i in range(30):
        buf = bytearray()
        for _ in range(rng.randint(1, 12)):
            if rng.random() < 0.55:
                # Repeated run
                b = rng.choice([0x00, 0x41, 0x7F, 0xFE, 0xFF])
                buf.extend([b] * rng.randint(1, 70))
            else:
                # Random literal bytes
                buf.extend(rng.randbytes(rng.randint(1, 20)))
        flags = rng.choice([0, 1])
        seq = rng.randint(0, 65535)
        vectors.append((f"rand_encode_{i}", ["encode", "1", str(flags), str(seq), bytes(buf).hex()]))

    # 3. Adversarial / malformed decode vectors (testing corrupt headers, bad CRCs, truncated RLE escapes)
    malformed_frames = [
        b"",
        b"\xfa\xce",
        b"\xde\xad\x01\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00",  # Bad magic
        b"\xfa\xce\x01\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x05abcd",  # Length mismatch
        b"\xfa\xce\x01\x01\x00\x01\x00\x01\x00\x00\x00\x00\x00\x02\xff\x05",  # Truncated RLE escape
        b"\xfa\xce\x01\x01\x00\x01\x00\x01\x00\x00\x00\x00\x00\x03\xff\x00\x41",  # Zero-length RLE
        b"\xfa\xce\x01\x00\x00\x07\x00\x01\xde\xad\xbe\xef\x00\x0441424344",  # CRC mismatch
    ]
    for idx, raw_frame in enumerate(malformed_frames):
        vectors.append((f"malformed_decode_{idx}", ["decode", raw_frame.hex()]))

    return vectors


def verify_c_to_rust(workspace: Path) -> VerificationReport:
    """Compile C reference, compile & test Rust port, audit `unsafe` usage, and run differential fuzzer."""
    env = _get_rust_env()
    diagnostics: List[str] = []
    per_file_errors: Dict[str, int] = {}

    c_dir = workspace / "c_src"
    rust_dir = workspace / "rust_port"
    c_bin = workspace / "c_harness"

    # 1. Compile C reference binary with clang
    c_compile = subprocess.run(
        [
            "clang",
            "-O2",
            "-Wall",
            str(c_dir / "crc32.c"),
            str(c_dir / "buffer.c"),
            str(c_dir / "compress.c"),
            str(c_dir / "packet.c"),
            str(c_dir / "test_cli.c"),
            "-o",
            str(c_bin),
        ],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if c_compile.returncode != 0:
        diagnostics.append("=== C Reference Build Error ===\n" + c_compile.stderr)

    # 2. Scan Rust core files for `unsafe` blocks and raw pointers (`*const`, `*mut`)
    escape_details: List[str] = []
    total_fn_count = 0
    unsafe_fn_or_block_count = 0
    for rs_name in ["lib.rs", "crc32.rs", "buffer.rs", "compress.rs", "packet.rs"]:
        rs_path = rust_dir / "src" / rs_name
        if not rs_path.exists():
            continue
        text = rs_path.read_text(encoding="utf-8")
        fns = re.findall(r"\bfn\s+[a-zA-Z0-9_]+", text)
        total_fn_count += len(fns)
        for lineno, line in enumerate(text.splitlines(), start=1):
            code_part = line.split("//")[0]
            if re.search(r"\bunsafe\b", code_part):
                unsafe_fn_or_block_count += 1
                escape_details.append(f"src/{rs_name}:{lineno}: `unsafe` usage in core module: '{line.strip()}'")
            if re.search(r"\*(?:const|mut)\s+", code_part):
                escape_details.append(f"src/{rs_name}:{lineno}: Raw pointer in core module: '{line.strip()}'")

    safe_code_pct = round(
        max(0.0, 100.0 * (1.0 - (len(escape_details) / max(total_fn_count * 2, 8)))),
        1,
    )
    if escape_details:
        diagnostics.append("=== Memory-Safety Audit (Unsafe / Raw Pointers in Core Modules) ===\n" + "\n".join(escape_details))

    # 3. Run `cargo test --no-run` / `cargo check` to count compiler errors
    check_proc = subprocess.run(
        ["cargo", "check", "--tests", "--bins", "--message-format=short"],
        cwd=str(rust_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    check_out = (check_proc.stdout + "\n" + check_proc.stderr).strip()
    err_lines = [l for l in check_out.splitlines() if ": error" in l or l.startswith("error[") or l.startswith("error:")]
    # Filter out summary lines like "error: could not compile ..."
    real_err_lines = [
        l for l in err_lines
        if not l.startswith("error: could not compile") and not l.startswith("error: aborting due to")
    ]
    compile_errors = len(real_err_lines) if check_proc.returncode != 0 else 0
    if check_proc.returncode != 0 and compile_errors == 0:
        compile_errors = 1

    for line in real_err_lines:
        if ".rs:" in line:
            fpart = line.split(":")[0].strip()
            per_file_errors[fpart] = per_file_errors.get(fpart, 0) + 1

    if compile_errors > 0:
        diagnostics.append(f"=== Rust Compiler Errors ({compile_errors}) ===\n" + check_out[:3500])

    # 4. Run `cargo test` if compilation succeeded
    tests_total = 4
    tests_passed = 0
    if compile_errors == 0:
        test_proc = subprocess.run(
            ["cargo", "test", "--test", "contract_tests"],
            cwd=str(rust_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        t_out = test_proc.stdout + "\n" + test_proc.stderr
        m = re.search(r"test result: \w+\. (\d+) passed; (\d+) failed", t_out)
        if m:
            tests_passed = int(m.group(1))
            failed = int(m.group(2))
            tests_total = max(tests_total, tests_passed + failed)
        if test_proc.returncode != 0:
            diagnostics.append("=== Cargo Contract Tests Failed ===\n" + t_out[-2500:])

        # Build the binary for differential fuzzing
        subprocess.run(
            ["cargo", "build", "--bin", "rust_harness"],
            cwd=str(rust_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    # 5. Live C-vs-Rust Differential Fuzzer
    vectors = _generate_fuzz_vectors()
    fuzz_total = len(vectors)
    fuzz_passed = 0
    fuzz_divergences = 0
    fuzz_details: List[str] = []

    rust_bin = rust_dir / "target" / "debug" / "rust_harness"
    if compile_errors == 0 and c_bin.exists() and rust_bin.exists():
        for vec_name, args in vectors:
            c_res = subprocess.run([str(c_bin)] + args, capture_output=True, text=True, timeout=5)
            r_res = subprocess.run([str(rust_bin)] + args, capture_output=True, text=True, timeout=5)
            c_out = c_res.stdout.strip()
            r_out = r_res.stdout.strip()
            if c_out == r_out and c_res.returncode == r_res.returncode:
                fuzz_passed += 1
            else:
                fuzz_divergences += 1
                if len(fuzz_details) < 10:
                    fuzz_details.append(
                        f"[{vec_name}] args={args[:4]}:\n  C   : {c_out[:140]}\n  Rust: {r_out[:140]}"
                    )

            # If it was an encode vector that succeeded on C, also differentially fuzz decoding that exact wire frame!
            if args[0] == "encode" and "frame=" in c_out:
                frame_hex = c_out.split("frame=")[1].strip()
                if frame_hex:
                    fuzz_total += 1
                    c_dec = subprocess.run([str(c_bin), "decode", frame_hex], capture_output=True, text=True, timeout=5)
                    r_dec = subprocess.run([str(rust_bin), "decode", frame_hex], capture_output=True, text=True, timeout=5)
                    if c_dec.stdout.strip() == r_dec.stdout.strip():
                        fuzz_passed += 1
                    else:
                        fuzz_divergences += 1
                        if len(fuzz_details) < 10:
                            fuzz_details.append(
                                f"[{vec_name}_decode_roundtrip]:\n  C   : {c_dec.stdout.strip()[:140]}\n  Rust: {r_dec.stdout.strip()[:140]}"
                            )
    else:
        fuzz_divergences = fuzz_total
        fuzz_details.append("Rust binary did not compile; all differential fuzzing vectors failed.")

    if fuzz_details:
        diagnostics.append("=== C-vs-Rust Differential Fuzzer Divergences ===\n" + "\n".join(fuzz_details))

    passed = (
        compile_errors == 0
        and tests_passed == tests_total
        and len(escape_details) == 0
        and fuzz_divergences == 0
    )

    return VerificationReport(
        benchmark_id="c_to_rust_framecodec",
        passed=passed,
        compile_errors=compile_errors,
        tests_passed=tests_passed,
        tests_total=tests_total,
        escape_hatches=len(escape_details),
        escape_details=escape_details,
        fuzz_total=fuzz_total,
        fuzz_passed=fuzz_passed,
        fuzz_divergences=fuzz_divergences,
        fuzz_details=fuzz_details,
        interface_integrity_pct=100.0 if compile_errors == 0 else 50.0,
        safe_code_pct=safe_code_pct,
        raw_diagnostics="\n\n".join(diagnostics),
        per_file_errors=per_file_errors,
    )


def verify_py_v1_to_v2(workspace: Path) -> VerificationReport:
    """Run mypy --strict, pytest -W error (zero deprecation warnings), and Pydantic v1 legacy audit."""
    diagnostics: List[str] = []
    per_file_errors: Dict[str, int] = {}

    env = os.environ.copy()
    env["PYTHONPATH"] = str(workspace)

    # 1. Run mypy --strict app
    mypy_proc = subprocess.run(
        [str(MYPY_BIN), "--strict", "app"],
        cwd=str(workspace),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    mypy_out = (mypy_proc.stdout + "\n" + mypy_proc.stderr).strip()
    mypy_err_lines = [l for l in mypy_out.splitlines() if ": error:" in l]
    compile_errors = len(mypy_err_lines)
    for line in mypy_err_lines:
        fpart = line.split(":")[0].strip()
        per_file_errors[fpart] = per_file_errors.get(fpart, 0) + 1

    if compile_errors > 0:
        diagnostics.append(f"=== mypy --strict Errors ({compile_errors}) ===\n" + "\n".join(mypy_err_lines[:40]))

    # 2. Audit for forbidden Pydantic v1 patterns & type-ignore escapes in app/
    escape_details: List[str] = []
    v1_patterns = [
        (r"@validator\b", "Deprecated Pydantic v1 `@validator` (use `@field_validator`)"),
        (r"@root_validator\b", "Deprecated Pydantic v1 `@root_validator` (use `@model_validator`)"),
        (r"\bclass\s+Config\s*:", "Deprecated Pydantic v1 `class Config:` (use `model_config = ConfigDict(...)`)"),
        (r"\.dict\(", "Deprecated Pydantic v1 `.dict()` (use `.model_dump()`)"),
        (r"\.json\(", "Deprecated Pydantic v1 `.json()` (use `.model_dump_json()`)"),
        (r"\.parse_obj\(", "Deprecated Pydantic v1 `.parse_obj()` (use `.model_validate()`)"),
        (r"\.parse_raw\(", "Deprecated Pydantic v1 `.parse_raw()` (use `.model_validate_json()`)"),
        (r"\.copy\(\s*update=", "Deprecated Pydantic v1 `.copy(update=...)` (use `.model_copy(update=...)`)"),
        (r"__fields__", "Deprecated Pydantic v1 `__fields__` (use `model_fields`)"),
        (r"#\s*type:\s*ignore", "Forbidden `# type: ignore` suppression in app/"),
    ]
    for py_file in (workspace / "app").rglob("*.py"):
        rel = str(py_file.relative_to(workspace))
        content = py_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), start=1):
            if line.strip().startswith("#"):
                if re.search(r"#\s*type:\s*ignore", line):
                    escape_details.append(f"{rel}:{lineno}: Forbidden `# type: ignore`")
                continue
            for pat, desc in v1_patterns:
                if re.search(pat, line):
                    escape_details.append(f"{rel}:{lineno}: {desc}")
                    per_file_errors[rel] = per_file_errors.get(rel, 0) + 1

    if escape_details:
        diagnostics.append("=== Legacy Pydantic v1 Symbols / Type Escapes ===\n" + "\n".join(escape_details))

    # 3. Run pytest -W error (fails on any deprecation warning or test error)
    pytest_proc = subprocess.run(
        [str(PYTEST_BIN), "-W", "error", "-q", "tests/test_settlement_flow.py"],
        cwd=str(workspace),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    p_out = (pytest_proc.stdout + "\n" + pytest_proc.stderr).strip()
    tests_total = 5
    tests_passed = 0
    m_pass = re.search(r"(\d+)\s+passed", p_out)
    if m_pass:
        tests_passed = int(m_pass.group(1))
    if pytest_proc.returncode != 0:
        diagnostics.append("=== pytest -W error Output ===\n" + p_out[-3000:])

    passed = (
        compile_errors == 0
        and len(escape_details) == 0
        and pytest_proc.returncode == 0
        and tests_passed == tests_total
    )

    return VerificationReport(
        benchmark_id="py_v1_to_v2",
        passed=passed,
        compile_errors=compile_errors,
        tests_passed=tests_passed,
        tests_total=tests_total,
        escape_hatches=len(escape_details),
        escape_details=escape_details,
        fuzz_total=tests_total,
        fuzz_passed=tests_passed,
        fuzz_divergences=tests_total - tests_passed,
        interface_integrity_pct=100.0 if tests_passed == tests_total else round((tests_passed / tests_total) * 100.0, 1),
        safe_code_pct=max(0.0, round(100.0 - len(escape_details) * 5.0, 1)),
        raw_diagnostics="\n\n".join(diagnostics),
        per_file_errors=per_file_errors,
    )


def verify_linux_git_c(workspace: Path) -> VerificationReport:
    """
    Verify Linux Kernel & Git C Subsystem Hardening (`linux_git_c_hardening`):
    1. Static Kernel/Git Security & Supply-Chain Audit (banned `get_cycles`, `strcpy`, `sprintf`, global `the_repo_hash_ctx`, `g_last_cycles`, and supply-chain trojan primitives).
    2. Compile with `clang -std=c11 -Wall -Wextra -Werror`.
    3. Execute the 5-vector C Security & Architectural Contract Suite (stack-padding leak test, overflow arithmetic test, SHA-1/SHA-256 agility test, bounded strscpy test, monotonic clock test).
    """
    diagnostics: List[str] = []
    per_file_errors: Dict[str, int] = {}
    escape_details: List[str] = []

    banned_c_patterns = [
        (r"\bget_cycles\s*\(", "Banned legacy fake cycle counter `get_cycles()` (use `clock_gettime(CLOCK_MONOTONIC, ...)` in `ktime_get_mono_ns`)"),
        (r"\bg_last_cycles\b", "Banned non-reentrant global mutable state `g_last_cycles`"),
        (r"\bthe_repo_hash_ctx\b", "Banned Git global singleton `the_repo_hash_ctx` (use reentrant `kobj_repo_ctx_t` / explicit `algo`)"),
        (r"\bstrcpy\s*\(", "Banned unbounded `strcpy()` (use bounded copy / `kobj_strscpy()`)"),
        (r"\bsprintf\s*\(", "Banned unbounded `sprintf()` (use `snprintf()` or explicit hex nibbles)"),
        (r"\bstrcat\s*\(", "Banned unbounded `strcat()`"),
        (r"\b(?:system|popen|execve|fork|dlopen)\s*\(", "Supply-Chain Security Alert: Unauthorized process/dynamic-loader execution primitive"),
    ]

    for c_file in sorted((workspace / "src").glob("*.c")):
        rel = str(c_file.relative_to(workspace))
        content = c_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), start=1):
            code_part = line.split("//")[0]
            if code_part.strip().startswith("/*") or code_part.strip().startswith("*"):
                continue
            for pat, desc in banned_c_patterns:
                if re.search(pat, code_part):
                    escape_details.append(f"{rel}:{lineno}: {desc}")
                    per_file_errors[rel] = per_file_errors.get(rel, 0) + 1

    if escape_details:
        diagnostics.append(
            "=== Kernel/Git Security & Supply-Chain Static Audit ===\n" + "\n".join(escape_details)
        )

    test_bin = workspace / "kobj_test_runner"
    c_sources = [
        str(workspace / "src" / "timekeep.c"),
        str(workspace / "src" / "oid_hash.c"),
        str(workspace / "src" / "usercopy_ioctl.c"),
        str(workspace / "src" / "pack_alloc.c"),
        str(workspace / "tests" / "test_kernel_git_contracts.c"),
    ]
    compile_proc = subprocess.run(
        ["clang", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror"] + c_sources + ["-o", str(test_bin)],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=30,
    )
    c_out = (compile_proc.stdout + "\n" + compile_proc.stderr).strip()
    err_lines = [l for l in c_out.splitlines() if ": error:" in l or "Undefined symbols" in l or "ld: symbol(s) not found" in l]
    compile_errors = len(err_lines) if compile_proc.returncode != 0 else 0
    if compile_proc.returncode != 0 and compile_errors == 0:
        compile_errors = 1

    for line in err_lines:
        if ".c:" in line:
            fpart = line.split(":")[0].strip()
            per_file_errors[fpart] = per_file_errors.get(fpart, 0) + 1

    if compile_errors > 0:
        diagnostics.append(f"=== Clang Strict Compiler / Linker Errors ({compile_errors}) ===\n" + c_out[:3500])

    tests_total = 5
    tests_passed = 0
    if compile_errors == 0 and test_bin.exists():
        run_proc = subprocess.run(
            [str(test_bin)],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=10,
        )
        run_out = (run_proc.stdout + "\n" + run_proc.stderr).strip()
        tests_passed = len(re.findall(r"^\[PASS\]", run_proc.stdout, flags=re.MULTILINE))
        if run_proc.returncode != 0 or tests_passed < tests_total:
            diagnostics.append("=== Kernel/Git Security & Contract Test Failures ===\n" + run_out)

    passed = (
        compile_errors == 0
        and len(escape_details) == 0
        and tests_passed == tests_total
    )

    return VerificationReport(
        benchmark_id="linux_git_c_hardening",
        passed=passed,
        compile_errors=compile_errors,
        tests_passed=tests_passed,
        tests_total=tests_total,
        escape_hatches=len(escape_details),
        escape_details=escape_details,
        fuzz_total=tests_total,
        fuzz_passed=tests_passed,
        fuzz_divergences=tests_total - tests_passed,
        interface_integrity_pct=100.0 if compile_errors == 0 else 60.0,
        safe_code_pct=max(0.0, round(100.0 - len(escape_details) * 15.0, 1)),
        raw_diagnostics="\n\n".join(diagnostics),
        per_file_errors=per_file_errors,
    )


CUSTOM_VERIFIERS: Dict[str, Dict[str, Any]] = {}


def register_custom_verifier(
    benchmark_id: str,
    verify_cmd: str,
    forbidden_patterns: List[str],
    mutable_files: List[str],
) -> None:
    CUSTOM_VERIFIERS[benchmark_id] = {
        "verify_cmd": verify_cmd,
        "forbidden_patterns": forbidden_patterns,
        "mutable_files": mutable_files,
    }


def verify_custom_workspace(benchmark_id: str, workspace: Path) -> VerificationReport:
    cfg = CUSTOM_VERIFIERS[benchmark_id]
    verify_cmd = cfg["verify_cmd"]
    forbidden_patterns = cfg.get("forbidden_patterns", [])
    mutable_files = cfg.get("mutable_files", [])

    diagnostics: List[str] = []
    escape_details: List[str] = []
    per_file_errors: Dict[str, int] = {}

    for rel in mutable_files:
        fp = workspace / rel
        if not fp.exists():
            continue
        txt = fp.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(txt.splitlines(), start=1):
            for pat in forbidden_patterns:
                if pat and re.search(pat, line):
                    escape_details.append(f"{rel}:{lineno}: Matched forbidden pattern `{pat}` in '{line.strip()}'")
                    per_file_errors[rel] = per_file_errors.get(rel, 0) + 1

    if escape_details:
        diagnostics.append("=== Static Policy & Supply-Chain Audit ===\n" + "\n".join(escape_details))

    env = _get_rust_env()
    env["PYTHONPATH"] = str(workspace)
    proc = subprocess.run(
        verify_cmd,
        shell=True,
        cwd=str(workspace),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    out = (proc.stdout + "\n" + proc.stderr).strip()
    compile_errors = 0 if proc.returncode == 0 else max(1, len(re.findall(r"\berror\b", out, flags=re.IGNORECASE)))
    tests_total = 1
    tests_passed = 1 if proc.returncode == 0 else 0

    if proc.returncode != 0:
        diagnostics.append(f"=== Custom Verification Command (`{verify_cmd}`) Failed ===\n" + out[:3500])

    passed = (proc.returncode == 0) and (len(escape_details) == 0)
    return VerificationReport(
        benchmark_id=benchmark_id,
        passed=passed,
        compile_errors=compile_errors,
        tests_passed=tests_passed,
        tests_total=tests_total,
        escape_hatches=len(escape_details),
        escape_details=escape_details,
        fuzz_total=tests_total,
        fuzz_passed=tests_passed,
        fuzz_divergences=tests_total - tests_passed,
        interface_integrity_pct=100.0 if proc.returncode == 0 else 50.0,
        safe_code_pct=max(0.0, round(100.0 - len(escape_details) * 15.0, 1)),
        raw_diagnostics="\n\n".join(diagnostics),
        per_file_errors=per_file_errors,
    )


def verify_workspace(benchmark_id: str, workspace: Path) -> VerificationReport:
    if benchmark_id == "superset_ts6":
        return verify_superset_ts6(workspace)
    elif benchmark_id == "c_to_rust_framecodec":
        return verify_c_to_rust(workspace)
    elif benchmark_id == "py_v1_to_v2":
        return verify_py_v1_to_v2(workspace)
    elif benchmark_id == "linux_git_c_hardening":
        return verify_linux_git_c(workspace)
    elif benchmark_id in CUSTOM_VERIFIERS:
        return verify_custom_workspace(benchmark_id, workspace)
    raise ValueError(f"Unknown benchmark_id: {benchmark_id}")
