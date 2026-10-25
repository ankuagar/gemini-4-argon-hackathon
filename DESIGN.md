# ArgonLedger — UI/UX & Visual Design System (`DESIGN.md`)

> Created following **Hackathon Pattern #3**: *Extract typography, color palette, and layout rules into a `DESIGN.md` file first to ensure visual consistency across the application.*

## 1. Aesthetic Direction & Polarity
- **Theme Polarity**: **High-Craft Daylight / Light Mode** (inspired by Linear Light, Stripe Dashboard, and GitHub Primer Light).
- **Design Goal**: Make complex, million-token multi-file software engineering feel **approachable, transparent, and effortless to navigate** for a first-time user or hackathon judge in under 3 minutes.

---

## 2. Color Palette & Atmospheric Tokens

### Surface Hierarchy
| Role | Token | Hex | Usage |
| :--- | :--- | :--- | :--- |
| **Primary App Canvas** | `--bg-canvas` | `#F8FAFC` | Warm alabaster/slate-50 background with subtle radial daylight gradients |
| **Elevated Card Surface** | `--bg-surface` | `#FFFFFF` | Pure crisp white cards for Proving Grounds, Wizard, and Scoreboards |
| **Subtle Inset / Code Well** | `--bg-subtle` | `#F1F5F9` | Light cool-gray wells for file trees, metric boxes, and pill containers |
| **Glass Sticky Header** | `--bg-header` | `rgba(255, 255, 255, 0.88)` | Frosted white header with `backdrop-filter: blur(12px)` |

### Text & Typography Hierarchy
| Role | Token | Hex | Contrast & Usage |
| :--- | :--- | :--- | :--- |
| **Primary Ink** | `--text-primary` | `#0F172A` | Deep slate-900 for headings, metric numbers, and active code |
| **Secondary Body** | `--text-secondary` | `#334155` | Slate-700 for descriptions, contract details, and explanations |
| **Muted / Metadata** | `--text-muted` | `#64748B` | Slate-500 for timestamps, file paths, token counts, and labels |

### Semantic & Orchestration Accents
| Role | Accent Hex | Soft Tint Bg | Border Hex | Meaning in ArgonLedger |
| :--- | :--- | :--- | :--- | :--- |
| **Argon Lead Architect (`gemini-4-argon`)** | `#4F46E5` (Indigo 600) | `#EEF2FF` | `#C7D2FE` | Whole-repo synthesis, 1M context window, cross-file contract extraction |
| **Flash Subagents (`gemini-3.8-flash`)** | `#0284C7` (Sky 600) | `#F0F9FF` | `#BAE6FD` | Parallel leaf-module static scanners & edge-case spotters |
| **Human Maintainer Gate (Step 2)** | `#D97706` (Amber 600) | `#FFFBEB` | `#FDE68A` | Interactive review & approval before autonomous code execution |
| **Verified Pass / Zero Regressions** | `#059669` (Emerald 600) | `#ECFDF5` | `#A7F3D0` | 100% compiler, test suite, and C-vs-Rust differential fuzzer pass |
| **Baseline Drift / Compile Error** | `#E11D48` (Rose 600) | `#FFF1F2` | `#FECDD3` | Broken cross-file imports, unsafe escapes, or test failures |

---

## 3. Typography & Scannable Hierarchy
- **UI & Editorial Sans**: `'Inter', -apple-system, BlinkMacSystemFont, sans-serif`
  - **Step & Section Titles**: `18px–22px`, `font-weight: 700`, tight tracking (`-0.02em`).
  - **Card Titles**: `14px`, `font-weight: 700`, `#0F172A`.
  - **Readable Body Copy**: `13px–14px`, `line-height: 1.55`, `#334155`.
- **Code, Contracts & Telemetry Mono**: `'JetBrains Mono', monospace`
  - Used for all file paths, function signatures, compiler output, SHA digests, token counters, and side-by-side diffs.
  - All numeric scoreboard cells enforce `font-variant-numeric: tabular-nums` so elapsed timers and token counts align cleanly.

---

## 4. Layout Architecture & First-Time User Ergonomics
1. **Top Navigation Bar**:
   - Displays live engine status, model orchestration pills (`gemini-4-argon` Lead + `gemini-3.8-flash` Subagents), and quick-access buttons for the **Interactive Architecture & 5 Patterns Walkthrough** and **Open-Source Crisis Catalog**.
2. **4-Card Proving Ground Selector**:
   - Clicking any card immediately runs the initial repository audit (~1s) with visual pass/fail badges.
3. **3-Step Guided Wizard Banner (Single Primary CTA)**:
   - Eliminates button clutter by spotlighting the exact current step (`Step 1: Analyze & Align Intent` $\rightarrow$ `Step 2: Maintainer Gate Approval` $\rightarrow$ `Step 3: Verified Complete & Commit`) with **one primary action button** and a live elapsed timer banner when active.
4. **3-Column Executive Verdict Scoreboard**:
   - Always visible side-by-side comparison of **Initial Broken Repo** vs. **Myopic File-by-File Baseline (`FAILED`)** vs. **Argon Whole-Repo Synthesis (`PASSED 100%`)**.
5. **4-Tab Deep Inspection Workspace**:
   - **① Cross-File Interface Ledger & Flash Subagents**
   - **② Side-by-Side Code Diffs** (with light pastel emerald/rose diff highlighting)
   - **③ Real Compiler, Test & Fuzzer Logs**
   - **④ Interactive Architecture, `AGENTS.md` Quirks & `DESIGN.md`**
