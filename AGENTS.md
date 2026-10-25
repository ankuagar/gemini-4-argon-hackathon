# ArgonLedger — Engineering Quirks & Multi-Agent Playbook (`AGENTS.md`)

> Created following **Hackathon Pattern #5**: *Capture codebase quirks, Interactions API optimizations, and verification lessons learned so the team and autonomous agents never hit the same snag twice.*

---

## 1. Gemini 4 Argon (`gemini-4-argon`) Interactions API Quirks & Optimizations

### Quirk 1.1: `previous_interaction_id` Implicit Context Caching (2.8x Speedup)
- **Snag**: Re-sending the full repository bundle (`repo_bundle`) on Phase 3 (whole-repo synthesis) and Turn 2+ (autonomous compiler repair turns) when `previous_interaction_id` is already passed doubles token ingestion and increases latency from ~45s to >150s.
- **Lesson Learned**: The `client.interactions.create(model="gemini-4-argon", previous_interaction_id=...)` endpoint maintains full server-side state across turns (`input` + `thinking` + `output` in the unified 1M-token context window).
- **Rule**: Send `repo_bundle` **once** during Step 1 (`generate_ledger`). On Step 3 (`run_argon_migration`), pass `previous_interaction_id=session.ledger_interaction_id` and omit the duplicate source files. On Turn 2+ repair iterations, use `thinking_level="low"` and ask Argon to emit **only the specific file(s)** that failed compiler/test checks.

### Quirk 1.2: Long Decode (`background=True`) vs. Synchronous Calls
- **Snag**: The Interactions API enforces a `65,536` (64K) output token limit on synchronous calls. Setting `max_output_tokens > 65536` without `background=True` fails or truncates deep thinking.
- **Rule**: Whenever `max_output_tokens > 65536` (up to the 1M shared window), pass `background=True` and poll `client.interactions.get(id=interaction.id)` until `interaction.status not in ("in_progress", "queued")`.

### Quirk 1.3: Lead Architect (`gemini-4-argon`) + Parallel Subagents (`gemini-3.8-flash`)
- **Pattern**: Use `gemini-4-argon` (`thinking_level="medium"` or `"high"`) as the Lead Architect to build the **Cross-File Interface Contract Ledger** and synthesize synchronized multi-file changes, while running parallel `gemini-3.8-flash` subagents via `ThreadPoolExecutor` to scan individual leaf modules for security hazards, deprecated APIs, and boundary edge cases concurrently with zero added wall-clock latency.

### Quirk 1.4: Track 2 Multimodal Video Critique (`video/mp4`) + Stateful 3D Code Fix Loop
- **Pattern**: `client.interactions.create(model="gemini-4-argon", input=[{"type": "video", "data": b64_mp4, "mime_type": "video/mp4"}, {"type": "text", "text": prompt}])` natively watches recorded H.264 `.mp4` WebGL flythrough videos and emits timestamped (`MM:SS`) visual, lighting/shader, and camera motion critiques.
- **Rule**: Chain the 3D scene upgrade turn onto the video critique turn via `previous_interaction_id=critique_interaction_id` so `gemini-4-argon` retains both the video understanding context and its own timestamped fix directives without re-uploading the `.mp4` video.

---

## 2. Proving Ground Verification & Build Quirks

### Quirk 2.1: Linux Kernel & Git C Subsystem (`linux_git_c_hardening`)
- **Stack Alignment Padding Leak (`0xAA` Poisoning)**:
  - **Snag**: On 64-bit ABI targets (`arm64` / `x86_64`), `struct kobj_uapi_stat` has 4 bytes of implicit compiler padding between `uint32_t flags` and `uint64_t inode_nr`. Initializing fields individually (`out.version = ...; out.flags = ...`) leaves prior stack bytes (`0xAA`) inside the padding, leaking kernel stack memory when copied via `memcpy(user_buf, &out, sizeof(out))`.
  - **Rule**: Always `memset(&out, 0, sizeof(out))` before populating any struct copied across the kernel-to-userspace boundary.
- **Git SHA-1 (20B) $\rightarrow$ SHA-256 (32B) Global State Race**:
  - **Snag**: Legacy Git helpers that mutate a file-scoped `static hash_ctx_t the_repo_hash_ctx` corrupt digests across threads and hardcode 20-byte SHA-1 assumptions.
  - **Rule**: Pass `const struct git_hash_algo *algo` explicitly into every object/packfile function and size buffers with `GIT_MAX_RAWSZ` (32 bytes) + `GIT_MAX_HEXSZ` (64 hex chars + NUL).

### Quirk 2.2: C-to-Safe-Rust Port (`c_to_rust_framecodec`)
- **Differential Fuzzer `#[no_mangle] pub extern "C"` Harness Trap**:
  - **Snag**: We want 100% safe Rust (`#![forbid(unsafe_code)]` / zero `unsafe` blocks) in the library crate (`src/lib.rs`, `src/varint.rs`, `src/crc16.rs`, `src/header.rs`, `src/frame.rs`, `src/session.rs`), while still allowing the external C-vs-Rust differential fuzzer (`fuzz_harness.py`) to compare C and Rust on 80+ randomized/adversarial frames.
  - **Rule**: Keep `src/*.rs` strictly 100% safe Rust (0 `unsafe` tokens, 0 `*const`/`*mut` raw pointers) and run the differential fuzzer via a separate `cargo test` harness binary (`tests/diff_vectors.rs`) that invokes the public safe Rust API against the compiled `libframecodec.dylib` C reference oracle.

### Quirk 2.3: Apache Superset TypeScript 6.0 Strict (`superset_ts6`)
- **`verbatimModuleSyntax` + `exactOptionalPropertyTypes` Interaction**:
  - **Snag**: Under TypeScript 6.0 strict mode, re-exporting interfaces with `export { ChartQueryPayload }` triggers `TS1205` unless `export type { ... }` is used, and passing `{ vizType: string | undefined }` to an optional property `vizType?: string` fails under `exactOptionalPropertyTypes: true` unless `| undefined` is explicitly included in the type signature or omitted when `undefined`.

### Quirk 2.4: Ray / Pydantic v2 Strict (`py_v1_to_v2`)
- **Validator Execution Order & `ConfigDict(extra="forbid")`**:
  - **Snag**: Replacing `@root_validator(pre=True)` with `@model_validator(mode="before")` requires `@classmethod` in Pydantic v2, whereas `@model_validator(mode="after")` receives `self` (the validated model instance) rather than `cls, values`.

### Quirk 2.5: Track 2 WebGL Canvas Capture & Three.js `r128` Compatibility (`world_loop.py`)
- **Black Frame Buffer Without `preserveDrawingBuffer: true`**:
  - **Snag**: Calling `canvas.toDataURL('image/jpeg', 0.82)` asynchronously from a `postMessage` capture timer returns blank black frames if the WebGL drawing buffer was swapped and cleared after `renderer.render(scene, camera)`.
  - **Rule**: Always initialize `new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })` and enforce `scale=trunc(iw/2)*2:trunc(ih/2)*2 -c:v libx264 -pix_fmt yuv420p` in `ffmpeg` so odd-pixel iframe dimensions never fail H.264 encoding. Also avoid `THREE.CapsuleGeometry` when targeting Three.js `r128` (use `CylinderGeometry` / `SphereGeometry` / `ConeGeometry` / `TorusGeometry` / `DodecahedronGeometry`).

### Quirk 2.6: Smartphone HEVC (`hvc1`) + `mett` Telemetry Stream + Display Matrix Rotation in Real-to-Sim Video Ingestion
- **Snag**: Field videos captured on modern smartphones (e.g., Pixel 8 1080p30 HEVC `hvc1`, 20MB–72MB) contain a 3rd `codec_name=unknown` (`mett`) metadata stream, a `-90°` display matrix rotation tag, and exceed the `<20MB` inline payload budget for fast multimodal `video/mp4` turns.
- **Rule**: Normalize field videos via `ffmpeg -map "0:v:0" -map "0:a:0?" -vf "scale='if(gt(iw,ih),min(720,iw),-2)':'if(gt(iw,ih),-2,min(720,ih))',fps=12" -c:v libx264 -preset fast -crf 27 -pix_fmt yuv420p -movflags +faststart`. This strips the unsupported `mett` stream, bakes in upright orientation, ensures universal browser `<video>` playback, and compresses 30s clips into `<4MB` for instant inline `gemini-4-argon` multimodal perception.
