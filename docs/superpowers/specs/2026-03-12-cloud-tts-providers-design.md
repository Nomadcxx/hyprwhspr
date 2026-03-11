# Cloud TTS Provider Support — Design Spec

**Date:** 2026-03-12
**Branch:** `feat/pocket-tts` (target: new branch once PR #129 merges)
**Depends on:** PR #129 (zenocode-org) merged into upstream main

---

## Context

PR #129 adds local TTS via pocket-tts. This follow-up PR extends the TTS system with cloud provider support (ElevenLabs, OpenAI, Groq, Deepgram, Lemonfox), mirroring the existing cloud STT provider architecture. Provider parity with STT is a goal — every provider available for STT that also offers TTS is included.

---

## Approach

**Option A (selected):** Extend `TTSManager` with provider dispatch + new `tts_provider_registry.py`.

- Existing pocket-tts path unchanged
- New `tts_provider_registry.py` mirrors `provider_registry.py` pattern exactly
- `TTSManager` gains `_speak_cloud()` which dispatches based on registry flags
- Streaming providers (OpenAI, Groq, ElevenLabs) pipe audio chunks to `ffplay` stdin for sub-200ms first audio
- Non-streaming providers (Deepgram, Lemonfox) use POST → temp file → `AudioManager.play_file()`
- API keys shared with STT credential store — same provider, same key

---

## Providers

| Provider | Streaming | Latency | TTS Endpoint |
|----------|-----------|---------|--------------|
| ElevenLabs | Yes | ~75ms | `/v1/text-to-speech/{voice_id}/stream` |
| OpenAI | Yes | ~200ms | `/v1/audio/speech` |
| Groq | Yes | ~200ms | `/v1/audio/speech` (PlayAI) |
| Deepgram | No | ~300ms | `/v1/speak` |
| Lemonfox | No | ~300ms | `/v1/audio/speech` (OAI-compat) |
| pocket-tts | N/A | local | local model |
| Regolo | — | no TTS API | excluded |

---

## Files Changed

### New
- `lib/src/tts_provider_registry.py`

### Modified
- `lib/src/tts_manager.py`
- `lib/src/cli_commands.py`
- `lib/src/backend_installer.py`
- `lib/cli.py`
- `lib/src/config_manager.py`
- `share/config.schema.json`
- `docs/CONFIGURATION.md`

---

## `tts_provider_registry.py`

Single `TTS_PROVIDERS` dict. Each entry contains everything needed to construct a request without hardcoding in `tts_manager.py`.

```python
TTS_PROVIDERS = {
    'openai': {
        'name': 'OpenAI',
        'endpoint': 'https://api.openai.com/v1/audio/speech',
        'api_key_prefix': 'sk-',
        'api_key_description': 'OpenAI API key (starts with sk-)',
        'streaming': True,
        'audio_format': 'mp3',
        'voices': ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
        'default_voice': 'alloy',
        'endpoint_uses_voice_in_url': False,
        'voice_as_query_param': False,
        'models': {
            'gpt-4o-mini-tts': {'name': 'GPT-4o Mini TTS', 'description': 'Lowest latency, steerable'},
            'tts-1':           {'name': 'TTS-1',           'description': 'Optimised for speed'},
            'tts-1-hd':        {'name': 'TTS-1 HD',        'description': 'Higher quality'},
        },
        'default_model': 'gpt-4o-mini-tts',
    },
    'groq': {
        'name': 'Groq',
        'endpoint': 'https://api.groq.com/openai/v1/audio/speech',
        'api_key_prefix': 'gsk_',
        'api_key_description': 'Groq API key (starts with gsk_)',
        'streaming': True,
        'audio_format': 'mp3',
        'voices': ['Aaliyah-PlayAI', 'Adelaide-PlayAI', 'Angelo-PlayAI', 'Briggs-PlayAI'],
        'default_voice': 'Aaliyah-PlayAI',
        'endpoint_uses_voice_in_url': False,
        'voice_as_query_param': False,
        'models': {
            'playai-tts':        {'name': 'PlayAI TTS',        'description': 'Fast, natural speech'},
            'playai-tts-arabic': {'name': 'PlayAI TTS Arabic', 'description': 'Arabic language support'},
        },
        'default_model': 'playai-tts',
    },
    'elevenlabs': {
        'name': 'ElevenLabs',
        'endpoint': 'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream',
        'api_key_header': 'xi-api-key',
        'api_key_description': 'ElevenLabs API key',
        'streaming': True,
        'audio_format': 'mp3',
        'voices': ['aria', 'sarah', 'laura', 'charlie', 'george', 'callum'],
        'default_voice': 'aria',
        'endpoint_uses_voice_in_url': True,
        'voice_as_query_param': False,
        'models': {
            'eleven_turbo_v2_5':      {'name': 'Turbo v2.5',       'description': 'Lowest latency (~75ms)'},
            'eleven_multilingual_v2': {'name': 'Multilingual v2',  'description': 'Best quality, 29 languages'},
        },
        'default_model': 'eleven_turbo_v2_5',
    },
    'deepgram': {
        'name': 'Deepgram',
        'endpoint': 'https://api.deepgram.com/v1/speak',
        'api_key_header': 'Authorization',
        'api_key_prefix': 'Token ',
        'api_key_description': 'Deepgram API key',
        'streaming': False,
        'audio_format': 'mp3',
        'voices': ['aura-2-thalia-en', 'aura-2-zeus-en', 'aura-2-luna-en'],
        'default_voice': 'aura-2-thalia-en',
        'endpoint_uses_voice_in_url': False,
        'voice_as_query_param': True,
        'models': {
            'aura-2': {'name': 'Aura 2', 'description': 'Natural, low latency'},
        },
        'default_model': 'aura-2',
    },
    'lemonfox': {
        'name': 'Lemonfox',
        'endpoint': 'https://api.lemonfox.ai/v1/audio/speech',
        'api_key_header': 'Authorization',
        'api_key_prefix': 'Bearer ',
        'api_key_description': 'Lemonfox API key',
        'streaming': False,
        'audio_format': 'mp3',
        'voices': ['sarah', 'rachel', 'domi', 'bella', 'antoni', 'elli'],
        'default_voice': 'sarah',
        'endpoint_uses_voice_in_url': False,
        'voice_as_query_param': False,
        'models': {
            'tts-1': {'name': 'TTS-1', 'description': 'OpenAI-compatible TTS'},
        },
        'default_model': 'tts-1',
    },
}

def get_provider(provider_id: str) -> dict | None:
    return TTS_PROVIDERS.get(provider_id)

def list_providers() -> list[str]:
    return list(TTS_PROVIDERS.keys())
```

Helper functions mirror `provider_registry.py`: `get_provider()`, `list_providers()`, `validate_api_key()`.

---

## `tts_manager.py` Changes

### Constructor additions
```python
self.provider = config_manager.get_setting('tts_provider', 'pocket-tts')
self.cloud_model = config_manager.get_setting('tts_cloud_model', None)
self.cloud_voice = config_manager.get_setting('tts_cloud_voice', None)
```

### New `speak()` dispatch method
A new top-level `speak()` method is added. The existing `synthesize_and_play_streaming()` is **not renamed** — `speak_command` in `cli_commands.py` is updated to call `speak()` instead of `synthesize_and_play_streaming()` directly.

```python
def speak(self, text: str, voice: Optional[str] = None, progress_callback=None):
    """Dispatch to local (pocket-tts) or cloud provider."""
    if self.provider == 'pocket-tts':
        # Existing path — unchanged
        return self.synthesize_and_play_streaming(text, voice=voice,
                                                  progress_callback=progress_callback)
    return self._speak_cloud(text, progress_callback=progress_callback)
```

`speak_command` in `cli_commands.py` is updated: replace `tts_manager.synthesize_and_play_streaming(...)` call with `tts_manager.speak(text, voice=voice, ...)`.

### `_speak_cloud()` structure
```python
def _speak_cloud(self, text: str, progress_callback=None):
    provider = get_provider(self.provider)
    api_key  = get_credential(self.provider)

    url          = _build_url(provider, self.cloud_voice)
    headers      = _build_headers(provider, api_key)
    body, params = _build_request(provider, text, self.cloud_voice, self.cloud_model)

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
        # Fall back to pocket-tts if installed
        try:
            import pocket_tts  # noqa: F401
            _log_tts("Falling back to pocket-tts")
            return self.synthesize_and_play_streaming(text, progress_callback=progress_callback)
        except ImportError:
            raise
```

`progress_callback` signature: `callback(state: str, progress: float) -> None`. States used: `'fetching'` (before HTTP request), `'playing'` (audio started), `'error'`. Same states already used by pocket-tts OSD — no OSD changes required.

Three private helpers keep all provider-specific branching in one place, driven entirely by registry flags — no scattered `if provider == 'elevenlabs'` checks elsewhere:
- `_build_url(provider, voice)` — substitutes `{voice_id}` in URL for ElevenLabs
- `_build_headers(provider, api_key)` — handles `xi-api-key` vs `Authorization: Token/Bearer`
- `_build_request(provider, text, voice, model)` — handles Deepgram query-param voice vs body voice

### Streaming path
```python
def _stream_to_player(self, url, headers, body, params, progress_callback):
    player = subprocess.Popen(
        ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', '-i', 'pipe:0'],
        stdin=subprocess.PIPE
    )
    with requests.post(url, headers=headers, json=body,
                       params=params, stream=True, timeout=30) as resp:
        resp.raise_for_status()
        if progress_callback:
            progress_callback('playing', 0.5)
        for chunk in resp.iter_content(chunk_size=4096):
            if chunk:
                player.stdin.write(chunk)
    player.stdin.close()
    player.wait()
```

### Non-streaming path
```python
def _request_and_play(self, url, headers, body, params, progress_callback):
    resp = requests.post(url, headers=headers, json=body, params=params, timeout=30)
    resp.raise_for_status()
    tmp = TEMP_DIR / 'tts_cloud_output.mp3'
    tmp.write_bytes(resp.content)
    if progress_callback:
        progress_callback('playing', 1.0)
    self._audio_manager.play_file(str(tmp))
```

### `is_available()` fix
```python
def is_available(self) -> bool:
    if self.provider == 'pocket-tts':
        try:
            import pocket_tts  # noqa: F401
            return True
        except ImportError:
            return False
    # Cloud: available if API key is stored
    return bool(get_credential(self.provider))
```

---

## `cli_commands.py` — Setup Wizard Changes

### New TTS setup flow
```
Enable TTS? [y/N]
  └─ yes →
       Choose TTS backend:
         1. Local  - pocket-tts (free, offline, CPU)
         2. Cloud  - faster, higher quality (requires API key)

       [cloud] →
         Select provider:
           1. ElevenLabs  (~75ms, streaming)
           2. OpenAI      (~200ms, streaming)
           3. Groq        (~200ms, streaming)
           4. Deepgram    (non-streaming)
           5. Lemonfox    (non-streaming)

         [if key already in credential store] →
           Found existing [Provider] key from STT setup. Use it? [Y/n]

         [if no/new key] →
           Enter [Provider] API key:  (validated against api_key_prefix)

         [if provider has >1 model] →
           Select model: (list from registry)

         Select voice: (list from registry)

         Test it? [Y/n]
```

### Provider list built from registry
No hardcoding — wizard iterates `tts_provider_registry.TTS_PROVIDERS`, sorted by `provider['streaming']` descending so streaming providers appear first. Latency hint shown next to each entry.

### Key reuse
`credential_manager.get_credential(provider_id)` — same lookup as STT wizard. If found, offer to reuse.

### `speak_command` fixes
- Error message becomes provider-aware
- Voice resolution: `tts_cloud_voice` for cloud, `tts_voice` for pocket-tts
- `--provider` and `--model` flags added to `speak` subparser for per-invocation override

---

## `backend_installer.py` Changes

New function added:
```python
def setup_cloud_tts_provider(provider_id: str, api_key: str,
                              model: Optional[str] = None,
                              voice: Optional[str] = None) -> Tuple[bool, str]:
    """
    Configure a cloud TTS provider. No pip install — just stores credentials
    and writes config defaults.
    Returns (success, message).
    """
    try:
        from .tts_provider_registry import get_provider
        from .credential_manager import store_credential
        provider = get_provider(provider_id)
        if not provider:
            return False, f"Unknown TTS provider: {provider_id}"
        store_credential(provider_id, api_key)
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

Setup wizard branches on user choice:
```python
if tts_backend == 'pocket-tts':
    install_tts_backend(...)                                   # existing, unchanged
else:
    setup_cloud_tts_provider(provider_id, api_key, model, voice)  # new
```

`credential_manager.store_credential()` is the existing function used by the STT setup wizard — same call pattern.

---

## Config Keys Added

Three keys added to `ConfigManager.default_config` (lines ~109–114 in `config_manager.py`) alongside existing `tts_*` keys:

```python
'tts_provider':    'pocket-tts',  # 'pocket-tts' | 'openai' | 'groq' | 'elevenlabs' | 'deepgram' | 'lemonfox'
'tts_cloud_model': None,          # Provider model ID; None = use provider default_model
'tts_cloud_voice': None,          # Provider voice ID; None = use provider default_voice
```

Three entries added to `share/config.schema.json`:
```json
"tts_provider": {
  "type": "string",
  "default": "pocket-tts",
  "description": "TTS backend: 'pocket-tts' for local or a cloud provider ID"
},
"tts_cloud_model": {
  "type": ["string", "null"],
  "default": null,
  "description": "Cloud TTS model ID (null = provider default)"
},
"tts_cloud_voice": {
  "type": ["string", "null"],
  "default": null,
  "description": "Cloud TTS voice ID (null = provider default)"
}
```

Existing `tts_voice` key unchanged — still used exclusively for pocket-tts path.

---

## Provider-Specific Wizard Notes

| Provider | Model selection | Voice in | API key header | Auth format |
|----------|----------------|----------|----------------|-------------|
| OpenAI | Yes (3) | body | `Authorization` | `Bearer sk-...` |
| Groq | Yes (2) | body | `Authorization` | `Bearer gsk_...` |
| ElevenLabs | Yes (2) | **URL path** | `xi-api-key` | raw key |
| Deepgram | Skip (1) | **query param** | `Authorization` | `Token <key>` |
| Lemonfox | Skip (1) | body | `Authorization` | `Bearer <key>` |

---

## Runtime Dependencies

- `requests>=2.25.0` — already in `requirements.txt` ✅
- `ffplay` — already first choice in `AudioManager.play_file()` chain ✅
- No new pip packages required

---

## Out of Scope

- `hyprwhspr config set` subcommand (no equivalent for STT either; users use wizard or `config edit`)
- Regolo TTS (no public TTS API)
- WebSocket/streaming TTS beyond chunked HTTP (no provider requires it)
- Voice cloning (provider-specific, post-MVP)
