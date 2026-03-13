"""
main.py  –  J.A.R.V.I.S  Personal Assistant
─────────────────────────────────────────────────
Usage:
    python main.py          # text mode (default)
    python main.py --voice  # start in voice mode
─────────────────────────────────────────────────
Commands inside the app:
    voice       – toggle voice input on/off
    clear       – clear conversation memory
    quit/exit   – shut down JARVIS
"""
import argparse
import sys
import time
from datetime import datetime

try:
    # Running as a script: python jarvis/main.py
    from brain import chat
    from voice import VOICE_ERROR, listen, speak, start_background_listening
except ImportError:
    # Running as a module: python -m jarvis.main
    from .brain import chat
    from .voice import VOICE_ERROR, listen, speak, start_background_listening

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
  ║  Commands:  voice | clear | quit                         ║
  ╚══════════════════════════════════════════════════════════╝
"""


def run() -> None:
    parser = argparse.ArgumentParser(description="JARVIS Personal Assistant")
    parser.add_argument("--voice", action="store_true", help="Start in voice mode")
    args = parser.parse_args()

    print(BANNER)

    history: list[dict] = []
    voice_mode = args.voice

    now = datetime.now().strftime("%A, %B %d  %I:%M %p")
    greeting = (
        f"Good day, Boss. JARVIS is online. "
        f"Today is {now}. All systems nominal. How can I assist?"
    )
    speak(greeting)
    print("\n  Type 'talk' to speak to JARVIS  |  'quit' to exit\n")
    print("─" * 62)

    bg_queue = None
    bg_stop = None
    listen_fallback = False

    while True:
        try:
            if voice_mode:
                # Try to use a background listener (best experience) and fall
                # back to a direct listen() call if unavailable.
                if not listen_fallback and (bg_queue is None or bg_stop is None):
                    bg_queue, bg_stop, err = start_background_listening()
                    if err:
                        print(f"  ⚠️  {err}")
                        print("  → Falling back to direct speech capture (no ENTER required).")
                        listen_fallback = True
                        bg_queue = None
                        bg_stop = None
                    else:
                        listen_fallback = False
                        speak("Voice mode on.")
                        print("\n  Listening… (say 'voice' to switch to text, 'quit' to exit)")
                        time.sleep(0.2)
                        continue

                if listen_fallback:
                    user_input = listen()
                    if user_input == VOICE_ERROR:
                        print("  ⚠️  Voice input failed (mic/STT not available). Switching to text mode.")
                        voice_mode = False
                        listen_fallback = False
                        continue
                    if not user_input:
                        continue
                else:
                    try:
                        user_input = bg_queue.get_nowait()
                    except Exception:
                        time.sleep(0.1)
                        continue
                    if not user_input:
                        continue

                if user_input.lower() in ("quit", "exit"):
                    break
                if user_input.lower() == "clear":
                    history.clear()
                    speak("Memory cleared.")
                    continue
                if user_input.lower() == "voice":
                    voice_mode = False
                    listen_fallback = False
                    try:
                        if bg_stop is not None:
                            bg_stop()
                    except Exception:
                        pass
                    bg_queue = None
                    bg_stop = None
                    speak("Text mode on.")
                    print("  → Switched to text mode.")
                    continue

            else:
                print("\nYou ▶  ", end="", flush=True)
                user_input = input().strip()
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit"):
                    break
                if user_input.lower() == "clear":
                    history.clear()
                    speak("Memory cleared.")
                    continue
                if user_input.lower() in ("list mics", "mics", "microphones"):
                    try:
                        from voice import list_microphones
                        names = list_microphones()
                        print("Available microphones:")
                        for idx, name in enumerate(names, start=1):
                            print(f"  {idx}. {name}")
                    except Exception as e:
                        print(f"Error listing mics: {e}")
                    continue
                if user_input.lower() == "voice":
                    voice_mode = True
                    bg_queue = None
                    bg_stop = None
                    listen_fallback = False
                    continue
                if user_input.lower() == "talk":
                    user_input = listen()
                    if user_input == VOICE_ERROR:
                        print("  ⚠️  Voice input failed (mic/STT not available).")
                        continue
                    if not user_input:
                        continue
                    print(f"You (speech): {user_input}")

            print("  ⚡  Thinking…", flush=True)
            history.append({"role": "user", "content": user_input})
            response, history = chat(history)
            speak(response)

            if len(history) > 30:
                history = history[-30:]

        except KeyboardInterrupt:
            print("\n\n  ⚠️  Interrupted.")
            speak("Emergency shutdown, Boss. Goodbye.")
            sys.exit(0)
        except Exception as exc:
            print(f"\n  ❌  Error: {exc}")
            speak("I encountered an error, Boss. Check the terminal for details.")

    speak("JARVIS shutting down. Until next time, Boss.")
    print("\n  👋  Goodbye.\n")

    if bg_stop is not None:
        try:
            bg_stop()
        except Exception:
            pass


if __name__ == "__main__":
    run()
