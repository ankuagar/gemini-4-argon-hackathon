"""
cli_benchmark.py
Command-line benchmark runner for ArgonLedger.
Runs any (or all) of the 3 proving grounds end-to-end with live Gemini 4 Argon calls:
  1. Initial toolchain diagnostics
  2. Phase 1: Global Interface Ledger extraction
  3. Phase 2: Human-in-the-Loop approval gate
  4. Baseline comparison: File-by-File isolated migration
  5. Phase 3 & 4: Argon Whole-Repo Synthesis + Autonomous Verification Loop (`previous_interaction_id`)
"""
from __future__ import annotations

import sys
import time
from engine.migrator import MigrationOrchestrator


def run_benchmark(benchmark_id: str, thinking_level: str = "medium", run_baseline: bool = True) -> bool:
    orch = MigrationOrchestrator()
    t0 = time.monotonic()
    print(f"\n================================================================================")
    print(f"🚀 PROVING GROUND: {benchmark_id} (thinking_level={thinking_level})")
    print(f"================================================================================")

    s = orch.create_session(benchmark_id, thinking_level=thinking_level)
    init = s.initial_report or {}
    print(
        f"[{time.monotonic() - t0:5.1f}s] Initial State   -> "
        f"passed={init.get('passed')} | compile_errors={init.get('compile_errors')} | "
        f"tests={init.get('tests_passed')}/{init.get('tests_total')} | "
        f"escapes={init.get('escape_hatches')} | fuzz_divergences={init.get('fuzz_divergences')}"
    )

    s = orch.generate_ledger(s.session_id)
    contracts = (s.ledger or {}).get("contracts", [])
    print(
        f"[{time.monotonic() - t0:5.1f}s] Phase 1 Ledger  -> "
        f"extracted {len(contracts)} cross-file contracts | "
        f"interaction_id={s.ledger_interaction_id}"
    )

    s = orch.approve_ledger(s.session_id)
    print(f"[{time.monotonic() - t0:5.1f}s] Phase 2 HITL    -> Global Interface Ledger locked & approved.")

    if run_baseline:
        s = orch.run_baseline_file_by_file(s.session_id)
        base = s.baseline_report or {}
        print(
            f"[{time.monotonic() - t0:5.1f}s] Baseline (1x1)  -> "
            f"passed={base.get('passed')} | compile_errors={base.get('compile_errors')} | "
            f"tests={base.get('tests_passed')}/{base.get('tests_total')} | "
            f"escapes={base.get('escape_hatches')} | fuzz_divergences={base.get('fuzz_divergences')} "
            f"({s.baseline_elapsed_s}s, {s.baseline_tokens:,} tokens)"
        )

    s = orch.run_argon_migration(s.session_id)
    arg = s.argon_report or {}
    print(
        f"[{time.monotonic() - t0:5.1f}s] Argon WholeRepo -> "
        f"passed={arg.get('passed')} | turns={s.argon_iterations} | "
        f"compile_errors={arg.get('compile_errors')} | "
        f"tests={arg.get('tests_passed')}/{arg.get('tests_total')} | "
        f"escapes={arg.get('escape_hatches')} | "
        f"fuzz={arg.get('fuzz_passed')}/{arg.get('fuzz_total')} "
        f"({s.argon_elapsed_s}s, {s.argon_tokens:,} tokens)"
    )

    if not arg.get("passed"):
        print("\n--- Residual Diagnostics ---")
        print(arg.get("raw_diagnostics", ""))
        return False

    commit_info = orch.commit_approved_migration(s.session_id)
    print(f"[{time.monotonic() - t0:5.1f}s] Committed       -> {commit_info['committed_path']}")
    return True


if __name__ == "__main__":
    targets = sys.argv[1:] or ["linux_git_c_hardening", "c_to_rust_framecodec", "superset_ts6", "py_v1_to_v2"]
    all_ok = True
    for b_id in targets:
        ok = run_benchmark(b_id)
        if not ok:
            all_ok = False
    sys.exit(0 if all_ok else 1)
