"""
Edge-TTS integration for AI Calorie Assistant.
Provides text-to-speech synthesis using Microsoft Edge's TTS service.
"""
import os
import json
import base64
import logging
import asyncio
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ── Edge-TTS API endpoints ──
EDGE_TTS_TRUSTED_HOST = "https://speech.platform.bing.com"
EDGE_TTS_TOKEN_URL = "https://edge.microsoft.com/translate/auth"

# Default voice configuration
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"     # Chinese (Mandarin, Simplified)
DEFAULT_RATE = "+0%"                       # Speaking rate
DEFAULT_VOLUME = "+0%"                     # Volume
DEFAULT_PITCH = "+0Hz"                     # Pitch

# Available voices (commonly used)
AVAILABLE_VOICES = {
    # Chinese
    "zh-CN-XiaoxiaoNeural": "晓晓 (女, 普通话)",
    "zh-CN-XiaoyiNeural": "晓伊 (女, 普通话)",
    "zh-CN-YunjianNeural": "云健 (男, 普通话)",
    "zh-CN-YunxiNeural": "云希 (男, 普通话)",
    "zh-CN-YunyangNeural": "云扬 (男, 普通话)",
    # English
    "en-US-AriaNeural": "Aria (Female, US)",
    "en-US-GuyNeural": "Guy (Male, US)",
    "en-GB-SoniaNeural": "Sonia (Female, UK)",
    "en-GB-RyanNeural": "Ryan (Male, UK)",
    # Japanese
    "ja-JP-NanamiNeural": "Nanami (Female)",
    "ja-JP-KeitaNeural": "Keita (Male)",
    # Korean
    "ko-KR-SunHiNeural": "Sun-Hi (Female)",
    "ko-KR-InJoonNeural": "InJoon (Male)",
}


async def _fetch_token() -> str:
    """Obtain an access token from Edge TTS."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(EDGE_TTS_TOKEN_URL)
        resp.raise_for_status()
        return resp.text.strip()


def _build_ssml(text: str, voice: str = DEFAULT_VOICE,
                rate: str = DEFAULT_RATE,
                pitch: str = DEFAULT_PITCH) -> str:
    """Build SSML markup for Edge TTS."""
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
             xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{voice[:5]}">
  <voice name="{voice}">
    <prosody rate="{rate}" pitch="{pitch}">
      {text}
    </prosody>
  </voice>
</speak>"""


async def synthesize(text: str, voice: str = DEFAULT_VOICE,
                     rate: str = DEFAULT_RATE,
                     pitch: str = DEFAULT_PITCH) -> Optional[bytes]:
    """
    Synthesize text to speech using Edge TTS.
    Returns raw audio bytes (audio/mpeg) or None on failure.
    """
    try:
        token = await _fetch_token()
        ssml = _build_ssml(text, voice, rate, pitch)

        url = f"{EDGE_TTS_TRUSTED_HOST}/consumer/speech/synthesize/readaloud/edge/v1"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/ssml+xml",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, content=ssml)
            resp.raise_for_status()

            # Parse the response — it's a binary stream with audio data
            # The response contains the audio data after the JSON header
            body = resp.content
            audio_start = body.find(b"Path:")
            if audio_start == -1:
                # Try to extract from audio/x-mpeg format
                return body

            # Extract audio data from the response format
            audio_data = body[audio_start:]
            # Find the actual audio start
            path_end = audio_data.find(b"\r\n\r\n")
            if path_end != -1:
                audio_data = audio_data[path_end + 4:]

            # Find audio boundary
            boundary = b"--"
            end_idx = audio_data.find(boundary)
            if end_idx != -1:
                audio_data = audio_data[:end_idx]

            if audio_data and len(audio_data) > 100:
                logger.info(f"TTS synthesized {len(audio_data)} bytes, voice={voice}")
                return audio_data

            logger.warning(f"TTS returned minimal audio data ({len(audio_data)} bytes)")
            return None

    except httpx.HTTPStatusError as e:
        logger.error(f"TTS HTTP error: {e.response.status_code} - {e.response.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return None


async def list_available_voices() -> dict:
    """Return the available voices dictionary."""
    return AVAILABLE_VOICES
