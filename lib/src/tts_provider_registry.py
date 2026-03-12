"""
Provider registry for cloud TTS backends.
Mirrors provider_registry.py - one entry per provider with all request metadata.
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
        'request_text_field': 'input',
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
        'request_text_field': 'input',
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
        'api_key_prefix': '',
        'api_key_validation_prefix': None,
        'api_key_description': 'ElevenLabs API key',
        'streaming': True,
        'audio_format': 'mp3',
        'request_text_field': 'text',
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
        'request_text_field': 'text',
        'voices': ['aura-2-thalia-en', 'aura-2-zeus-en', 'aura-2-luna-en',
                   'aura-2-orion-en', 'aura-2-asteria-en'],
        'default_voice': 'aura-2-thalia-en',
        'endpoint_uses_voice_in_url': False,
        'voice_as_query_param': True,
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
        'request_text_field': 'input',
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
        (provider_id, provider['name'], provider['streaming'])
        for provider_id, provider in TTS_PROVIDERS.items()
    ]
    return sorted(items, key=lambda item: (not item[2], item[0]))


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
