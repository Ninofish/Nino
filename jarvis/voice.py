"""
voice.py  –  J.A.R.V.I.S  Voice I/O
─────────────────────────────────────
TTS  : Fish.audio  (falls back to pyttsx3, then print)
STT  : Google Speech Recognition via SpeechRecognition library
─────────────────────────────────────
Required env vars:
    FISH_AUDIO_KEY          – Fish.audio API key
    FISH_AUDIO_VOICE_ID     – (optional) Fish.audio reference/voice ID
"""

import io
import os
import queue
import tempfile
import threading
import time

# ── constants ────────────────────────────────────────────────────────────────
VOICE_ERROR = "__VOICE_ERROR__"

# ── helpers ──────────────────────────────────────────────────────────────────

def _play_audio_bytes(data: bytes, fmt: str = "mp3") -> None:
    """Play raw audio bytes using pygame (cross-platform)."""
    try:
        import pygame  # type: ignore

        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        sound = pygame.mixer.Sound(io.BytesIO(data))
        channel = sound.play()
        while channel.get_busy():
            pygame.time.Clock().tick(20)
    except Exception:
        # Last-resort: write to temp file and use subprocess
        try:
            import subprocess

            suffix = f".{fmt}"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(data)
                tmp = f.name
            subprocess.run(["ffplay", "-nodisp", "-autoexit", tmp],
                           capture_output=True, check=False)
            os.unlink(tmp)
        except Exception:
            pass


def _fish_tts(text: str) -> bytes | None:
    """Call Fish.audio TTS API and return raw MP3 bytes, or None on failure."""
    api_key = os.getenv("FISH_AUDIO_KEY", "").strip()
    if not api_key:
        return None

    try:
        import httpx  # type: ignore

        voice_id = os.getenv("FISH_AUDIO_VOICE_ID", "").strip()
        payload: dict = {
            "text": text,
            "format": "mp3",
            "mp3_bitrate": 128,
            "latency": "normal",
        }
        if voice_id:
            payload["reference_id"] = voice_id

        resp = httpx.post(
            "https://api.fish.audio/v1/tts",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.content
        print(f"  [Fish.audio error {resp.status_code}]: {resp.text[:120]}")
        return None
    except Exception as exc:
        print(f"  [Fish.audio exception]: {exc}")
        return None


# ── public API ────────────────────────────────────────────────────────────────

def speak(text: str) -> None:
    """
    Speak *text* aloud.

    Priority:
      1. Fish.audio TTS  (requires FISH_AUDIO_KEY)
      2. pyttsx3 offline TTS
      3. Plain print fallback
    """
    print(f"\nJARVIS ▶  {text}")

    # 1) Fish.audio
    audio = _fish_tts(text)
    if audio:
        _play_audio_bytes(audio, "mp3")
        return

    # 2) pyttsx3
    try:
        import pyttsx3  # type: ignore

        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.setProperty("volume", 0.9)
        engine.say(text)
        engine.runAndWait()
        return
    except Exception:
        pass

    # 3) Plain print (already printed above)


def listen(timeout: int = 10, phrase_limit: int = 20) -> str:
    """
    Capture one utterance and return the transcribed text.
    Returns VOICE_ERROR if mic or STT is unavailable.
    """
    try:
        import speech_recognition as sr  # type: ignore

        r = sr.Recognizer()
        r.energy_threshold = 300
        r.dynamic_energy_threshold = True

        with sr.Microphone() as source:
            print("  🎤  Listening…", flush=True)
            r.adjust_for_ambient_noise(source, duration=0.4)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)

        text: str = r.recognize_google(audio)
        return text.strip()

    except Exception:
        return VOICE_ERROR


def start_background_listening(
    timeout: int = 10,
    phrase_limit: int = 20,
) -> tuple[queue.Queue, object, str | None]:
    """
    Spin up a background thread that continuously listens and puts
    recognised phrases into a Queue.

    Returns:
        (queue, stop_fn, error_msg)
        error_msg is None on success, a string on failure.
    """
    try:
        import speech_recognition as sr  # type: ignore

        q: queue.Queue = queue.Queue()
        stop_event = threading.Event()

        r = sr.Recognizer()
        r.energy_threshold = 300
        r.dynamic_energy_threshold = True

        mic = sr.Microphone()

        def _callback(recognizer: sr.Recognizer, audio: sr.AudioData) -> None:
            if stop_event.is_set():
                return
            try:
                text = recognizer.recognize_google(audio)
                if text:
                    q.put(text.strip())
            except sr.UnknownValueError:
                pass  # silence / unrecognised – ignore
            except Exception:
                pass

        # Warm-up: calibrate ambient noise once
        with mic as source:
            r.adjust_for_ambient_noise(source, duration=0.5)

        stop_listening = r.listen_in_background(mic, _callback,
                                                phrase_time_limit=phrase_limit)

        def _stop() -> None:
            stop_event.set()
            stop_listening(wait_for_stop=False)

        return q, _stop, None

    except Exception as exc:
        return queue.Queue(), lambda: None, str(exc)


def list_microphones() -> list[str]:
    """Return a list of available microphone device names."""
    try:
        import speech_recognition as sr  # type: ignore

        return sr.Microphone.list_microphone_names()
    except Exception:
        return []
