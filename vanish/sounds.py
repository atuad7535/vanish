"""Sound effects and text-to-speech for vanish notifications.

Cross-platform:
  - macOS: `afplay` (MP3/WAV, built-in) + `say` TTS
  - Linux: `ffplay`/`mpv`/`aplay` + `espeak` TTS
  - Windows: PowerShell MediaPlayer + SpeechSynthesizer (built-in Win10+)

Bundles a FAHHH.mp3 sound effect in vanish/assets/.
Falls back to a generated chime if the asset is missing.
"""

import os
import platform
import struct
import math
import wave
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

_ASSETS_DIR = Path(__file__).parent / "assets"
_FAHHH_MP3 = _ASSETS_DIR / "fahhh.mp3"


def _system() -> str:
    return platform.system().lower()


def speak(text: str, voice: Optional[str] = None):
    """Speak text out loud using the OS text-to-speech engine."""
    system = _system()
    clean = _strip_for_tts(text)

    try:
        if system == "darwin":
            cmd = ["say", "-r", "195"]
            if voice:
                cmd += ["-v", voice]
            cmd.append(clean)
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        elif system == "linux":
            espeak = _which("espeak") or _which("espeak-ng")
            if espeak:
                subprocess.Popen(
                    [espeak, clean],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )

        elif system == "windows":
            ps_script = (
                f'Add-Type -AssemblyName System.Speech; '
                f'(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{_escape_ps(clean)}")'
            )
            subprocess.Popen(
                ["powershell", "-Command", ps_script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass


def play_fahhh(wait: bool = True):
    """Play the bundled FAHHH sound, falling back to a generated chime."""
    sound_path = str(_FAHHH_MP3) if _FAHHH_MP3.exists() else _generate_chime()
    if not sound_path:
        return

    system = _system()
    is_mp3 = sound_path.endswith(".mp3")

    try:
        if system == "darwin":
            p = subprocess.Popen(
                ["afplay", sound_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if wait:
                p.wait()

        elif system == "linux":
            if is_mp3:
                player = (_which("ffplay") or _which("mpv") or
                          _which("cvlc") or _which("paplay"))
                if player and "ffplay" in player:
                    cmd = [player, "-nodisp", "-autoexit", sound_path]
                elif player and "mpv" in player:
                    cmd = [player, "--no-video", sound_path]
                elif player and "cvlc" in player:
                    cmd = [player, "--play-and-exit", sound_path]
                elif player:
                    cmd = [player, sound_path]
                else:
                    return
            else:
                player = _which("paplay") or _which("aplay")
                if not player:
                    return
                cmd = [player, sound_path]

            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if wait:
                p.wait()

        elif system == "windows":
            if is_mp3:
                ps_script = (
                    f'Add-Type -AssemblyName PresentationCore; '
                    f'$p = New-Object System.Windows.Media.MediaPlayer; '
                    f'$p.Open([Uri]"{sound_path}"); '
                    f'$p.Play(); Start-Sleep -Milliseconds 3000'
                )
                p = subprocess.Popen(
                    ["powershell", "-Command", ps_script],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                if wait:
                    p.wait()
            else:
                import winsound
                flag = winsound.SND_FILENAME
                if not wait:
                    flag |= winsound.SND_ASYNC
                winsound.PlaySound(sound_path, flag)
    except Exception:
        pass


# Keep old name as alias for backward compat
play_chime = play_fahhh


def _generate_chime() -> Optional[str]:
    """Fallback: generate a short ascending 3-note chime as a .wav temp file."""
    try:
        sample_rate = 22050
        duration_per_note = 0.12
        freqs = [523.25, 659.25, 783.99]  # C5, E5, G5

        samples = []
        for freq in freqs:
            n_samples = int(sample_rate * duration_per_note)
            for i in range(n_samples):
                t = i / sample_rate
                envelope = 1.0 - (i / n_samples)
                val = envelope * math.sin(2.0 * math.pi * freq * t)
                samples.append(int(val * 16000))

        path = os.path.join(tempfile.gettempdir(), "vanish_chime.wav")
        with wave.open(path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        return path
    except Exception:
        return None


def _strip_for_tts(text: str) -> str:
    """Remove emoji and Rich markup so TTS reads cleanly."""
    import re
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF\u2600-\u26FF\u2700-\u27BF\U0001FA00-\U0001FA6F'
        r'\U0001FA70-\U0001FAFF\u200d\ufe0f]+', '', text
    )
    return text.strip()


def _escape_ps(text: str) -> str:
    """Escape text for PowerShell string embedding."""
    return text.replace('"', '`"').replace("'", "`'")


def _which(cmd: str) -> Optional[str]:
    import shutil
    return shutil.which(cmd)
