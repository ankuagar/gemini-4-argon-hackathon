"""
engine/migrator.py
Orchestrates the 3 Proving Grounds on Gemini 4 Argon (`gemini-4-argon`):
- Workspace sandboxing & initial baseline verification
- Phase 1: Global Interface Ledger synthesis (`thinking_level="high"`)
- Phase 2: Human-in-the-Loop Contract & Policy Approval Gate
- Phase 3: Naive File-by-File Baseline (no shared cross-file context)
- Phase 4: Argon Whole-Repo Synthesis + Autonomous Verification & Repair Loop (`previous_interaction_id`)
"""
from __future__ import annotations

import difflib
import json
import shutil
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from engine.argon_client import ArgonClient, FLASH_SUBAGENT_MODEL_ID, InteractionResult, MODEL_ID
from engine.verifiers import ROOT_DIR, VerificationReport, register_custom_verifier, verify_workspace


BENCHMARKS_DIR = ROOT_DIR / "benchmarks"
RUNS_DIR = ROOT_DIR / "runs"


# --- Structured Output Pydantic Schemas for Gemini 4 Argon ---

class ModuleContractSchema(BaseModel):
    file_path: str = Field(description="Relative path of the module in the repository.")
    role: str = Field(description="Concise description of module responsibility.")
    dependency_tier: int = Field(description="Migration order tier (1 = leaf module with no internal deps, higher = depends on lower tiers).")
    public_signatures: List[str] = Field(description="Exact exported function/type/struct signatures that downstream files must honor.")
    ownership_and_invariants: List[str] = Field(description="Memory ownership, slice lifetimes, strict optionality, or validation invariants.")
    cross_file_dependents: List[str] = Field(description="Other files in the repo that import or call this module.")


class InterfaceLedgerSchema(BaseModel):
    architectural_summary: str = Field(description="High-level root-cause analysis of cross-file coupling and why file-by-file edits fail.")
    migration_order: List[str] = Field(description="Dependency-ordered list of relative file paths to migrate (leaf modules first).")
    safety_policies: List[str] = Field(description="Strictness, type-safety, ABI, and memory-safety rules enforced across all files.")
    contracts: List[ModuleContractSchema] = Field(description="Locked interface contracts for each module.")


class SynthesizedFileSchema(BaseModel):
    file_path: str = Field(description="Relative path of the file being written.")
    content: str = Field(description="Complete, valid source code for this file.")
    change_summary: str = Field(description="Summary of interface and implementation updates made to this file.")


class MultiFileSynthesisSchema(BaseModel):
    coherence_notes: str = Field(description="Explanation of how cross-file interfaces were kept consistent across all updated files.")
    files: List[SynthesizedFileSchema] = Field(description="All migrated/repaired files in the repository.")


# --- Benchmark Definitions ---

@dataclass
class BenchmarkSpec:
    id: str
    title: str
    subtitle: str
    persona: str
    pain_point: str
    reference_link: str
    initial_dir: Path
    mutable_files: List[str]
    readonly_context_files: List[str]
    language: str
    task_instructions: str


BENCHMARK_SPECS: Dict[str, BenchmarkSpec] = {
    "superset_ts6": BenchmarkSpec(
        id="superset_ts6",
        title="Apache Superset Monorepo: TypeScript 5.4 → 6.0 Strict Migration",
        subtitle="Coordinated cross-package strict type upgrade (`exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`)",
        persona="Staff Frontend Architect @ Apache Superset (Issue #39539)",
        pain_point=(
            "Enabling strict TS 6 compiler flags (`exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, "
            "`verbatimModuleSyntax`, `useUnknownInCatchVariables`) breaks 6 interdependent packages and reducers. "
            "Fixing files one at a time causes conflicting optional/undefined property contracts and `any` escapes."
        ),
        reference_link="https://github.com/apache/superset/issues/39539",
        initial_dir=BENCHMARKS_DIR / "superset_ts6" / "initial",
        mutable_files=[
            "packages/superset-ui-core/src/query/types/QueryFormData.ts",
            "packages/superset-ui-core/src/connection/SupersetClientClass.ts",
            "packages/superset-ui-core/src/chart/models/ChartProps.ts",
            "packages/superset-ui-chart-controls/src/shared-controls/components/ColumnConfigControl.ts",
            "src/dashboard/reducers/dashboardState.ts",
            "src/explore/controlUtils/getFormDataFromControls.ts",
        ],
        readonly_context_files=[
            "tsconfig.json",
            "tests/superset_contracts.test.ts",
        ],
        language="typescript",
        task_instructions="""Upgrade all 6 mutable TypeScript source files to pass TypeScript's strict compiler settings in `tsconfig.json` AND pass all runtime assertions in `tests/superset_contracts.test.ts`:
1. `verbatimModuleSyntax: true` is active: any import of a TypeScript interface or type alias (`QueryFormData`, `AdhocFilter`, `ExtraFormData`, `QueryFormMetric`, `DatasourceColumn`, `ColumnConfigMap`, etc.) MUST use `import type { ... }` or inline `type` modifiers (`import { type QueryFormData, createSimpleFilter } from ...`), while value imports (`createSimpleFilter`, `normalizeMetricLabel`, `ChartProps`, `SupersetClientClass`) remain value imports with `.js` extensions.
2. `exactOptionalPropertyTypes: true` is active: you CANNOT assign `undefined` to an optional property `prop?: T` unless you either omit the property when undefined (e.g., conditionally spreading `...(clause !== undefined ? { clause } : {})` or `delete`) OR explicitly include `| undefined` in the interface property type where appropriate. Note: `tests/superset_contracts.test.ts` specifically asserts `assert.equal('clause' in filter1, false)` when `createSimpleFilter('country', '==', 'US')` is called without `clause`, AND checks `dashState.lastUpdatedFilterId === undefined` after `CLEAR_NATIVE_FILTER`.
3. `noUncheckedIndexedAccess: true` is active: array indexing (`metrics[0]`, `queriesData[0]`, `specs[0]`) and Record indexing (`controlsState['datasource']`, `state.sliceEntities[sliceId]`) return `T | undefined`. Handle undefined safely with fallbacks or explicit guards while preserving all return types expected by `tests/superset_contracts.test.ts`.
4. `useUnknownInCatchVariables: true` is active: narrow `err` using `err instanceof Error ? err.message : String(err)`.
5. ZERO type escapes allowed: do NOT use `any`, `as any`, `@ts-ignore`, `@ts-expect-error`, or `@ts-nocheck` anywhere.""",
    ),
    "c_to_rust_framecodec": BenchmarkSpec(
        id="c_to_rust_framecodec",
        title="Rust-for-Linux & Ladybird Style C-to-Safe-Rust Port: `libframecodec`",
        subtitle="0-`unsafe`, fallible-allocation idiomatic Rust port of a C RLE compression, CRC32/Adler16 & binary framing subsystem",
        persona="Linux Kernel (`Rust-for-Linux`) & Ladybird Browser Systems Security Maintainer",
        pain_point=(
            "Mechanical `c2rust` ports litter subsystems with `unsafe` raw pointers (`*const u8`, `*mut u8`) and panic-inducing `.unwrap()` calls. "
            "Refactoring C lifetimes into safe Rust slices (`&[u8]`), fallible `Result<T, FcError>` returns, and owned `FcBuffer` structs "
            "changes every caller across modules and risks silent wire-format divergence unless differentially fuzzed against C."
        ),
        reference_link="https://rust-for-linux.com/",
        initial_dir=BENCHMARKS_DIR / "c_to_rust_framecodec" / "initial",
        mutable_files=[
            "rust_port/src/lib.rs",
            "rust_port/src/crc32.rs",
            "rust_port/src/buffer.rs",
            "rust_port/src/compress.rs",
            "rust_port/src/packet.rs",
        ],
        readonly_context_files=[
            "c_src/framecodec.h",
            "c_src/crc32.c",
            "c_src/buffer.c",
            "c_src/compress.c",
            "c_src/packet.c",
            "c_src/test_cli.c",
            "rust_port/Cargo.toml",
            "rust_port/src/bin/rust_harness.rs",
            "rust_port/tests/contract_tests.rs",
        ],
        language="rust",
        task_instructions="""Port the C library in `c_src/` (`framecodec.h`, `crc32.c`, `buffer.c`, `compress.c`, `packet.c`) into 100% safe, idiomatic Rust across the 5 mutable files in `rust_port/src/` (`lib.rs`, `crc32.rs`, `buffer.rs`, `compress.rs`, `packet.rs`):
1. ZERO `unsafe` blocks and ZERO raw pointers (`*const`, `*mut`) are permitted anywhere in `rust_port/src/*.rs`.
2. Honor the exact public Rust signatures expected by `rust_port/src/bin/rust_harness.rs` and `rust_port/tests/contract_tests.rs`:
   - `fc_crc32(buf: &[u8]) -> u32`: IEEE 802.3 CRC32 (init `0xFFFF_FFFF`, poly `0xEDB8_8320`, final `!crc`).
   - `fc_adler16(buf: &[u8]) -> u16`: Mod-251 rolling checksum (`s1 = 1, s2 = 0`, `s1 = (s1 + b) % 251`, `s2 = (s2 + s1) % 251`, returns `((s2 << 8) | s1) as u16`).
   - `FcBuffer`: Safe `Vec<u8>`-backed buffer providing `with_capacity(cap: usize) -> Self`, `new() -> Self`, `clear(&mut self)`, `as_slice(&self) -> &[u8]`, `len(&self) -> usize`, `is_empty(&self) -> bool`, `extend_from_slice(&mut self, src: &[u8]) -> Result<(), FcError>`, `push_u8(&mut self, val: u8) -> Result<(), FcError>`, `push_u16_be(&mut self, val: u16) -> Result<(), FcError>`, `push_u32_be(&mut self, val: u32) -> Result<(), FcError>`.
   - `fc_rle_compress(in_buf: &[u8], out_buf: &mut FcBuffer) -> Result<(), FcError>`: Must match `c_src/compress.c` bit-for-bit! If `in_buf.len() > FC_MAX_PAYLOAD`, return `Err(FcError::Bounds)`. Runs of identical bytes with length >= 4 (capped at 255 per escape) OR any byte equal to `FC_RLE_MARKER (0xFF)` are emitted as `[0xFF, run as u8, byte]`. Runs < 4 where `byte != 0xFF` are emitted literally.
   - `fc_rle_decompress(in_buf: &[u8], out_buf: &mut FcBuffer) -> Result<(), FcError>`: Decodes `[0xFF, count, val]` into `count` copies of `val`. If `i + 2 >= in_buf.len()` or `count == 0`, return `Err(FcError::Corrupt)`. If `out_buf.len() + count > FC_MAX_PAYLOAD` (or `+ 1` for literal), return `Err(FcError::Bounds)`.
   - `fc_frame_encode(version: u8, flags: u8, seq: u16, payload: &[u8], out_frame: &mut FcBuffer) -> Result<(), FcError>` and `fc_frame_decode(frame: &[u8], out_payload: &mut FcBuffer) -> Result<FcHeader, FcError>`: Must match `c_src/packet.c` bit-for-bit on all 14 header bytes, compression flag (`FC_FLAG_COMPRESSED = 0x01`), error priority (`Corrupt` vs `Bounds` vs `Crc`), and CRC32/Adler16 verification.""",
    ),
    "linux_git_c_hardening": BenchmarkSpec(
        id="linux_git_c_hardening",
        title="Linux Kernel & Git C Subsystem Hardening: Memory Safety, SHA-256 Agility & Debt Purge",
        subtitle="Purge `get_cycles()`, eliminate global state for SHA-1/SHA-256 agility, zero stack-padding leaks, and enforce checked arithmetic",
        persona="Linux Kernel & Git Core Subsystem Maintainer auditing multi-file C refactoring patches",
        pain_point=(
            "Legacy C subsystems in the Linux kernel and Git suffer from 5 intertwined hazards: fake `get_cycles()` counters, "
            "global mutable `the_repo_hash_ctx` state with hardcoded 20-byte SHA-1 buffers, unbounded `strcpy()`/`sprintf()`, "
            "uninitialized struct alignment padding leaking kernel stack bytes to userspace, and integer overflow before buffer allocation."
        ),
        reference_link="https://gist.github.com/andy-shev/a2cb1ee4767d6d2f5d20db53ecb9aabc",
        initial_dir=BENCHMARKS_DIR / "linux_git_c_hardening" / "initial",
        mutable_files=[
            "src/timekeep.c",
            "src/oid_hash.c",
            "src/usercopy_ioctl.c",
            "src/pack_alloc.c",
        ],
        readonly_context_files=[
            "include/kobj_subsys.h",
            "tests/test_kernel_git_contracts.c",
        ],
        language="c",
        task_instructions="""Refactor all 4 mutable C source files in `src/` (`src/timekeep.c`, `src/oid_hash.c`, `src/usercopy_ioctl.c`, `src/pack_alloc.c`) to pass `clang -std=c11 -Wall -Wextra -Werror`, the Kernel/Git Security & Supply-Chain Static Audit, and all 5 security tests in `tests/test_kernel_git_contracts.c`:
1. `src/timekeep.c`:
   - Remove the banned `get_cycles()` function and banned `g_last_cycles` global variable completely.
   - Implement `uint64_t ktime_get_mono_ns(void)` using `clock_gettime(CLOCK_MONOTONIC, &ts)` returning `(uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec`.
   - Implement `int kobj_record_timestamp(kobj_repo_ctx_t *ctx, uint64_t now_ns, uint64_t *out_delta_ns)`: if `!ctx || !out_delta_ns` or `now_ns < ctx->last_timestamp_ns`, return `KOBJ_EINVAL`. Otherwise set `*out_delta_ns = now_ns - ctx->last_timestamp_ns`, update `ctx->last_timestamp_ns = now_ns`, increment `ctx->op_count++`, and return `KOBJ_OK`.
2. `src/oid_hash.c`:
   - Remove the banned global `the_repo_hash_ctx` variable and banned `sprintf()` calls completely.
   - Implement `int kobj_oid_init(kobj_oid_t *oid, kobj_hash_algo_t algo, const uint8_t *raw_bytes, size_t raw_len)`: validate `!oid || !raw_bytes`. If `algo == KOBJ_ALGO_SHA1`, require `raw_len == KOBJ_SHA1_RAW_LEN` (20); if `algo == KOBJ_ALGO_SHA256`, require `raw_len == KOBJ_SHA256_RAW_LEN` (32); otherwise return `KOBJ_EINVAL`. Zero `oid->raw` with `memset`, copy `raw_len` bytes, set `oid->algo = algo`, and return `KOBJ_OK`.
   - Implement `int kobj_oid_to_hex(const kobj_oid_t *oid, char *hex_out, size_t hex_out_size)`: determine `raw_len` (20 for SHA-1, 32 for SHA-256, else `KOBJ_EINVAL`). If `hex_out_size < (raw_len * 2 + 1)`, return `KOBJ_E2BIG`. Format each byte as lowercase hex (`0123456789abcdef`) without `sprintf()`, NUL-terminate `hex_out[raw_len * 2] = '\\0'`, and return `KOBJ_OK`.
3. `src/usercopy_ioctl.c`:
   - Remove all banned `strcpy()` calls.
   - Implement `int kobj_strscpy(char *dst, const char *src, size_t dst_size)`: if `!dst || !src || dst_size == 0`, return `KOBJ_EINVAL`. Copy up to `dst_size - 1` characters, always NUL-terminate `dst`. If `src` length >= `dst_size`, return `KOBJ_E2BIG`; otherwise return `(int)len`.
   - Implement `int kobj_build_ioctl_FromContext(...)`: MUST zero-initialize the entire `kobj_ioctl_resp_t resp` struct using `memset(&resp, 0, sizeof(resp))` BEFORE populating fields so the 3 bytes of compiler alignment padding between `flags` and `status` never leak uninitialized kernel stack memory! Use `kobj_strscpy(resp.label, label, sizeof(resp.label))` and propagate any negative error (like `KOBJ_E2BIG`).
4. `src/pack_alloc.c`:
   - Implement `int kobj_checked_alloc_size(size_t count, size_t elem_size, size_t header_bytes, size_t *out_total)`: validate `if (!out_total) return KOBJ_EINVAL;`. Check for multiplication overflow (`if (count != 0 && elem_size > SIZE_MAX / count) return KOBJ_EOVERFLOW;`) and addition overflow (`if (prod > SIZE_MAX - header_bytes) return KOBJ_EOVERFLOW;`). Store `*out_total = prod + header_bytes` and return `KOBJ_OK`.""",
    ),
    "py_v1_to_v2": BenchmarkSpec(
        id="py_v1_to_v2",
        title="Financial Settlement Service: Pydantic v1 → Strict Pydantic v2 + Mypy Upgrade",
        subtitle="Multi-module migration of validators, root_validators, Config classes, serialization aliases, and strict typing",
        persona="Lead Backend Engineer upgrading a regulated payment ledger service",
        pain_point=(
            "Upgrading Pydantic v1 to v2 across coupled domain models, risk engines, and stores triggers dozens of "
            "`PydanticDeprecatedSince20` errors, subtle validator ordering bugs, alias serialization mismatches, and `mypy --strict` failures."
        ),
        reference_link="https://docs.pydantic.dev/latest/migration/",
        initial_dir=BENCHMARKS_DIR / "py_v1_to_v2" / "initial",
        mutable_files=[
            "app/models/primitives.py",
            "app/models/transactions.py",
            "app/services/risk_engine.py",
            "app/services/ledger_store.py",
            "app/api/handlers.py",
        ],
        readonly_context_files=[
            "tests/test_settlement_flow.py",
        ],
        language="python",
        task_instructions="""Migrate all 5 mutable Python modules in `app/` from legacy Pydantic v1 to modern Pydantic v2 and full `mypy --strict` compliance:
1. Replace all Pydantic v1 constructs with Pydantic v2 equivalents:
   - `class Config:` -> `model_config = ConfigDict(...)` (`populate_by_name=True`, `frozen=True`, `str_strip_whitespace=True`, `json_schema_extra=...`).
   - `Field(..., regex=...)` -> `Field(..., pattern=...)`.
   - `@validator(..., pre=True)` -> `@field_validator(..., mode="before")` with `@classmethod`. Note: for `tags` in `SettlementInstruction`, replace `@validator("tags", each_item=True, pre=True)` with a `@field_validator("tags", mode="before")` that validates/cleans each item in the list!
   - `@root_validator` -> `@model_validator(mode="after")` operating on `self` (for `AccountRef`, mutate or use `object.__setattr__(self, "country_iso", ...)` or validate in `@field_validator("country_iso", mode="before")` + `@model_validator(mode="after")`).
   - `.dict(by_alias=True)` -> `.model_dump(by_alias=True)` (and if JSON-compatible primitives are needed or match test expectations, ensure `to_public_dict`, `to_wire_payload`, and `query_account_summary` return the exact dict keys expected by `tests/test_settlement_flow.py`).
   - `.json(by_alias=True)` -> `.model_dump_json(by_alias=True)`.
   - `.parse_raw(...)` -> `.model_validate_json(...)`.
   - `.parse_obj(...)` -> `.model_validate(...)`.
   - `.copy(update=...)` -> `.model_copy(update=...)`.
   - `__fields__` -> `model_fields`.
2. Must pass `mypy --strict app` with 0 errors and ZERO `# type: ignore` comments in `app/`. Every function parameter and return type must be explicitly annotated.
3. Must pass `pytest -W error tests/test_settlement_flow.py` with 0 failures and 0 deprecation warnings.""",
    ),
}


@dataclass
class RunEvent:
    timestamp: float
    phase: str
    level: str  # "info" | "thought" | "success" | "warn" | "error"
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class MigrationSession:
    session_id: str
    benchmark_id: str
    created_at: float
    status: str = "initialized"
    thinking_level: str = "high"
    use_long_decode_background: bool = False
    max_output_tokens: int = 65536
    initial_report: Optional[Dict[str, Any]] = None
    ledger: Optional[Dict[str, Any]] = None
    ledger_approved: bool = False
    ledger_interaction_id: Optional[str] = None
    baseline_report: Optional[Dict[str, Any]] = None
    baseline_tokens: int = 0
    baseline_elapsed_s: float = 0.0
    baseline_diffs: Dict[str, str] = field(default_factory=dict)
    argon_report: Optional[Dict[str, Any]] = None
    argon_tokens: int = 0
    argon_elapsed_s: float = 0.0
    argon_iterations: int = 0
    argon_diffs: Dict[str, str] = field(default_factory=dict)
    argon_coherence_notes: str = ""
    thought_timeline: List[Dict[str, Any]] = field(default_factory=list)
    events: List[RunEvent] = field(default_factory=list)
    committed_to_disk: bool = False

    def log(self, phase: str, level: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.events.append(
            RunEvent(
                timestamp=round(time.time(), 2),
                phase=phase,
                level=level,
                message=message,
                details=details,
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MigrationOrchestrator:
    def __init__(self) -> None:
        self.client = ArgonClient()
        self.sessions: Dict[str, MigrationSession] = {}
        RUNS_DIR.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str) -> Path:
        return RUNS_DIR / session_id

    def _prepare_workspace(self, benchmark_id: str, dest: Path) -> Path:
        spec = BENCHMARK_SPECS[benchmark_id]
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(spec.initial_dir, dest)
        return dest

    def _compute_diffs(self, initial_dir: Path, modified_dir: Path, files: List[str]) -> Dict[str, str]:
        diffs: Dict[str, str] = {}
        for rel in files:
            orig_p = initial_dir / rel
            mod_p = modified_dir / rel
            orig_lines = orig_p.read_text(encoding="utf-8").splitlines(keepends=True) if orig_p.exists() else []
            mod_lines = mod_p.read_text(encoding="utf-8").splitlines(keepends=True) if mod_p.exists() else []
            diff_text = "".join(
                difflib.unified_diff(
                    orig_lines,
                    mod_lines,
                    fromfile=f"a/{rel}",
                    tofile=f"b/{rel}",
                    n=3,
                )
            )
            if diff_text:
                diffs[rel] = diff_text
        return diffs

    def register_custom_benchmark(
        self,
        *,
        benchmark_id: str,
        title: str,
        subtitle: str,
        persona: str,
        pain_point: str,
        reference_link: str,
        source_dir: str,
        mutable_files: List[str],
        readonly_context_files: List[str],
        language: str,
        task_instructions: str,
        verify_cmd: str,
        forbidden_patterns: List[str],
    ) -> BenchmarkSpec:
        src_path = Path(source_dir).expanduser().resolve()
        if not src_path.exists() or not src_path.is_dir():
            raise ValueError(f"Source directory does not exist: {src_path}")

        spec = BenchmarkSpec(
            id=benchmark_id,
            title=title,
            subtitle=subtitle,
            persona=persona,
            pain_point=pain_point,
            reference_link=reference_link,
            initial_dir=src_path,
            mutable_files=mutable_files,
            readonly_context_files=readonly_context_files,
            language=language,
            task_instructions=task_instructions,
        )
        BENCHMARK_SPECS[benchmark_id] = spec
        register_custom_verifier(
            benchmark_id=benchmark_id,
            verify_cmd=verify_cmd,
            forbidden_patterns=forbidden_patterns,
            mutable_files=mutable_files,
        )
        return spec

    def create_session(
        self,
        benchmark_id: str,
        thinking_level: str = "medium",
        use_long_decode_background: bool = False,
    ) -> MigrationSession:
        if benchmark_id not in BENCHMARK_SPECS:
            raise ValueError(f"Unknown benchmark_id: {benchmark_id}")

        session_id = f"{benchmark_id}-{uuid.uuid4().hex[:8]}"
        max_tokens = 131072 if use_long_decode_background else 65536
        session = MigrationSession(
            session_id=session_id,
            benchmark_id=benchmark_id,
            created_at=time.time(),
            thinking_level=thinking_level,
            use_long_decode_background=use_long_decode_background,
            max_output_tokens=max_tokens,
        )
        self.sessions[session_id] = session

        # Prepare initial sandbox and run initial verification
        init_ws = self._prepare_workspace(benchmark_id, self._session_dir(session_id) / "initial_ws")
        session.log("init", "info", f"Running initial toolchain audit on `{benchmark_id}`...")
        init_rep = verify_workspace(benchmark_id, init_ws)
        session.initial_report = init_rep.to_dict()
        session.status = "audited"
        session.log(
            "init",
            "warn",
            f"Initial repository state: {init_rep.compile_errors} compile/type errors, "
            f"{init_rep.tests_passed}/{init_rep.tests_total} tests passing, "
            f"{init_rep.escape_hatches} safety/deprecation violations.",
        )
        return session

    def _build_repo_bundle(self, spec: BenchmarkSpec, workspace: Path) -> str:
        sections: List[str] = []
        sections.append("=== READ-ONLY REFERENCE & CONTRACT FILES (DO NOT MODIFY) ===")
        for rel in spec.readonly_context_files:
            fp = workspace / rel
            if fp.exists():
                sections.append(f"--- FILE: {rel} (READ-ONLY) ---\n{fp.read_text(encoding='utf-8')}\n")

        sections.append("=== MUTABLE REPOSITORY FILES (TO MIGRATE) ===")
        for rel in spec.mutable_files:
            fp = workspace / rel
            if fp.exists():
                sections.append(f"--- FILE: {rel} (MUTABLE) ---\n{fp.read_text(encoding='utf-8')}\n")
        return "\n".join(sections)

    def generate_ledger(self, session_id: str) -> MigrationSession:
        """
        Phase 1: Orchestrate `gemini-4-argon` (Lead Architect) across the whole repository
        while delegating parallel per-file static hazard & edge-case scans to `gemini-3.8-flash` subagents.
        """
        session = self.sessions[session_id]
        spec = BENCHMARK_SPECS[session.benchmark_id]
        init_ws = self._session_dir(session_id) / "initial_ws"

        session.status = "generating_ledger"
        ledger_thinking = "low"
        session.log(
            "ledger",
            "info",
            f"Lead Architect `gemini-4-argon` (thinking_level='{ledger_thinking}') analyzing {len(spec.mutable_files) + len(spec.readonly_context_files)} files + dispatching {min(4, len(spec.mutable_files))} parallel `gemini-3.8-flash` leaf subagents...",
        )

        repo_bundle = self._build_repo_bundle(spec, init_ws)
        diag = (session.initial_report or {}).get("raw_diagnostics", "")

        prompt = f"""You are ArgonLedger, a Principal Software Migration Architect powered by Gemini 4 Argon.
Analyze the entire repository below and its current toolchain diagnostics.
Produce a concise Global Interface Ledger that locks down every cross-file signature, type contract, ownership/lifetime invariant, and dependency-ordered migration plan BEFORE any code is changed.

BENCHMARK: {spec.title}
TASK REQUIREMENTS:
{spec.task_instructions}

INITIAL TOOLCHAIN DIAGNOSTICS:
{diag}

FULL REPOSITORY CONTEXT:
{repo_bundle}
"""

        class FlashLeafAuditSchema(BaseModel):
            hazard_spotted: str = Field(description="1-sentence critical bug, memory hazard, or type drift in this file.")
            edge_case_quirk: str = Field(description="1-sentence non-obvious edge case or build quirk to watch out for.")

        flash_schema = FlashLeafAuditSchema.model_json_schema()

        def _run_flash_subagent(rel_path: str) -> Dict[str, Any]:
            fp = init_ws / rel_path
            code = fp.read_text(encoding="utf-8") if fp.exists() else ""
            sub_prompt = f"""You are a fast `gemini-3.8-flash` Leaf Module Subagent reporting to the `gemini-4-argon` Lead Architect.
Inspect `{rel_path}` for benchmark `{spec.title}` and identify the single most critical hazard and edge-case quirk in 1 concise sentence each.

```
{code[:6000]}
```"""
            try:
                sub_res = self.client.interact(
                    sub_prompt,
                    model=FLASH_SUBAGENT_MODEL_ID,
                    thinking_level="low",
                    max_output_tokens=1024,
                    json_schema=flash_schema,
                )
                parsed = FlashLeafAuditSchema.model_validate_json(sub_res.output_text)
                return {
                    "file_path": rel_path,
                    "model": FLASH_SUBAGENT_MODEL_ID,
                    "hazard_spotted": parsed.hazard_spotted,
                    "edge_case_quirk": parsed.edge_case_quirk,
                    "elapsed_s": sub_res.elapsed_seconds,
                    "tokens": sub_res.total_tokens,
                }
            except Exception as exc:
                return {
                    "file_path": rel_path,
                    "model": FLASH_SUBAGENT_MODEL_ID,
                    "hazard_spotted": "Cross-module signature and boundary check required.",
                    "edge_case_quirk": f"Subagent fast scan note ({exc})",
                    "elapsed_s": 0.0,
                    "tokens": 0,
                }

        leaf_targets = spec.mutable_files[:4]
        with ThreadPoolExecutor(max_workers=1 + len(leaf_targets)) as pool:
            argon_future = pool.submit(
                self.client.interact,
                prompt,
                model=MODEL_ID,
                thinking_level=ledger_thinking,
                max_output_tokens=16384,
                json_schema=InterfaceLedgerSchema.model_json_schema(),
            )
            flash_futures = [pool.submit(_run_flash_subagent, rel) for rel in leaf_targets]
            res: InteractionResult = argon_future.result()
            flash_reports = [f.result() for f in flash_futures]

        session.ledger_interaction_id = res.interaction_id
        session.argon_tokens += res.total_tokens
        session.argon_elapsed_s = round(session.argon_elapsed_s + res.elapsed_seconds, 2)

        for idx, t in enumerate(res.thoughts):
            thought_entry = {
                "phase": "Phase 1: Global Interface Ledger (Argon Lead Architect)",
                "step": idx + 1,
                "thinking_level": res.thinking_level,
                "summary": t.summary_text,
                "has_signature": t.has_signature,
                "interaction_id": res.interaction_id,
            }
            session.thought_timeline.append(thought_entry)
            session.log("ledger", "thought", t.summary_text[:300], thought_entry)

        ledger_obj = InterfaceLedgerSchema.model_validate_json(res.output_text)
        ledger_dict = ledger_obj.model_dump()
        for c in ledger_dict["contracts"]:
            c["locked"] = True
        ledger_dict["flash_subagents"] = flash_reports
        session.ledger = ledger_dict
        session.status = "awaiting_human_approval"
        session.log(
            "ledger",
            "success",
            f"Lead Architect `gemini-4-argon` synthesized Global Interface Ledger ({len(ledger_dict['contracts'])} contracts) + {len(flash_reports)} parallel `gemini-3.8-flash` subagent audits in {res.elapsed_seconds}s ({res.total_tokens:,} tokens). Awaiting human review & lock approval.",
        )
        return session

    def approve_ledger(self, session_id: str, updated_ledger: Optional[Dict[str, Any]] = None) -> MigrationSession:
        """Phase 2: Human-in-the-Loop approves (and optionally customizes) the Interface Ledger."""
        session = self.sessions[session_id]
        if updated_ledger is not None:
            session.ledger = updated_ledger
        session.ledger_approved = True
        session.status = "ledger_approved"
        session.log(
            "hitl",
            "success",
            "Human-in-the-Loop approved and locked the Global Interface Ledger. Ready for execution.",
        )
        return session

    def run_baseline_file_by_file(self, session_id: str) -> MigrationSession:
        """
        Phase 3 (Baseline): Naive File-by-File LLM migration without shared cross-file context.
        Demonstrates the 'accuracy drops off at scale / interface drift' failure mode.
        Runs isolated single-file translations concurrently.
        """
        session = self.sessions[session_id]
        spec = BENCHMARK_SPECS[session.benchmark_id]
        base_ws = self._prepare_workspace(
            session.benchmark_id, self._session_dir(session_id) / "baseline_ws"
        )

        session.status = "running_baseline"
        session.log(
            "baseline",
            "info",
            f"Running Baseline (File-by-File isolated translation across {len(spec.mutable_files)} files with NO shared cross-file context or Interface Ledger)...",
        )

        total_tokens = 0
        start_t = time.monotonic()

        class SingleFileSchema(BaseModel):
            content: str = Field(description="Complete updated source code for this single file.")

        schema_dict = SingleFileSchema.model_json_schema()

        def _migrate_single_file(rel_path: str) -> Tuple[str, Optional[str], int, Optional[str]]:
            fp = base_ws / rel_path
            orig_code = fp.read_text(encoding="utf-8")
            isolated_prompt = f"""Migrate or refactor the following single {spec.language} file in isolation (upgrade legacy idioms, types, or safety issues).
You do NOT have access to the other files in the repository—infer any external types or signatures locally.
File path: {rel_path}

```
{orig_code}
```"""
            res = self.client.interact(
                isolated_prompt,
                thinking_level="low",
                max_output_tokens=16384,
                json_schema=schema_dict,
            )
            try:
                parsed = SingleFileSchema.model_validate_json(res.output_text)
                return rel_path, parsed.content, res.total_tokens, None
            except Exception as exc:
                return rel_path, None, res.total_tokens, str(exc)

        with ThreadPoolExecutor(max_workers=min(6, len(spec.mutable_files))) as pool:
            results = list(pool.map(_migrate_single_file, spec.mutable_files))

        for rel_path, new_content, toks, err in results:
            total_tokens += toks
            if new_content is not None:
                (base_ws / rel_path).write_text(new_content, encoding="utf-8")
            elif err:
                session.log("baseline", "warn", f"Baseline parse error on {rel_path}: {err}")

        elapsed = round(time.monotonic() - start_t, 2)
        rep = verify_workspace(session.benchmark_id, base_ws)
        session.baseline_report = rep.to_dict()
        session.baseline_tokens = total_tokens
        session.baseline_elapsed_s = elapsed
        session.baseline_diffs = self._compute_diffs(spec.initial_dir, base_ws, spec.mutable_files)
        session.status = "baseline_completed"

        session.log(
            "baseline",
            "warn" if not rep.passed else "info",
            f"Baseline (File-by-File) finished in {elapsed}s ({total_tokens:,} tokens): "
            f"{rep.compile_errors} compile errors, {rep.tests_passed}/{rep.tests_total} tests passed, "
            f"{rep.escape_hatches} escapes, {rep.fuzz_divergences} fuzz/contract divergences.",
        )
        return session

    def run_argon_migration(self, session_id: str, max_repair_turns: int = 2) -> MigrationSession:
        """
        Phase 4: Argon Whole-Repo Synthesis + Autonomous Verification Loop (`previous_interaction_id`).
        Requires Human-in-the-Loop Ledger Approval first.
        """
        session = self.sessions[session_id]
        if not session.ledger_approved:
            raise PermissionError("Human-in-the-Loop must approve the Global Interface Ledger before running migration.")

        spec = BENCHMARK_SPECS[session.benchmark_id]
        argon_ws = self._prepare_workspace(
            session.benchmark_id, self._session_dir(session_id) / "argon_ws"
        )

        session.status = "running_argon"
        repo_bundle = self._build_repo_bundle(spec, argon_ws)
        ledger_json = json.dumps(session.ledger, indent=2)
        init_diag = (session.initial_report or {}).get("raw_diagnostics", "")

        session.log(
            "argon",
            "info",
            f"Synthesizing all {len(spec.mutable_files)} files simultaneously in Gemini 4 Argon's unified 1M-token window "
            f"(thinking_level='{session.thinking_level}', max_output_tokens={session.max_output_tokens:,}, background={session.use_long_decode_background})...",
        )

        if session.ledger_interaction_id:
            synthesis_prompt = f"""You are ArgonLedger executing Phase 3: Whole-Repository Coordinated Synthesis with Gemini 4 Argon.
Using the full repository context already in this interaction session (`previous_interaction_id`), the human maintainer has reviewed and LOCKED the following Global Interface Ledger:
{ledger_json}

Generate the complete, migrated source code for ALL {len(spec.mutable_files)} mutable files in a single coherent pass so every cross-file import, type, lifetime, and return signature matches 100% and resolves all initial diagnostics.
Keep `change_summary` concise (1 short sentence per file).
Return a JSON object matching MultiFileSynthesisSchema containing ALL {len(spec.mutable_files)} mutable files:
{json.dumps(spec.mutable_files)}
"""
        else:
            synthesis_prompt = f"""You are ArgonLedger executing Phase 3: Whole-Repository Coordinated Synthesis with Gemini 4 Argon.
The human engineer has reviewed and LOCKED the following Global Interface Ledger.
You must now generate the complete, migrated source code for ALL {len(spec.mutable_files)} mutable files in a single coherent pass so every cross-file import, type, lifetime, and return signature matches 100%.

BENCHMARK: {spec.title}
TASK INSTRUCTIONS:
{spec.task_instructions}

HUMAN-LOCKED GLOBAL INTERFACE LEDGER:
{ledger_json}

INITIAL TOOLCHAIN DIAGNOSTICS TO RESOLVE:
{init_diag}

COMPLETE REPOSITORY SOURCE & READ-ONLY CONTRACT TESTS:
{repo_bundle}

Return a JSON object matching MultiFileSynthesisSchema containing ALL {len(spec.mutable_files)} mutable files:
{json.dumps(spec.mutable_files)}
"""

        def _poll_cb(status: str, elapsed: float) -> None:
            session.log(
                "argon",
                "info",
                f"Long-decode background execution in progress (status={status}, elapsed={elapsed:.1f}s)...",
            )

        res = self.client.interact(
            synthesis_prompt,
            thinking_level=session.thinking_level,
            max_output_tokens=session.max_output_tokens,
            previous_interaction_id=session.ledger_interaction_id,
            json_schema=MultiFileSynthesisSchema.model_json_schema(),
            force_background=session.use_long_decode_background,
            on_poll=_poll_cb,
        )

        session.argon_iterations = 1
        session.argon_tokens += res.total_tokens
        session.argon_elapsed_s = round(session.argon_elapsed_s + res.elapsed_seconds, 2)
        last_interaction_id = res.interaction_id

        for idx, t in enumerate(res.thoughts):
            entry = {
                "phase": "Phase 3: Whole-Repo Synthesis (Turn 1)",
                "step": idx + 1,
                "thinking_level": res.thinking_level,
                "summary": t.summary_text,
                "has_signature": t.has_signature,
                "interaction_id": res.interaction_id,
            }
            session.thought_timeline.append(entry)
            session.log("argon", "thought", t.summary_text[:300], entry)

        self._apply_synthesized_files(session, argon_ws, res.output_text)

        # Run toolchain verification + autonomous repair loop via previous_interaction_id
        rep = verify_workspace(session.benchmark_id, argon_ws)
        turn = 1
        while not rep.passed and turn <= max_repair_turns:
            turn += 1
            session.argon_iterations = turn
            session.log(
                "verify",
                "warn",
                f"Verification Turn {turn - 1} found residuals (compile_errors={rep.compile_errors}, "
                f"tests={rep.tests_passed}/{rep.tests_total}, escapes={rep.escape_hatches}, fuzz_divergences={rep.fuzz_divergences}). "
                f"Triggering Autonomous Repair Loop via `previous_interaction_id={last_interaction_id}`...",
            )

            repair_prompt = f"""Toolchain verification on your synthesized repository reported the following residual errors/divergences.
Using server-side state (`previous_interaction_id`), repair ONLY the affected mutable files while strictly preserving the Global Interface Ledger and all passing contracts.

TOOLCHAIN VERIFICATION DIAGNOSTICS:
{rep.raw_diagnostics}

Return ONLY the modified mutable file(s) that needed fixes in MultiFileSynthesisSchema."""

            repair_res = self.client.interact(
                repair_prompt,
                thinking_level="low",
                max_output_tokens=32768,
                previous_interaction_id=last_interaction_id,
                json_schema=MultiFileSynthesisSchema.model_json_schema(),
            )
            last_interaction_id = repair_res.interaction_id
            session.argon_tokens += repair_res.total_tokens
            session.argon_elapsed_s = round(session.argon_elapsed_s + repair_res.elapsed_seconds, 2)

            for idx, t in enumerate(repair_res.thoughts):
                entry = {
                    "phase": f"Phase 4: Autonomous Verification Repair (Turn {turn})",
                    "step": idx + 1,
                    "thinking_level": repair_res.thinking_level,
                    "summary": t.summary_text,
                    "has_signature": t.has_signature,
                    "interaction_id": repair_res.interaction_id,
                }
                session.thought_timeline.append(entry)
                session.log("verify", "thought", t.summary_text[:300], entry)

            self._apply_synthesized_files(session, argon_ws, repair_res.output_text)
            rep = verify_workspace(session.benchmark_id, argon_ws)

        session.argon_report = rep.to_dict()
        session.argon_diffs = self._compute_diffs(spec.initial_dir, argon_ws, spec.mutable_files)
        session.status = "completed" if rep.passed else "completed_with_warnings"

        session.log(
            "verify",
            "success" if rep.passed else "warn",
            f"Argon Whole-Repo Migration completed in {session.argon_iterations} turn(s) "
            f"({session.argon_elapsed_s}s total, {session.argon_tokens:,} tokens): "
            f"compile_errors={rep.compile_errors}, tests={rep.tests_passed}/{rep.tests_total}, "
            f"escapes={rep.escape_hatches}, differential_fuzz={rep.fuzz_passed}/{rep.fuzz_total} passed!",
        )
        return session

    def _apply_synthesized_files(self, session: MigrationSession, workspace: Path, raw_json: str) -> None:
        spec = BENCHMARK_SPECS[session.benchmark_id]
        allowed = set(spec.mutable_files)
        parsed = MultiFileSynthesisSchema.model_validate_json(raw_json)
        session.argon_coherence_notes = parsed.coherence_notes
        for fitem in parsed.files:
            clean_rel = fitem.file_path.lstrip("./")
            if clean_rel in allowed:
                target = workspace / clean_rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(fitem.content, encoding="utf-8")

    def commit_approved_migration(self, session_id: str) -> Dict[str, Any]:
        """Human-in-the-Loop final gate: export verified migration snapshot to `verified_outputs/<benchmark_id>/`."""
        session = self.sessions.get(session_id)
        benchmark_id = session.benchmark_id if session else session_id.rsplit("-", 1)[0]
        spec = BENCHMARK_SPECS.get(benchmark_id)
        argon_ws = self._session_dir(session_id) / "argon_ws"
        if not argon_ws.exists():
            raise ValueError("No Argon workspace found to commit.")
        export_dir = ROOT_DIR / "verified_outputs" / benchmark_id
        if export_dir.exists():
            shutil.rmtree(export_dir)
        shutil.copytree(argon_ws, export_dir)
        rel_export = str(export_dir.relative_to(ROOT_DIR))
        if session:
            session.committed_to_disk = True
            session.log(
                "hitl",
                "success",
                f"Human-approved migration exported to `{rel_export}`.",
            )
        return {
            "committed_path": rel_export,
            "committed_to": str(export_dir),
            "files": spec.mutable_files if spec else [],
            "session_id": session_id,
        }
