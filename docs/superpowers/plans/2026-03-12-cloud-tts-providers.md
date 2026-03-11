# Cloud TTS Providers Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend hyprwhspr's TTS system to support ElevenLabs, OpenAI, Groq, Deepgram, and Lemonfox as cloud backends alongside the existing pocket-tts local backend.

**Architecture:** New `tts_provider_registry.py` mirrors the existing `provider_registry.py` pattern. `TTSManager` gains a `speak()` dispatch method that routes to the existing `synthesize_and_play_streaming()` (pocket-tts) or a new `_speak_cloud()` path. Streaming providers (OpenAI, Groq, ElevenLabs) pipe chunked HTTP audio to `ffplay` stdin; non-streaming (Deepgram, Lemonfox) use POST → temp file → `AudioManager.play_file()`. API keys are stored via the existing `credential_manager` and shared with STT keys where providers overlap.

**Tech Stack:** Python 3, `requests` (already in requirements.txt), `ffplay` (already first choice in `AudioManager`), `rich` (already used for wizard prompts), existing `credential_manager`, `config_manager`, `provider_registry` patterns.

**Branch note:** Work on `feat/pocket-tts`. When PR #129 merges upstream, rebase onto a new `feat/cloud-tts` branch off the updated main before submitting.

**No test suite:** The maintainer explicitly removed tests (commit `524d620`). Use manual verification steps instead.

**Spec:** `docs/superpowers/specs/2026-03-12-cloud-tts-providers-design.md`

---

## Chunk 1: Foundation — Registry + Config

### Task 1: Create `tts_provider_registry.py`

**Files:**
- Create: `lib/src/tts_provider_registry.py`

- [ ] **Create the registry file**

```python
# lib/src/tts_provider_registry.py
"""
Provider registry for cloud TTS backends.
Mirrors provider_registry.py — one entry per provider with all request metadata.
"""

from typing import Dict, List, Optional, Tuple

TTS_PROVIDERS: Dict[str, Dict] = {
    'openai': {
        'name': 'OpenAI',
        'endpoint': 'https://api.openai.com/v1/audio/speech',
        'api_key_header': 'Authorization',
        'api_key_prefix': 'Bearer ',
        'api_key_validation_prefix': 'sk-',
        'api_key_description': 'OpenAI API key (starts with sk-)',
        'streaming': True,
        'audio_format': 'mp3',
        'request_text_field': 'input',   # OpenAI API uses 'input', not 'text'
        'voices': ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
        'default_voice': 'alloy',
        'endpoint_uses_voice_in_url': False,
        'voice_as_query_param': False,
        'models': {
            'gpt-4o-mini-tts': {
                'name': 'GPT-4o Mini TTS',
                'description': 'Lowest latency, steerable',
            },
            'tts-1': {
                'name': 'TTS-1',
                'description': 'Optimised for speed',
            },
            'tts-1-hd': {
                'name': 'TTS-1 HD',
                'description': 'Higher quality',
            },
        },
        'default_model': 'gpt-4o-mini-tts',
    },
    'groq': {
        'name': 'Groq',
        'endpoint': 'https://api.groq.com/openai/v1/audio/speech',
        'api_key_header': 'Authorization',
        'api_key_prefix': 'Bearer ',
        'api_key_validation_prefix': 'gsk_',
        'api_key_description': 'Groq API key (starts with gsk_)',
        'streaming': True,
        'audio_format': 'mp3',
        'request_text_field': 'input',   # Groq uses OpenAI-compatible format
        'voices': ['Aaliyah-PlayAI', 'Adelaide-PlayAI', 'Angelo-PlayAI', 'Briggs-PlayAI',
                   'Calum-PlayAI', 'Celeste-PlayAI', 'Cheyenne-PlayAI', 'Chip-PlayAI'],
        'default_voice': 'Aaliyah-PlayAI',
        'endpoint_uses_voice_in_url': False,
        'voice_as_query_param': False,
        'models': {
            'playai-tts': {
                'name': 'PlayAI TTS',
                'description': 'Fast, natural speech',
            },
            'playai-tts-arabic': {
                'name': 'PlayAI TTS Arabic',
                'description': 'Arabic language support',
            },
        },
        'default_model': 'playai-tts',
    },
    'elevenlabs': {
        'name': 'ElevenLabs',
        'endpoint': 'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream',
        'api_key_header': 'xi-api-key',
        'api_key_prefix': '',           # key sent directly, no Bearer/Token prefix
        'api_key_validation_prefix': None,
        'api_key_description': 'ElevenLabs API key',
        'streaming': True,
        'audio_format': 'mp3',
        'request_text_field': 'text',    # ElevenLabs body uses 'text'
        'voices': ['aria', 'sarah', 'laura', 'charlie', 'george', 'callum', 'river'],
        'default_voice': 'aria',
        'endpoint_uses_voice_in_url': True,
        'voice_as_query_param': False,
        'models': {
            'eleven_turbo_v2_5': {
                'name': 'Turbo v2.5',
                'description': 'Lowest latency (~75ms)',
            },
            'eleven_multilingual_v2': {
                'name': 'Multilingual v2',
                'description': 'Best quality, 29 languages',
            },
        },
        'default_model': 'eleven_turbo_v2_5',
    },
    'deepgram': {
        'name': 'Deepgram',
        'endpoint': 'https://api.deepgram.com/v1/speak',
        'api_key_header': 'Authorization',
        'api_key_prefix': 'Token ',
        'api_key_validation_prefix': None,
        'api_key_description': 'Deepgram API key',
        'streaming': False,
        'audio_format': 'mp3',
        'request_text_field': 'text',    # Deepgram body uses 'text'
        'voices': ['aura-2-thalia-en', 'aura-2-zeus-en', 'aura-2-luna-en',
                   'aura-2-orion-en', 'aura-2-asteria-en'],
        'default_voice': 'aura-2-thalia-en',
        'endpoint_uses_voice_in_url': False,
        'voice_as_query_param': True,   # voice sent as ?model=<voice>
        'models': {
            'aura-2': {
                'name': 'Aura 2',
                'description': 'Natural, low latency',
            },
        },
        'default_model': 'aura-2',
    },
    'lemonfox': {
        'name': 'Lemonfox',
        'endpoint': 'https://api.lemonfox.ai/v1/audio/speech',
        'api_key_header': 'Authorization',
        'api_key_prefix': 'Bearer ',
        'api_key_validation_prefix': None,
        'api_key_description': 'Lemonfox API key',
        'streaming': False,
        'audio_format': 'mp3',
        'request_text_field': 'input',   # Lemonfox uses OpenAI-compatible format
        'voices': ['sarah', 'rachel', 'domi', 'bella', 'antoni', 'elli', 'josh'],
        'default_voice': 'sarah',
        'endpoint_uses_voice_in_url': False,
        'voice_as_query_param': False,
        'models': {
            'tts-1': {
                'name': 'TTS-1',
                'description': 'OpenAI-compatible TTS',
            },
        },
        'default_model': 'tts-1',
    },
}


def get_provider(provider_id: str) -> Optional[Dict]:
    """Get provider config by ID. Returns None if unknown."""
    return TTS_PROVIDERS.get(provider_id)


def list_providers() -> List[Tuple[str, str, bool]]:
    """
    Return list of (provider_id, name, streaming) sorted streaming-first.
    Used by setup wizard to build the provider selection menu.
    """
    items = [
        (pid, p['name'], p['streaming'])
        for pid, p in TTS_PROVIDERS.items()
    ]
    return sorted(items, key=lambda x: (not x[2], x[0]))  # streaming first, then alpha


def validate_api_key(provider_id: str, api_key: str) -> Tuple[bool, Optional[str]]:
    """
    Validate API key format for provider. Returns (is_valid, error_message).
    Only checks prefix format where known; all keys pass length check.
    """
    provider = get_provider(provider_id)
    if not provider:
        return False, f"Unknown TTS provider: {provider_id}"
    if not api_key or not api_key.strip():
        return False, "API key cannot be empty"
    prefix = provider.get('api_key_validation_prefix')
    if prefix and not api_key.startswith(prefix):
        return False, f"Key should start with '{prefix}'"
    if len(api_key.strip()) < 10:
        return False, "API key appears too short"
    return True, None
```

- [ ] **Verify the registry imports cleanly**

```bash
cd /home/nomadx/projects/hyprwhspr
python3 -c "
import sys; sys.path.insert(0, 'lib/src')
from tts_provider_registry import get_provider, list_providers, validate_api_key
print('Providers:', [p[0] for p in list_providers()])
print('Streaming first:', list_providers()[0][0])
p = get_provider('elevenlabs')
print('ElevenLabs voice-in-url:', p['endpoint_uses_voice_in_url'])
ok, err = validate_api_key('openai', 'sk-abc123456789')
print('OpenAI key valid:', ok, err)
ok, err = validate_api_key('openai', 'bad')
print('Bad key valid:', ok, err)
"
```

Expected output:
```
Providers: ['elevenlabs', 'groq', 'openai', 'deepgram', 'lemonfox']
Streaming first: elevenlabs  (or openai/groq — any streaming provider)
ElevenLabs voice-in-url: True
OpenAI key valid: True None
Bad key valid: False Key should start with 'sk-'
```

- [ ] **Commit**

```bash
git add lib/src/tts_provider_registry.py
git commit -m "feat: add tts_provider_registry with 5 cloud providers"
```

---

### Task 2: Add config defaults and schema entries

**Files:**
- Modify: `lib/src/config_manager.py` (~line 114, after `tts_osd_timeout`)
- Modify: `share/config.schema.json` (after `tts_osd_timeout` block)

- [ ] **Add 3 keys to `config_manager.py` default_config**

Find the block ending with `'tts_osd_timeout': 30,` (around line 114) and add immediately after:

```python
            'tts_provider':    'pocket-tts',  # 'pocket-tts' | 'openai' | 'groq' | 'elevenlabs' | 'deepgram' | 'lemonfox'
            'tts_cloud_model': None,          # Cloud model ID; None = provider default
            'tts_cloud_voice': None,          # Cloud voice ID; None = provider default
```

- [ ] **Add 3 entries to `share/config.schema.json`**

Find the `tts_osd_timeout` block and add after its closing `}`:

```json
    "tts_provider": {
      "type": "string",
      "default": "pocket-tts",
      "description": "TTS backend: 'pocket-tts' for local or a cloud provider ID (openai, groq, elevenlabs, deepgram, lemonfox)"
    },
    "tts_cloud_model": {
      "type": ["string", "null"],
      "default": null,
      "description": "Cloud TTS model ID. null = use provider default."
    },
    "tts_cloud_voice": {
      "type": ["string", "null"],
      "default": null,
      "description": "Cloud TTS voice ID. null = use provider default."
    },
```

- [ ] **Verify config defaults are readable**

```bash
cd /home/nomadx/projects/hyprwhspr
python3 -c "
import sys; sys.path.insert(0, 'lib/src')
from config_manager import ConfigManager
c = ConfigManager()
print('tts_provider:', c.get_setting('tts_provider'))
print('tts_cloud_model:', c.get_setting('tts_cloud_model'))
print('tts_cloud_voice:', c.get_setting('tts_cloud_voice'))
"
```

Expected:
```
tts_provider: pocket-tts
tts_cloud_model: None
tts_cloud_voice: None
```

- [ ] **Commit**

```bash
git add lib/src/config_manager.py share/config.schema.json
git commit -m "feat: add tts_provider, tts_cloud_model, tts_cloud_voice config keys"
```

---

## Chunk 2: Core — TTSManager Extension

### Task 3: Extend `tts_manager.py` with provider dispatch

**Files:**
- Modify: `lib/src/tts_manager.py`

The existing `TTSManager` class has:
- `__init__` at line ~44 — reads `tts_voice`, `tts_volume` from config
- `synthesize_and_play_streaming` at line ~172 — the existing pocket-tts entry point (DO NOT RENAME)
- `is_available` at line ~303 — currently only checks `import pocket_tts`

We add: new imports, 3 constructor lines, `speak()`, `_speak_cloud()`, 3 request-building helpers, `_stream_to_player()`, `_request_and_play()`, and fix `is_available()`.

- [ ] **Add imports at top of `tts_manager.py`**

After the existing `from .audio_manager import AudioManager` import block, add:

```python
try:
    import requests as _requests
    from .tts_provider_registry import get_provider as _get_tts_provider
    from .credential_manager import get_credential as _get_credential
except ImportError:
    import requests as _requests
    from tts_provider_registry import get_provider as _get_tts_provider
    from credential_manager import get_credential as _get_credential
```

- [ ] **Add 4 lines to `__init__`**

In `TTSManager.__init__`, after the **entire** `if self.config_manager: / else:` block closes (after the `self.volume = 1.0` line in the `else` branch, at the same indentation level as the `if` statement itself). Do NOT place these inside either the `if` or `else` branch — they must be unconditional, as `config_manager` may be `None` in some call paths:

```python
        self.provider = self.config_manager.get_setting('tts_provider', 'pocket-tts') if self.config_manager else 'pocket-tts'
        self.cloud_model = self.config_manager.get_setting('tts_cloud_model', None) if self.config_manager else None
        self.cloud_voice = self.config_manager.get_setting('tts_cloud_voice', None) if self.config_manager else None
        self._audio_manager = AudioManager()  # needed by _request_and_play() for non-streaming providers
```

- [ ] **Fix `is_available()`**

Replace the existing `is_available` method (lines ~303-310) with:

```python
    def is_available(self) -> bool:
        """Check if TTS is usable: pocket-tts importable, or cloud key stored."""
        if self.provider == 'pocket-tts':
            try:
                import pocket_tts  # noqa: F401
                return True
            except ImportError:
                return False
        return bool(_get_credential(self.provider))
```

- [ ] **Add `speak()` dispatch method**

Add after `is_available()`:

```python
    def speak(self, text: str, voice: Optional[str] = None,
              progress_callback=None) -> bool:
        """
        Top-level TTS entry point. Routes to pocket-tts or cloud provider.
        Returns True on success, False on failure.
        progress_callback(state: str, progress: float) — states: fetching, playing, error.
        """
        if self.provider == 'pocket-tts':
            # synthesize_and_play_streaming takes on_playback_started: Callable[[], None]
            # Map progress_callback to that signature
            on_started = (lambda: progress_callback('playing', 0.5)) if progress_callback else None
            return self.synthesize_and_play_streaming(
                text, voice=voice, on_playback_started=on_started
            )
        return self._speak_cloud(text, progress_callback=progress_callback)
```

- [ ] **Add 3 request-building helpers**

Add after `speak()`:

```python
    def _build_tts_url(self, provider: dict, voice: Optional[str]) -> str:
        """Build request URL, substituting voice_id for ElevenLabs."""
        url = provider['endpoint']
        if provider.get('endpoint_uses_voice_in_url'):
            v = voice or provider['default_voice']
            url = url.replace('{voice_id}', v)
        return url

    def _build_tts_headers(self, provider: dict, api_key: str) -> dict:
        """Build auth headers. ElevenLabs uses xi-api-key directly; others use Authorization."""
        prefix = provider.get('api_key_prefix', '')
        return {provider['api_key_header']: f"{prefix}{api_key}"}

    def _build_tts_request(self, provider: dict, text: str,
                            voice: Optional[str], model: Optional[str]):
        """
        Build (body_dict, query_params_dict).
        Uses request_text_field from registry so no provider-specific branching here.
        Deepgram sends voice as query param; ElevenLabs puts voice in URL (handled in _build_tts_url);
        all others put voice in body.
        """
        v = voice or provider['default_voice']
        m = model or provider['default_model']
        params = {}
        text_field = provider['request_text_field']  # 'input' (OpenAI-compat) or 'text' (ElevenLabs/Deepgram)
        body: dict = {text_field: text}

        if provider.get('voice_as_query_param'):
            params['model'] = v          # Deepgram: voice name IS the model param
        elif not provider.get('endpoint_uses_voice_in_url'):
            body['voice'] = v            # OpenAI / Groq / Lemonfox: voice in body

        # Model placement: ElevenLabs uses 'model_id'; Deepgram has only one fixed model
        if provider.get('endpoint_uses_voice_in_url'):
            body['model_id'] = m         # ElevenLabs
        elif not provider.get('voice_as_query_param'):
            body['model'] = m            # OpenAI / Groq / Lemonfox

        return body, params
```

- [ ] **Add `_speak_cloud()`**

```python
    def _speak_cloud(self, text: str, progress_callback=None) -> bool:
        """Dispatch to streaming or request/response cloud TTS path."""
        provider = _get_tts_provider(self.provider)
        if not provider:
            _log_tts(f"Unknown TTS provider: {self.provider}")
            return False

        api_key = _get_credential(self.provider)
        if not api_key:
            _log_tts(f"No API key stored for {self.provider}. Run: hyprwhspr setup")
            return False

        url = self._build_tts_url(provider, self.cloud_voice)
        headers = self._build_tts_headers(provider, api_key)
        body, params = self._build_tts_request(
            provider, text, self.cloud_voice, self.cloud_model
        )

        if progress_callback:
            progress_callback('fetching', 0.0)

        try:
            if provider['streaming']:
                return self._stream_to_player(url, headers, body, params, progress_callback)
            else:
                return self._request_and_play(url, headers, body, params, progress_callback)
        except Exception as e:
            _log_tts(f"Cloud TTS failed ({self.provider}): {e}")
            if progress_callback:
                progress_callback('error', 0.0)
            # Fallback: pocket-tts if installed
            try:
                import pocket_tts  # noqa: F401
                _log_tts("Falling back to pocket-tts")
                on_started = (lambda: progress_callback('playing', 0.5)) if progress_callback else None
                return self.synthesize_and_play_streaming(text, on_playback_started=on_started)
            except ImportError:
                return False
```

- [ ] **Add `_stream_to_player()`**

```python
    def _stream_to_player(self, url: str, headers: dict, body: dict,
                           params: dict, progress_callback=None) -> bool:
        """
        Stream audio chunks from cloud provider to ffplay stdin.
        First audio plays within one buffered chunk (~200ms for fast providers).
        """
        import subprocess as _subprocess
        player = _subprocess.Popen(
            ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', '-i', 'pipe:0'],
            stdin=_subprocess.PIPE
        )
        try:
            with _requests.post(url, headers=headers, json=body,
                                 params=params, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                if progress_callback:
                    progress_callback('playing', 0.5)
                for chunk in resp.iter_content(chunk_size=4096):
                    if chunk:
                        player.stdin.write(chunk)
            player.stdin.close()
            player.wait()
            return True
        except Exception:
            try:
                player.kill()
            except Exception:
                pass
            raise
```

- [ ] **Add `_request_and_play()`**

```python
    def _request_and_play(self, url: str, headers: dict, body: dict,
                           params: dict, progress_callback=None) -> bool:
        """POST → save temp MP3 → play via AudioManager."""
        resp = _requests.post(url, headers=headers, json=body,
                               params=params, timeout=30)
        resp.raise_for_status()
        tmp = TEMP_DIR / 'tts_cloud_output.mp3'
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(resp.content)
        if progress_callback:
            progress_callback('playing', 1.0)
        if self._audio_manager:
            self._audio_manager.play_file(str(tmp))
        return True
```

- [ ] **Verify TTSManager still works for pocket-tts**

With current config still set to `pocket-tts`:

```bash
hyprwhspr speak --text "Testing pocket TTS path"
```

Expected: audio plays via pocket-tts unchanged.

- [ ] **Commit**

```bash
git add lib/src/tts_manager.py
git commit -m "feat: add cloud provider dispatch to TTSManager"
```

---

## Chunk 3: CLI Fixes and Backend Installer

### Task 4: Fix `speak_command` in `cli_commands.py`

**Files:**
- Modify: `lib/src/cli_commands.py` (around lines 2961, 3001, 3019)

Three targeted fixes — do not restructure the function.

- [ ] **Update `speak_command` to call `speak()` instead of `synthesize_and_play_streaming()`**

The current call (line ~3049) looks like:
```python
ok = tts_manager.synthesize_and_play_streaming(
    text, voice=voice, volume=volume,
    on_playback_started=on_playback_started,
)
```

Replace it with:
```python
# speak() uses self.volume from config; if args.volume was set, apply it first
if getattr(args, 'volume', None) is not None:
    tts_manager.volume = max(0.1, min(1.0, float(args.volume)))
ok = tts_manager.speak(
    text,
    voice=voice,
    progress_callback=(
        lambda state, p: on_playback_started() if state == 'playing' and on_playback_started else None
    ) if on_playback_started else None,
)
```

Note: `volume` is not a parameter of `speak()` — the pocket-tts path inside `speak()` reads `self.volume`, and cloud providers have no per-call volume. Setting `tts_manager.volume` directly before the call handles any per-invocation `--volume` override.
Note: `on_playback_started` is mapped to `progress_callback` via a lambda that fires on the `'playing'` state.

- [ ] **Fix the "not available" error message (line ~3001)**

Replace:
```python
log_error("Pocket TTS is not installed. Run: hyprwhspr setup  # and enable TTS")
```
With:
```python
provider = config.get_setting('tts_provider', 'pocket-tts')
if provider == 'pocket-tts':
    log_error("Pocket TTS is not installed. Run: hyprwhspr setup  # and enable TTS")
else:
    log_error(f"No API key found for {provider}. Run: hyprwhspr setup  # and configure TTS")
```

- [ ] **Fix voice resolution (line ~3019)**

Replace:
```python
voice = getattr(args, 'voice', None) or config.get_setting('tts_voice', 'alba')
```
With:
```python
provider = config.get_setting('tts_provider', 'pocket-tts')
if provider == 'pocket-tts':
    voice = getattr(args, 'voice', None) or config.get_setting('tts_voice', 'alba')
else:
    voice = getattr(args, 'voice', None) or config.get_setting('tts_cloud_voice', None)
```

- [ ] **Verify speak_command still works**

```bash
hyprwhspr speak --text "Voice resolution test"
```

Expected: audio plays correctly.

- [ ] **Commit**

```bash
git add lib/src/cli_commands.py
git commit -m "fix: update speak_command for cloud provider support"
```

---

### Task 5: Add `--provider` and `--model` flags to `speak` subparser

**Files:**
- Modify: `lib/cli.py` (speak subparser section)

- [ ] **Add flags to the speak subparser**

Find the speak subparser in `lib/cli.py` (search for `speak` subparser). After the existing `--voice` argument, add:

```python
speak_parser.add_argument(
    '--provider',
    metavar='PROVIDER',
    help='Override TTS provider for this invocation (e.g. openai, elevenlabs)',
    default=None,
)
speak_parser.add_argument(
    '--model',
    metavar='MODEL',
    help='Override TTS model for this invocation (e.g. tts-1, eleven_turbo_v2_5)',
    default=None,
)
```

- [ ] **Wire overrides into `speak_command`** (`cli_commands.py`)

In `speak_command`, after `TTSManager` is constructed but **before** the `is_available()` check (which is at line ~3000). The overrides must come first — otherwise `is_available()` evaluates the un-overridden provider and may wrongly return False for a `--provider` override.

Add after the `TTSManager(...)` constructor call:

```python
# Per-invocation overrides — must appear before is_available() check
if getattr(args, 'provider', None):
    tts_manager.provider = args.provider
if getattr(args, 'model', None):
    tts_manager.cloud_model = args.model
```

- [ ] **Verify help text shows new flags**

```bash
hyprwhspr speak --help
```

Expected: `--provider` and `--model` appear in the help output.

- [ ] **Commit**

```bash
git add lib/cli.py lib/src/cli_commands.py
git commit -m "feat: add --provider and --model flags to speak subcommand"
```

---

### Task 6: Add `setup_cloud_tts_provider()` to `backend_installer.py`

**Files:**
- Modify: `lib/src/backend_installer.py`

- [ ] **Add function near the end of the file, before the `if __name__` block if present**

> **Note:** The design spec says `store_credential` — that function does not exist. The correct function name is `save_credential`. Use the code below, not the spec.

```python
def setup_cloud_tts_provider(
    provider_id: str,
    api_key: str,
    model: Optional[str] = None,
    voice: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Configure a cloud TTS provider.
    No pip install — stores credentials and writes config.
    Returns (success, message).
    """
    try:
        from .tts_provider_registry import get_provider as _get_tts_provider
        from .credential_manager import save_credential
        from .config_manager import ConfigManager
    except ImportError:
        from tts_provider_registry import get_provider as _get_tts_provider
        from credential_manager import save_credential
        from config_manager import ConfigManager

    try:
        provider = _get_tts_provider(provider_id)
        if not provider:
            return False, f"Unknown TTS provider: {provider_id}"

        if not save_credential(provider_id, api_key):
            return False, f"Failed to store API key for {provider_id}"

        config = ConfigManager()
        config.set_setting('tts_provider', provider_id)
        config.set_setting('tts_cloud_model', model or provider['default_model'])
        config.set_setting('tts_cloud_voice', voice or provider['default_voice'])
        config.set_setting('tts_enabled', True)
        config.save_config()
        return True, f"{provider['name']} TTS configured"
    except Exception as e:
        return False, str(e)
```

- [ ] **Verify the function is importable**

```bash
cd /home/nomadx/projects/hyprwhspr
python3 -c "
import sys; sys.path.insert(0, 'lib/src')
from backend_installer import setup_cloud_tts_provider
print('setup_cloud_tts_provider imported OK')
"
```

- [ ] **Commit**

```bash
git add lib/src/backend_installer.py
git commit -m "feat: add setup_cloud_tts_provider() to backend_installer"
```

---

## Chunk 4: Setup Wizard

### Task 7: Extend the interactive setup wizard for cloud TTS

**Files:**
- Modify: `lib/src/cli_commands.py` (two sections)

**Section A — Interactive wizard (~line 1570):** Extends the TTS wizard step.
**Section B — Auto-setup (~line 2183):** Branches install vs cloud config.

- [ ] **Replace the TTS wizard block (interactive)**

The current block (lines ~1570–1577) asks only "Enable TTS?" then picks a pocket-tts voice.
Replace it with the expanded flow:

```python
    # ── TTS ──────────────────────────────────────────────────────────────
    print()
    print("[bold]Text-to-Speech (TTS)[/bold]")
    setup_tts_choice = Confirm.ask("Enable text-to-speech?", default=False)

    tts_backend = 'pocket-tts'
    tts_voice = 'alba'
    tts_provider_id = None
    tts_provider_model = None
    tts_provider_voice = None

    if setup_tts_choice:
        from .tts_provider_registry import list_providers as _list_tts_providers, get_provider as _get_tts_provider
        from .credential_manager import get_credential as _get_credential, save_credential

        backend_choice = Prompt.ask(
            "TTS backend",
            choices=["local", "cloud"],
            default="local",
        )

        if backend_choice == "cloud":
            tts_backend = 'cloud'
            providers = _list_tts_providers()  # streaming-first sorted list
            print("\nAvailable cloud TTS providers:")
            for i, (pid, pname, streaming) in enumerate(providers, 1):
                latency = "(streaming, ~75–200ms)" if streaming else "(non-streaming)"
                print(f"  {i}. {pname} {latency}")

            idx = IntPrompt.ask(
                "Select provider",
                default=1,
            )
            idx = max(1, min(len(providers), idx))
            tts_provider_id, _, _ = providers[idx - 1]
            provider_cfg = _get_tts_provider(tts_provider_id)

            # Offer to reuse existing key if already set up for STT
            existing_key = _get_credential(tts_provider_id)
            if existing_key:
                masked = existing_key[:6] + '...' + existing_key[-4:]
                reuse = Confirm.ask(
                    f"Found existing {provider_cfg['name']} key ({masked}) from STT setup. Use it?",
                    default=True,
                )
                if not reuse:
                    existing_key = None

            if not existing_key:
                from .tts_provider_registry import validate_api_key as _validate_tts_key
                while True:
                    key = Prompt.ask(f"Enter {provider_cfg['name']} API key")
                    ok, err = _validate_tts_key(tts_provider_id, key)
                    if ok:
                        save_credential(tts_provider_id, key)
                        break
                    print(f"[red]Invalid key: {err}[/red]")

            # Model selection (skip if provider only has one)
            models = list(provider_cfg['models'].items())
            if len(models) > 1:
                print(f"\n{provider_cfg['name']} models:")
                for i, (mid, mdata) in enumerate(models, 1):
                    print(f"  {i}. {mdata['name']} — {mdata['description']}")
                midx = IntPrompt.ask("Select model", default=1)
                midx = max(1, min(len(models), midx))
                tts_provider_model = models[midx - 1][0]
            else:
                tts_provider_model = models[0][0]

            # Voice selection
            voices = provider_cfg['voices']
            print(f"\n{provider_cfg['name']} voices:")
            for i, v in enumerate(voices, 1):
                print(f"  {i}. {v}")
            vidx = IntPrompt.ask("Select voice", default=1)
            vidx = max(1, min(len(voices), vidx))
            tts_provider_voice = voices[vidx - 1]

        else:
            # pocket-tts local path — existing logic unchanged
            print("Uses Pocket TTS (CPU-only, English, built-in voices).")
            tts_voice_input = Prompt.ask("Voice to use", default="alba")
            pocket_voices = ['alba', 'marius', 'javert', 'jean', 'fantine',
                             'cosette', 'eponine', 'azelma']
            if tts_voice_input.strip().lower() in pocket_voices:
                tts_voice = tts_voice_input.strip().lower()
```

**Important:** `IntPrompt` must be added to the module-level import at the top of `cli_commands.py` (line ~16). Find:
```python
from rich.prompt import Prompt, Confirm
```
And replace with:
```python
from rich.prompt import Prompt, Confirm, IntPrompt
```
There are two `from rich.prompt import` lines in the file; patch the one at module scope (line ~16), not any local import inside a function.

- [ ] **Update the wizard summary print (line ~1678)**

Replace the TTS line in the summary with:
```python
    if setup_tts_choice and tts_backend == 'cloud':
        print(f"Text-to-speech (TTS): Yes (cloud: {tts_provider_id}, voice: {tts_provider_voice})")
    elif setup_tts_choice:
        print(f"Text-to-speech (TTS): Yes (pocket-tts, voice: {tts_voice})")
    else:
        print("Text-to-speech (TTS): No")
```

- [ ] **Update the wizard execution block (line ~1731)**

Replace the `if setup_tts_choice:` block with:

```python
        # Step 2b2: TTS
        if setup_tts_choice:
            if tts_backend == 'cloud':
                from .backend_installer import setup_cloud_tts_provider
                success, msg = setup_cloud_tts_provider(
                    tts_provider_id, _get_credential(tts_provider_id),
                    model=tts_provider_model, voice=tts_provider_voice,
                )
                if success:
                    log_success(f"Text-to-speech enabled ({msg})")
                else:
                    log_error(f"TTS cloud setup failed: {msg}")
            else:
                log_info("Installing Pocket TTS...")
                if install_tts_backend(custom_python=python_path):
                    config = ConfigManager()
                    config.set_setting('tts_enabled', True)
                    config.set_setting('tts_provider', 'pocket-tts')
                    config.set_setting('tts_voice', tts_voice)
                    config.set_setting('tts_shortcut', 'SUPER+ALT+S')
                    config.set_setting('tts_osd_enabled', True)
                    config.save_config()
                    log_success("Text-to-speech enabled")
                else:
                    log_error("TTS installation failed - continuing without TTS")
        else:
            config = ConfigManager()
            config.set_setting('tts_enabled', False)
            config.save_config()
            log_info("Text-to-speech disabled")
```

- [ ] **Update auto-setup path (~line 2183)**

The auto-setup currently calls `install_tts_backend()` unconditionally. It only runs for `--tts` flag. Since auto-setup can't interactively ask for cloud credentials, it defaults to pocket-tts. No change required unless `--tts-provider` flag is added (out of scope). Add a comment:

```python
        # Auto-setup always installs pocket-tts. Cloud TTS requires interactive setup.
        log_info("Installing Pocket TTS...")
        if install_tts_backend(custom_python=python_path):
```

- [ ] **Verify wizard runs without errors (dry run)**

```bash
# Pipe 'n' to avoid actually running through the full wizard
echo "n" | hyprwhspr setup 2>&1 | head -20
```

Expected: setup launches, asks first question, exits cleanly on 'n'.

- [ ] **Commit**

```bash
git add lib/src/cli_commands.py
git commit -m "feat: extend TTS setup wizard with cloud provider selection"
```

---

## Chunk 5: Documentation

### Task 8: Update `docs/CONFIGURATION.md`

**Files:**
- Modify: `docs/CONFIGURATION.md`

- [ ] **Add cloud TTS section**

Find the existing TTS section in `CONFIGURATION.md` (search for `tts_enabled`). After the existing TTS table/description, add:

```markdown
### Cloud TTS Providers

In addition to the default local pocket-tts backend, hyprwhspr supports cloud TTS providers
for lower latency and higher quality synthesis.

| Provider | Streaming | Latency | Notes |
|----------|-----------|---------|-------|
| `openai` | Yes | ~200ms | Models: gpt-4o-mini-tts, tts-1, tts-1-hd |
| `groq` | Yes | ~200ms | Powered by PlayAI |
| `elevenlabs` | Yes | ~75ms | Lowest latency option |
| `deepgram` | No | ~300ms | Aura 2 voices |
| `lemonfox` | No | ~300ms | OpenAI-compatible |

**Setup:** Run `hyprwhspr setup` and choose "cloud" when prompted for TTS backend.

**Config keys:**

| Key | Default | Description |
|-----|---------|-------------|
| `tts_provider` | `pocket-tts` | `pocket-tts` or a cloud provider ID |
| `tts_cloud_model` | `null` | Provider model ID (`null` = provider default) |
| `tts_cloud_voice` | `null` | Provider voice ID (`null` = provider default) |

**Manual configuration example (ElevenLabs):**
```json
{
  "tts_provider": "elevenlabs",
  "tts_cloud_model": "eleven_turbo_v2_5",
  "tts_cloud_voice": "aria"
}
```
Then run `hyprwhspr setup` to store your API key securely.

**Sharing keys with STT:** If you already use ElevenLabs or OpenAI for STT,
the same API key is reused automatically — no second entry needed.
```

- [ ] **Commit**

```bash
git add docs/CONFIGURATION.md
git commit -m "docs: add cloud TTS provider section to CONFIGURATION.md"
```

---

## Final Verification

- [ ] **Verify `hyprwhspr config show --all` shows new keys**

```bash
hyprwhspr config show --all | grep tts_provider
```

Expected: `tts_provider: pocket-tts`

- [ ] **Verify `speak` subcommand help**

```bash
hyprwhspr speak --help
```

Expected: `--provider` and `--model` flags visible.

- [ ] **Verify registry structure (sanity check)**

```bash
cd /home/nomadx/projects/hyprwhspr
python3 -c "
import sys; sys.path.insert(0, 'lib/src')
from tts_provider_registry import list_providers, get_provider
for pid, name, streaming in list_providers():
    p = get_provider(pid)
    print(f'{pid}: streaming={streaming}, voices={len(p[\"voices\"])}, models={len(p[\"models\"])}')
"
```

- [ ] **End-to-end smoke test (pocket-tts — existing path)**

```bash
hyprwhspr speak --text "Cloud TTS smoke test complete"
```

Expected: audio via pocket-tts unchanged.

- [ ] **End-to-end smoke test (cloud — if key available)**

```bash
# Only if you have a key handy; skip otherwise
hyprwhspr speak --provider openai --text "Hello from OpenAI TTS"
```

Expected: audio via OpenAI TTS streaming.
