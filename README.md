# ArgonLedger — Million-Token Codebase Migration & Verification Engine

**Powered by Google Gemini 4 Argon (`gemini-4-argon`) via the Interactions API**

**ArgonLedger** solves **Problem Statement One: Million Token Engineering** and the **Open-Source Maintainer Trust Gap** by executing whole-repository migrations, memory-safe language ports, C kernel/VCS subsystem hardenings, and strict framework upgrades in a single unified 1M-token context window—verified against live compilers (`clang`, `cargo`/`rustc`, `tsc`, `mypy --strict`), test suites, static security/supply-chain audits, and differential fuzzers.

---

## 🎯 Why ArgonLedger Passes All 4 Hackathon Judging Criteria

1. **Solves Specific Open-Source Problems for Named Engineering Personas**:
   - **Proving Ground 1 (`linux_git_c_hardening`) — Linux Kernel & Git Core C Subsystem Hardening**:
     - *Persona*: Linux Kernel & Git Core Subsystem Maintainer.
     - *Open Problem*: Purging fake `get_cycles()` counters ([Linux Kernel cleanup tracker](https://gist.github.com/andy-shev/a2cb1ee4767d6d2f5d20db53ecb9aabc)), removing global mutable repository state (`the_repo_hash_ctx`) for reentrant SHA-1 (20B) + SHA-256 (32B) cryptographic agility ([Git Hash Function Transition](https://git-scm.com/docs/hash-function-transition)), zeroing kernel-to-userspace struct alignment padding leaks (`memset`), replacing unbounded `strcpy()`/`sprintf()` with bounded `kobj_strscpy()`, and enforcing checked multiplication/addition before buffer allocation.
   - **Proving Ground 2 (`c_to_rust_framecodec`) — `Rust-for-Linux` & Ladybird Style C-to-Safe-Rust Port**:
     - *Persona*: Principal Systems Security Engineer (`Rust-for-Linux` / Ladybird Browser migration).
     - *Open Problem*: Translating C pointer lifetimes (`*const u8`, `*mut u8`, manual `realloc`/`free` in `libframecodec`) into 100% safe, idiomatic Rust (`0 unsafe` blocks, `0` raw pointers, fallible `Result<T, FcError>` returns instead of panics) verified by an **80-vector Live C-vs-Rust Differential Fuzzer**.
   - **Proving Ground 3 (`superset_ts6`) — Apache Superset Monorepo TypeScript 6.0 Strict Upgrade**:
     - *Persona*: Staff Frontend Architect @ Apache Superset ([apache/superset#39539](https://github.com/apache/superset/issues/39539)).
     - *Open Problem*: Enabling `strict: true`, `exactOptionalPropertyTypes: true`, `noUncheckedIndexedAccess: true`, and `verbatimModuleSyntax: true` across `@superset-ui/core`, `@superset-ui/chart-controls`, and `src/` with zero `any`/`@ts-ignore` escapes.
   - **Proving Ground 4 (`py_v1_to_v2`) — Ray & Python Ecosystem Pydantic v1 $\rightarrow$ v2 + Strict Mypy Upgrade**:
     - *Persona*: Lead Platform Engineer ([ray-project/ray#58876](https://github.com/ray-project/ray/issues/58876)).
     - *Open Problem*: Eliminating deprecated Pydantic v1 validators (`@validator`, `@root_validator`, `class Config`, `.dict()`, `.parse_obj()`) across coupled service modules while passing `mypy --strict` and `pytest -W error`.
   - **Option 2 (`Custom Open-Source Repo Importer`)**:
     - Point ArgonLedger at **any local open-source directory** + mutable files + custom toolchain verification command (`clang`, `cargo test`, `pytest`, `tsc`) right from the web dashboard.

2. **Work That Uniquely Requires `gemini-4-argon`**:
   - **Unified 1M-Token Context Window**: Holds all mutable source files, read-only C/Rust/TS/Python headers & test contracts, compiler diagnostics, and the **Global Interface Ledger** simultaneously.
   - **Multi-Tier `thinking_level` (`low` | `medium` | `high`) & Observable Thought Signatures**:
     - `"low"` for fast targeted extraction of the Global Interface Ledger (Phase 1) and parallel File-by-File Baseline runs.
     - `"medium"` (default) for fast, high-accuracy Whole-Repository Coordinated Synthesis (Phase 3) in under 60 seconds.
     - `"high"` for deep multi-file debugging and autonomous compiler/fuzzer repair turns (Phase 4) or upfront security architecture design.
   - **Server-Side State (`previous_interaction_id`) & Implicit Caching**: Chains Phase 1 $\rightarrow$ Phase 3 $\rightarrow$ Phase 4 via `previous_interaction_id`, retaining thought signatures and workspace context with a 95% implicit cache discount.
   - **Long Decode (`background=True`)**: Supports generating $>65,536$ output tokens asynchronously via background polling on the Interactions API.

3. **Keeps Humans (Maintainers) in Control (2 Explicit Safety Gates + Supply-Chain Audit)**:
   - **Gate 1 — Global Interface Ledger Lock**: Maintainers inspect, customize, and explicitly **Approve & Lock** cross-file signatures, lifetime invariants, and safety policies before synthesis is unlocked.
   - **Gate 2 — Supply-Chain Audit & Verified Sandbox Commit Gate**: Static scanners verify zero unauthorized process/network/backdoor primitives (`system`, `popen`, `execve`, `dlopen`) and zero safety escapes (`unsafe`, `any`, `# type: ignore`) before the human commits verified outputs to `verified_outputs/<benchmark_id>/`.

4. **Runs Live During Judging in Under 3 Minutes**:
   - Every proving ground executes live with real `gemini-4-argon` calls and real compiler/fuzzer verification in **~45–75 seconds**, including a live side-by-side comparison against a **File-by-File Baseline**.

---

## 🚀 Quickstart

### 1. Start the Live Web Benchmark Dashboard
```bash
./venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

### 2. Run the Live CLI Benchmark Suite
```bash
# Run any individual proving ground end-to-end:
./venv/bin/python -u cli_benchmark.py linux_git_c_hardening
./venv/bin/python -u cli_benchmark.py c_to_rust_framecodec
./venv/bin/python -u cli_benchmark.py superset_ts6
./venv/bin/python -u cli_benchmark.py py_v1_to_v2
```
