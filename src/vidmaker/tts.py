from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import subprocess

from .models import TTSSettings


@dataclass(frozen=True)
class ProviderStatus:
    available: bool
    detail: str


class TextToSpeechProvider:
    name: str

    def check_availability(self) -> ProviderStatus:
        raise NotImplementedError

    def synthesize(self, text: str, destination: Path, settings: TTSSettings) -> None:
        raise NotImplementedError


class WindowsSapiProvider(TextToSpeechProvider):
    name = "windows_sapi"

    def check_availability(self) -> ProviderStatus:
        if platform.system() != "Windows":
            return ProviderStatus(False, "Windows SAPI is only available on Windows.")
        try:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "-"],
                input=(
                    "Add-Type -AssemblyName System.Speech\n"
                    "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
                    "$voices = $synth.GetInstalledVoices()\n"
                    "if ($voices.Count -gt 0) { Write-Output ($voices[0].VoiceInfo.Name) }\n"
                ),
                text=True,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError:
            return ProviderStatus(False, "PowerShell is not installed.")
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip() or "PowerShell exited with an error."
            return ProviderStatus(False, stderr)
        first_voice = completed.stdout.strip() or "Windows SAPI voices detected."
        return ProviderStatus(True, f"Windows SAPI available ({first_voice}).")

    def synthesize(self, text: str, destination: Path, settings: TTSSettings) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        script = "\n".join(
            [
                "Add-Type -AssemblyName System.Speech",
                "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer",
                f"$synth.Rate = {settings.rate}",
                f"$synth.Volume = {settings.volume}",
                *( [f"$synth.SelectVoice('{_ps_string(settings.voice)}')"] if settings.voice else [] ),
                f"$synth.SetOutputToWaveFile('{_ps_string(str(destination))}')",
                f"$synth.Speak('{_ps_string(text)}')",
                "$synth.Dispose()",
            ]
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "-"],
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip() or "Unknown TTS failure."
            raise RuntimeError(f"Windows SAPI synthesis failed: {stderr}")


def resolve_tts_provider(name: str) -> ProviderStatus:
    provider = create_tts_provider(name)
    if provider is None:
        return ProviderStatus(False, f"Unknown provider '{name}'.")
    return provider.check_availability()


def create_tts_provider(name: str) -> TextToSpeechProvider | None:
    if name == "windows_sapi":
        return WindowsSapiProvider()
    return None


def _ps_string(value: str) -> str:
    return value.replace("'", "''")
