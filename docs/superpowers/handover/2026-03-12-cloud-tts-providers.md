# Cloud TTS Provider Implementation — Handover

**Project:** `hyprwhspr` — Linux speech assistant (Python, GTK4, systemd)
**Working directory:** `/home/nomadx/projects/hyprwhspr`
**Branch:** `feat/pocket-tts`

---

## What Has Been Done

Two documents are fully written, reviewed, and committed:

1. **Design spec:** `docs/superpowers/specs/2026-03-12-cloud-tts-providers-design.md`
2. **Implementation plan:** `docs/superpowers/plans/2026-03-12-cloud-tts-providers.md`

The plan has been through multiple review cycles. All reviewer-identified issues are fixed. **The plan is the source of truth — do not use the spec as a fallback.** One known spec/plan discrepancy: the spec says `store_credential` but the correct function name is `save_credential` (noted explicitly in Task 6 of the plan).

---

## What the Plan Builds

Five cloud TTS providers (ElevenLabs, OpenAI, Groq, Deepgram, Lemonfox) added alongside the existing local pocket-tts backend.

| File | Action |
|------|--------|
| `lib/src/tts_provider_registry.py` | **Create** — provider registry mirroring `provider_registry.py` |
| `lib/src/config_manager.py` | **Modify** — 3 new config keys |
| `share/config.schema.json` | **Modify** — 3 new schema entries |
| `lib/src/tts_manager.py` | **Modify** — `speak()` dispatch + cloud methods |
| `lib/src/cli_commands.py` | **Modify** — `speak_command` fixes + setup wizard extension |
| `lib/cli.py` | **Modify** — `--provider` and `--model` flags on `speak` subparser |
| `lib/src/backend_installer.py` | **Modify** — `setup_cloud_tts_provider()` function |
| `docs/CONFIGURATION.md` | **Modify** — cloud TTS docs section |

---

## Execution Instructions

Use the **`superpowers:subagent-driven-development`** skill. Execute tasks sequentially (not in parallel — tasks have dependencies). **Read the plan file once at the start, extract all 8 tasks, then work task by task.**

**Recommended model per task:**

| Tasks | Model | Reason |
|-------|-------|--------|
| 1–3 (registry, config, TTSManager) | standard | Multi-file, integration concerns |
| 4–6 (CLI fixes, backend installer) | fast | Mechanical, well-specified |
| 7 (setup wizard) | standard | Complex interactive flow |
| 8 (docs) | fast | Additive only |

---

## Critical Caveats (Verified Against Source)

These were discovered during plan review. The plan already incorporates all fixes, but read these before starting to avoid surprises.

### 1. `synthesize_and_play_streaming` signature

The existing method takes `on_playback_started: Optional[Callable[[], None]]` — a zero-arg callback. The new `speak()` method uses `progress_callback(state, progress)` — a two-arg callback. Task 3 maps them correctly with a lambda. Task 4's replacement call must also map them. Both are in the plan.

### 2. `TTSManager.__init__` placement for new lines

The 4 new `__init__` lines must be placed **after the entire `if self.config_manager: / else:` block** — not inside it. If placed inside the `if` branch (which is where the `self.volume` clamp lives), `TTSManager(config_manager=None)` will raise `AttributeError`. The plan states this explicitly.

### 3. `_audio_manager` must be initialized explicitly

`TTSManager.__init__` currently has no `self._audio_manager`. Task 3 adds `self._audio_manager = AudioManager()` as one of the 4 new init lines. This is needed by `_request_and_play()`.

### 4. Override placement in `speak_command`

The `--provider` / `--model` overrides (Task 5) must be inserted **before** the `is_available()` check at line ~3000, not just after TTSManager construction. If placed after `is_available()`, a user with no pocket-tts running `hyprwhspr speak --provider openai` will get a false "not available" error.

### 5. `IntPrompt` import

Not currently in `cli_commands.py`. Task 7 includes an explicit instruction to patch the module-level `from rich.prompt import Prompt, Confirm` → `from rich.prompt import Prompt, Confirm, IntPrompt` at line ~16. There are two `from rich.prompt import` lines in the file — patch line ~16, not the other one.

### 6. No test suite

The maintainer removed tests (commit `524d620`). All verification steps in the plan are manual shell commands. Run them.

### 7. Pre-commit hook rejects AI attribution

The hook rejects commits containing references to AI tools. Do not add `Co-Authored-By: Claude` or similar to commit messages.

---

## Before Starting

```bash
cd /home/nomadx/projects/hyprwhspr
git status          # should be on feat/pocket-tts, clean
git log --oneline -5  # verify plan commit is there (ebfacba)
```

Then read the plan:

```
docs/superpowers/plans/2026-03-12-cloud-tts-providers.md
```

The plan is self-contained with exact code, exact file paths, and runnable verification commands after each task. Follow it literally. When the plan and spec conflict, follow the plan.
