# ArgonLedger — Million Token Engineering & More Dimensions (3D Virtual Worlds from Real Videos)

**Powered by Google Gemini 4 Argon (`gemini-4-argon`) & Gemini 3.8 Flash (`gemini-3.8-flash`) via the Interactions API**

---

## 💡 What ArgonLedger Does

**ArgonLedger** is a full-stack AI engineering workbench built on `gemini-4-argon` that solves two closed-loop verification challenges where a single-pass LLM output is never enough:

### 1. Million Token Engineering — Whole-Repo Codebase Migration & Verification Engine
Open-source maintainers cannot merge AI-generated pull requests that only edit one file at a time or break cross-module contracts, type systems, or memory-safety invariants. **Million Token Engineering** ingests an entire multi-file repository into `gemini-4-argon`'s unified **1M-token context window** and executes a **4-step human-gated verification pipeline**:
- **Step 1 — Global Interface Contract Ledger (`gemini-4-argon` Lead Architect + Parallel `gemini-3.8-flash` Recon Subagents)**:
  Scans every mutable and read-only file in parallel using `gemini-3.8-flash` subagents while `gemini-4-argon` builds a single **Cross-File Interface Contract Ledger** (exact function signatures, struct layouts, error types, and safety invariants across all modules).
- **Step 2 — Maintainer Gate 1 (Inspect, Edit & Lock Contract)**:
  The human maintainer reviews the cross-file contract, adds custom migration rules if desired, and explicitly **Approves & Locks** the ledger before any code can be rewritten.
- **Step 3 — Coordinated Whole-Repo Synthesis & Autonomous Compiler/Fuzzer Loop**:
  Chains onto `previous_interaction_id` (reusing the cached 1M-token context for a **2.8x speedup**) to rewrite all coupled files simultaneously, then compiles and tests them inside an isolated sandbox (`clang`, `cargo test`, `tsc --strict`, `mypy --strict`, plus an **80-vector C-vs-Rust Differential Fuzzer**). If a compiler or test check fails, `gemini-4-argon` autonomously inspects the diagnostics and repairs the broken file in a loop. You can also run a **File-by-File Baseline** side-by-side to see why isolated single-file prompting fails on cross-file contracts.
- **Step 4 — Maintainer Gate 2 (Static Supply-Chain Audit & Commit)**:
  Verifies zero unauthorized process/network/backdoor calls and zero safety escapes (`unsafe`, `any`, `# type: ignore`) before writing the verified files and a cryptographic `verification_manifest.json` receipt to `verified_outputs/<benchmark_id>/`.

### 2. More Dimensions — Create Virtual Worlds & Robotics Twins from Real Videos (`Render → Watch → Critique → Fix`)
Generating a 3D game or robotics simulation in a single pass produces a rough first draft (flat unlit shaders, missing terrain obstacles, rigid sliding motion). **More Dimensions** turns **real-world field videos** (black bears on a forest trail, cascading waterfalls, New Zealand sheep flocks, forest deer, Kenai Fjords calving glaciers) or **text prompts** into verified **60FPS Three.js 3D Digital Twins** and **exportable robotics/game training artifacts**:
- **Real-to-Sim Video Ingestion**:
  Watches real field footage (`.mp4` / `.mov`) inline via `gemini-4-argon` (`video/mp4`) to extract physical biome parameters: ground surface friction ($\mu$), slope grade, dynamic wildlife/flock kinematics, and LiDAR/camera occlusion hazards.
- **Closed-Loop Visual Self-Improvement (`Render → Watch → Critique → Fix`)**:
  1. **Render**: Renders the 3D Three.js WebGL scene live in the browser viewport.
  2. **Watch**: Captures live WebGL frames + scene telemetry (`mesh_count`, `light_count`, `vertex_count`) and encodes an H.264 `.mp4` flythrough clip via `ffmpeg`.
  3. **Critique**: Sends the `.mp4` video inline to `gemini-4-argon` (`video/mp4`), which emits a **Visual Fidelity Score (`0–100`)** and **timestamped (`MM:SS`) defects** across lighting/shaders, biome geometry, and motion kinematics.
  4. **Fix**: Chains onto the critique turn via `previous_interaction_id` to synthesize an upgraded 60FPS 3D scene (`Iteration #1: 24/100` $\rightarrow$ `Iteration #2: 94/100` $\rightarrow$ `Iteration #3+`), with a **📈 Closed-Loop Evolution timeline** and **⚖️ Side-by-Side Before/After 3D Split View**.
- **Interactive 3D Robotics Overlays & Exportable Artifact Pack**:
  - Toggle **🤖 3D BBoxes & Costmap** (wireframe 3D Oriented Bounding Boxes, 24m × 24m Ground Traversability Costmap Grid, and 15m wildlife safety standoff rings) and **🌦️ Weather / Sensor Domain Randomization** (`☀️ Daylight`, `🌫️ LiDAR Fog`, `🌙 Dusk / Night`, `🔥 Thermal IR`) directly inside the live 3D viewport.
  - Export ready-to-run **MuJoCo MJCF Physics Arenas (`scene_mujoco.xml`)**, **Gymnasium RL Reward Scripts (`reward_env.py`)**, **Scene Perception Specs (`scene_perception.json`)**, and **Game Engine Blueprints (`game_world_blueprint.json`)** individually or as a single `.zip` bundle.

---

## 🚀 How to Run the Application

### 1. Prerequisites & Environment Setup
1. **Python 3.10+** and **`ffmpeg`** (used by **More Dimensions** to encode captured WebGL frames into H.264 `.mp4` videos and normalize uploaded smartphone videos):
   ```bash
   # Verify ffmpeg is installed on macOS:
   ffmpeg -version
   ```
2. **Virtual Environment & Dependencies**:
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   ```
3. **Configure API Key**:
   Create a `.env` file in the repository root `/Users/user/gemini-4-argon-hackathon/.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### 2. Start the Live Web Server
```bash
./venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```
Then open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser:
- **Million Token Engineering**: Run the 4 built-in open-source proving grounds from the left sidebar or import any local repository via **➕ Custom Open-Source Repo**.
- **🌍 More Dimensions — Create Virtual Worlds from Real Videos**: Click the **🌍 More Dimensions: Create Virtual Worlds from Real Videos** button in the top navigation bar (or tab `⑤`) to select any of the 6 Real-to-Sim field video scenarios (or upload your own `.mp4`/`.mov` video) or the synthetic 3D game scenario (`🏎️ Synthwave Canyon Racer`), inspect the **📈 Closed-Loop Evolution (`Render → Watch → Critique → Fix`)** cards, toggle **⚖️ Compare Before vs. After (Split 3D View)**, and click **▶ Run Full Loop: Render → Watch → Critique → Fix**.
- **Interactive Architecture Walkthrough**: Click **🗺️ Architecture, 5 Patterns & AGENTS.md** in the top navigation bar or visit **[http://127.0.0.1:8000/architecture](http://127.0.0.1:8000/architecture)**.

### 3. Run the Million Token Engineering CLI Benchmark Suite (Optional)
```bash
./venv/bin/python -u cli_benchmark.py linux_git_c_hardening
./venv/bin/python -u cli_benchmark.py c_to_rust_framecodec
./venv/bin/python -u cli_benchmark.py superset_ts6
./venv/bin/python -u cli_benchmark.py py_v1_to_v2
```

---

## 📂 Where Media, Simulation Videos & Generated Artifacts Are Stored

All input media, recorded simulation videos, exported robotics/game artifacts, and verified codebase outputs are organized into dedicated directories inside the repository:

| Directory / Path | Purpose & Contents |
| :--- | :--- |
| **`assets/real_videos/`** | **Normalized Real-World Field Videos (`.mp4`) for More Dimensions**<br/>Stores browser- & API-ready H.264 `yuv420p` `.mp4` field videos (`bear_hike.mp4`, `bear_take1.mp4`, `waterfall_cascade.mp4`, `nz_sheep.mp4`, `forest_deer.mp4`, `kenai_glacier_calving.mp4`, `hillside_waterfall.mp4`, etc.).<br/>• When you upload a custom `.mov` or `.mp4` video via **📤 Upload Your Own Video** in the UI (`POST /api/track2/upload_video`), ArgonLedger automatically transcodes it with `ffmpeg` and stores it in `assets/real_videos/custom_<id>_<name>.mp4`. |
| **`runs/track2_worlds/<session_id>/`** | **More Dimensions — 3D Virtual Worlds, Recorded Sim Videos & Robotics Artifacts (Per Session)**<br/>Every session writes its generated 3D scenes, recorded WebGL flythrough videos, and Real-to-Sim artifacts here:<br/>• `iter_1.html`, `iter_2.html`, `iter_N.html` — Self-contained 60FPS Three.js `r128` 3D scenes for each loop iteration.<br/>• `iter_1.mp4`, `iter_2.mp4`, `iter_N.mp4` — Recorded H.264 `.mp4` WebGL flythrough videos captured from the live 3D canvas and sent inline to `gemini-4-argon` (`video/mp4`).<br/>• `scene_perception.json` — Structured biome physics spec (surface friction $\mu$, slope angle, dynamic entity kinematics, LiDAR/camera occlusion notes).<br/>• `scene_mujoco.xml` — Ready-to-run **MuJoCo MJCF** physics arena with calibrated ground geoms, obstacles, dynamic biological actors, and quadruped ego-robot.<br/>• `reward_env.py` — Executable **Gymnasium RL** reward function & curriculum training script.<br/>• `game_world_blueprint.json` — Procedural Unreal / Unity / Three.js world blueprint (heightmap recipe, foliage scatter layers, NPC AI / Boids rules).<br/>*(You can also download all of these as a single archive via the **⬇️ Download All Artifacts (`.zip`)** button in the UI or `GET /api/track2/sessions/<session_id>/artifacts.zip`.)* |
| **`verified_outputs/<benchmark_id>/`** | **Million Token Engineering — Maintainer-Approved & Compiler-Verified Codebase Outputs**<br/>When a maintainer clicks **Step 4: Commit Verified Build** after passing all compiler, test, differential fuzzer, and static supply-chain checks, the verified files are persisted to `verified_outputs/<benchmark_id>/` (alongside a `verification_manifest.json` audit receipt). |
| **`runs/<session_id>/`** | **Million Token Engineering — Isolated Verification Sandboxes**<br/>Temporary isolated workspaces (`runs/<session_id>/argon_repo/` and `runs/<session_id>/baseline_repo/`) where live compiler (`clang`, `cargo test`, `tsc`, `mypy --strict`) and differential fuzzer checks execute safely before human approval. |
| **`benchmarks/`** | **Million Token Engineering — Proving Ground Source Repositories**<br/>Contains the 4 built-in multi-file benchmark repositories (`linux_git_c_hardening`, `c_to_rust_framecodec`, `superset_ts6`, `py_v1_to_v2`). |
| **`AGENTS.md` & `static/architecture.html`** | **Engineering Playbook & Visual Architecture Explainer**<br/>`AGENTS.md` documents all Gemini 4 Argon Interactions API optimizations (`previous_interaction_id` caching, `background=True` long decode, multimodal `video/mp4` loops, and `ffmpeg` smartphone HEVC normalization). `static/architecture.html` provides the interactive visual system walkthrough. |

---

## 🌍 More Dimensions: Create Virtual Worlds from Real Videos

1. **Multi-Iteration Progression (`Render → Watch → Critique → Fix`)**:
   - Every scenario tracks its full visual evolution in the **📈 Closed-Loop Evolution** panel (`Iteration #1 Initial Single-Pass Draft (24/100)` $\xrightarrow{\text{Watched & Critiqued}}$ `Iteration #2 Upgraded 3D World (94/100, +70 pts)` $\xrightarrow{}$ `Live Iteration #3+`).
   - Click **⚖️ Compare Before vs. After (Split 3D View)** to run **Iteration #1 (Before)** and **Iteration #2+ (After)** side-by-side in two synchronized live 60FPS Three.js WebGL viewports.
2. **Interactive 3D Viewport Overlays**:
   - **🤖 3D BBoxes & Costmap (`OFF` / `ON`)**: Toggles wireframe 3D Oriented Bounding Boxes (OBBs), a 24m × 24m Ground Traversability Costmap Grid, and 15m wildlife safety standoff rings directly inside the live 3D scene.
   - **🌦️ Weather / Sensor (`☀️ Daylight` → `🌫️ LiDAR Fog` → `🌙 Dusk / Night` → `🔥 Thermal IR`)**: Cycles Sim-to-Real domain randomization lighting and FLIR thermal false-color shader modes across the 3D scene.

---

## 🏗️ Million Token Engineering: Whole-Repository Migration & Verification

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
   - **Custom Open-Source Repo Importer**:
     - Point ArgonLedger at **any local open-source directory** + mutable files + custom toolchain verification command (`clang`, `cargo test`, `pytest`, `tsc`) right from the web dashboard.

2. **Work That Uniquely Requires `gemini-4-argon`**:
   - **Unified 1M-Token Context Window**: Holds all mutable source files, read-only C/Rust/TS/Python headers & test contracts, compiler diagnostics, and the **Global Interface Ledger** simultaneously.
   - **Lead Architect (`gemini-4-argon`) + Parallel Subagents (`gemini-3.8-flash`)**: Runs parallel `gemini-3.8-flash` module reconnaissance subagents while `gemini-4-argon` synthesizes the Global Interface Contract Ledger.
   - **Server-Side State (`previous_interaction_id`) & Implicit Caching**: Chains Phase 1 $\rightarrow$ Phase 3 $\rightarrow$ Phase 4 (and Video Critique $\rightarrow$ 3D Scene Synthesis) via `previous_interaction_id`, retaining thought signatures and workspace context with a 2.8x speedup.
   - **Long Decode (`background=True`)**: Supports generating $>65,536$ output tokens asynchronously via background polling on the Interactions API.

3. **Keeps Humans (Maintainers) in Control (2 Explicit Safety Gates + Supply-Chain Audit)**:
   - **Gate 1 — Global Interface Ledger Lock**: Maintainers inspect, customize, and explicitly **Approve & Lock** cross-file signatures, lifetime invariants, and safety policies before synthesis is unlocked.
   - **Gate 2 — Supply-Chain Audit & Verified Sandbox Commit Gate**: Static scanners verify zero unauthorized process/network/backdoor primitives (`system`, `popen`, `execve`, `dlopen`) and zero safety escapes (`unsafe`, `any`, `# type: ignore`) before the human commits verified outputs to `verified_outputs/<benchmark_id>/`.

