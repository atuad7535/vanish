"""Tests for the sounds module."""

import os
import tempfile
from unittest.mock import patch, MagicMock

from vanish.sounds import _strip_for_tts, _generate_chime, _escape_ps, speak, play_chime


class TestStripForTTS:
    def test_removes_rich_markup(self):
        assert "hello world" == _strip_for_tts("[bold]hello[/bold] [green]world[/green]")

    def test_removes_emoji(self):
        cleaned = _strip_for_tts("poof 💀 gone ✨ nice")
        assert "💀" not in cleaned
        assert "✨" not in cleaned
        assert "poof" in cleaned
        assert "gone" in cleaned

    def test_plain_text_unchanged(self):
        assert "vanish freed 500 MB" == _strip_for_tts("vanish freed 500 MB")


class TestGenerateChime:
    def test_creates_wav_file(self):
        path = _generate_chime()
        assert path is not None
        assert os.path.exists(path)
        assert path.endswith(".wav")
        assert os.path.getsize(path) > 0

    def test_wav_is_valid(self):
        import wave
        path = _generate_chime()
        with wave.open(path, 'r') as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 22050
            assert wf.getnframes() > 0


class TestEscapePS:
    def test_double_quotes(self):
        assert _escape_ps('say "hello"') == 'say `"hello`"'

    def test_single_quotes(self):
        assert _escape_ps("it's fine") == "it`'s fine"


class TestSpeakDoesNotCrash:
    @patch("vanish.sounds.subprocess.Popen")
    def test_speak_calls_popen_on_darwin(self, mock_popen):
        with patch("vanish.sounds._system", return_value="darwin"):
            speak("test message")
            mock_popen.assert_called_once()

    @patch("vanish.sounds.subprocess.Popen")
    def test_speak_with_voice(self, mock_popen):
        with patch("vanish.sounds._system", return_value="darwin"):
            speak("hello", voice="Samantha")
            args = mock_popen.call_args[0][0]
            assert "-v" in args
            assert "Samantha" in args

    @patch("vanish.sounds._system", return_value="linux")
    @patch("vanish.sounds._which", return_value=None)
    def test_speak_linux_no_espeak(self, mock_which, mock_sys):
        speak("test message")

    @patch("vanish.sounds.subprocess.Popen", side_effect=Exception("boom"))
    def test_speak_swallows_exceptions(self, mock_popen):
        with patch("vanish.sounds._system", return_value="darwin"):
            speak("should not crash")


class TestPlayChimeDoesNotCrash:
    @patch("vanish.sounds.subprocess.Popen")
    def test_play_chime_on_darwin(self, mock_popen):
        with patch("vanish.sounds._system", return_value="darwin"):
            play_chime()
            mock_popen.assert_called_once()

    @patch("vanish.sounds._system", return_value="linux")
    @patch("vanish.sounds._which", return_value=None)
    def test_play_chime_linux_no_player(self, mock_which, mock_sys):
        play_chime()
