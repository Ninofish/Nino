"""
main.py  –  J.A.R.V.I.S  Personal Assistant
─────────────────────────────────────────────────
Usage:
    python main.py          # text mode (default)
    python main.py --voice  # start in voice mode
─────────────────────────────────────────────────
Commands (text or voice):
    voice       – toggle voice input on/off
    talk        – one-shot speech capture (text mode)
    mics        – list available microphones
    clear       – clear conversation memory
    help        – show command list
    quit/exit   – shut down JARVIS
─────────────────────────────────────────────────
"""

import argparse
import sys
import time
from datetime import datetime

try:
    # Running as a script: python jarvis/main.py
    from brain import chat
    from voice import VOICE_ERROR, list_microphones, listen, speak, start_background_listening
except ImportError:
    # Running as a module: python -m jarvis.main
    from .brain import chat
    from .voice import VOICE_ERROR, list_microphones, listen, speak, start_background_listening

BANNER = r"""
  ╔══════════════════════════════════════════════════════════╗
  ║     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗            ║
  ║     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝            ║
  ║     ██║███████║██████╔╝██║   ██║██║███████╗            ║
  ║██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║            ║
  ║╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║            ║
  ║ ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝            ║
  ║                                                          ║
  ║   Just A Rather Very Intelligent System  v1.0           ║
  ║   Powered by GPT-4o · Brave · Fish.audio · Google       ║
  ╠══════════════════════════════════════════════════════════╣
  ║  Commands:  voice | talk | mics | clear | help | quit   ║
  ╚══════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
  Commands:
    voice  – toggle voice input on/off
    talk   – one-shot mic capture (text mode only)
    mics   – list available microphones
    clear  – wipe conversation memory
    help   – show this message
    quit   – shut down JARVIS
"""


# ── voice-mode state ──────────────────────────────────────────────────────────

class VoiceState:
    """Holds mutable voice-mode state so it can be passed around cleanly."""

    def __init__(self) -> None:
        self.active: bool = False
        self.bg_queue = None          # Queue | None
        self.bg_stop = None           # callable | None
        self.use_fallback: bool = False   # True → use blocking listen()

    def start(self) -> str | None:
        """
        Activate voice mode. Returns an error string on failure, None on success.
        Idempotent if already started.
        """
        if self.bg_queue is not None or self.use_fallback:
            return None  # already running

        bg_queue, bg_stop, err = start_background_listening()
        if err:
            self.use_fallback = True
            return err

        self.bg_queue = bg_queue
        self.bg_stop = bg_stop
        self.active = True
        return None

    def stop(self) -> None:
        """Deactivate voice mode and clean up the background thread."""
        self.active = False
        self.use_fallback = False
        if self.bg_stop is not None:
            try:
                self.bg_stop()
            except Exception:
                pass
        self.bg_queue = None
        self.bg_stop = None

    def get_phrase(self) -> str | None:
        """
        Return the next recognised phrase, or None if nothing is ready yet.
        Uses the background listener when available, falls back to blocking listen().
        Returns VOICE_ERROR on a hard failure.
        """
        if self.use_fallback:
            return listen()  # blocks until speech or error
        try:
            return self.bg_queue.get_nowait()
        except Exception:
            return None  # queue empty – caller should retry


# ── command dispatch ──────────────────────────────────────────────────────────

def _dispatch_command(
    text: str,
    history: list[dict],
    vs: VoiceState,
) -> tuple[bool, bool]:
    """
    Handle a built-in command.

    Returns:
        (handled, should_quit)
        handled     – True if *text* was a command (caller should not send to AI)
        should_quit – True if the user asked to quit
    """
    cmd = text.strip().lower()

    if cmd in ("quit", "exit"):
        return True, True

    if cmd == "clear":
        history.clear()
        speak("Memory cleared, Boss.")
        return True, False

    if cmd == "help":
        print(HELP_TEXT)
        speak("Available commands: voice, talk, mics, clear, help, and quit.")
        return True, False

    if cmd in ("mics", "microphones", "list mics"):
        names = list_microphones()
        if names:
            print("  Available microphones:")
            for i, name in enumerate(names, 1):
                print(f"    {i}. {name}")
        else:
            print("  No microphones detected.")
        return True, False

    if cmd == "voice":
        if vs.active or vs.use_fallback:
            # Switch to text mode
            vs.stop()
            speak("Switched to text mode.")
            print("  → Text mode on.")
        else:
            # Switch to voice mode
            err = vs.start()
            if err:
                print(f"  ⚠️  {err}")
                print("  → Falling back to direct speech capture.")
                vs.active = True
                speak("Voice mode on (direct capture).")
            else:
                speak("Voice mode on.")
                print("  → Voice mode on. Listening…")
        return True, False

    if cmd == "talk":
        # One-shot mic capture; only meaningful in text mode
        phrase = listen()
        if phrase == VOICE_ERROR or not phrase:
            print("  ⚠️  Voice input failed (mic/STT not available).")
            return True, False
        print(f"  You (speech): {phrase}")
        # Re-enter dispatch so the spoken phrase is processed as a message
        return False, False  # caller will send 'phrase' to AI — see below

    return False, False


# ── main loop ─────────────────────────────────────────────────────────────────

def run() -> None:
    parser = argparse.ArgumentParser(description="JARVIS Personal Assistant")
    parser.add_argument("--voice", action="store_true", help="Start in voice mode")
    args = parser.parse_args()

    print(BANNER)

    history: list[dict] = []
    vs = VoiceState()

    now = datetime.now().strftime("%A, %B %d  %I:%M %p")
    speak(
        f"Good day, Boss. JARVIS is online. "
        f"Today is {now}. All systems nominal. How can I assist?"
    )
    print("\n  Type 'help' for commands  |  'quit' to exit\n")
    print("─" * 62)

    # Honour --voice flag
    if args.voice:
        err = vs.start()
        if err:
            print(f"  ⚠️  {err}")
            print("  → Falling back to direct speech capture.")
            vs.active = True
            speak("Voice mode on (direct capture).")
        else:
            speak("Voice mode on.")
            print("  → Voice mode on. Listening…")

    while True:
        try:
            # ── get user input ────────────────────────────────────────────────
            user_input: str | None = None

            if vs.active or vs.use_fallback:
                phrase = vs.get_phrase()
                if phrase is None:
                    time.sleep(0.05)
                    continue
                if phrase == VOICE_ERROR:
                    print("  ⚠️  Voice input failed. Switching to text mode.")
                    vs.stop()
                    continue
                user_input = phrase
                print(f"\nYou (voice) ▶  {user_input}")
            else:
                print("\nYou ▶  ", end="", flush=True)
                raw = input()
                if not raw.strip():
                    continue

                # Handle the special 'talk' command before the generic dispatch
                # so we can redirect the spoken phrase back as user_input.
                if raw.strip().lower() == "talk":
                    phrase = listen()
                    if phrase == VOICE_ERROR or not phrase:
                        print("  ⚠️  Voice input failed (mic/STT not available).")
                        continue
                    print(f"  You (speech): {phrase}")
                    user_input = phrase
                else:
                    user_input = raw.strip()

            # ── built-in commands ─────────────────────────────────────────────
            handled, should_quit = _dispatch_command(user_input, history, vs)
            if should_quit:
                break
            if handled:
                continue

            # ── send to AI ────────────────────────────────────────────────────
            print("  ⚡  Thinking…", flush=True)
            history.append({"role": "user", "content": user_input})
            response, history = chat(history)
            speak(response)

            # Keep history bounded to avoid ballooning token costs
            if len(history) > 40:
                history = history[-40:]

        except KeyboardInterrupt:
            print("\n\n  ⚠️  Interrupted.")
            speak("Emergency shutdown, Boss. Goodbye.")
            sys.exit(0)
        except Exception as exc:
            print(f"\n  ❌  Error: {exc}")
            speak("I encountered an error, Boss. Check the terminal for details.")

    # ── shutdown ──────────────────────────────────────────────────────────────
    speak("JARVIS shutting down. Until next time, Boss.")
    print("\n  👋  Goodbye.\n")
    vs.stop()


if __name__ == "__main__":
    run()
