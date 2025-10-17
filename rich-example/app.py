import os
import sys
import threading
import queue
import time
from dataclasses import dataclass
from typing import Optional, List

import numpy as np
import sounddevice as sd
from rich.text import Text
from rich.panel import Panel
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Log, RichLog

from gladiapy.v2 import GladiaWebsocketClient
from gladiapy.v2.ws import InitializeSessionRequest
from gladiapy.v2.ws_models import (
    Transcript,
    Translation,
    PostFinalTranscript,
    LifecycleEvent,
    AudioChunkAcknowledgment,
)


# -------------------- Audio Capture --------------------

@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "int16"  # matches ws: wav/pcm 16-bit
    block_duration: float = 0.125  # seconds per chunk (125ms)


class MicStreamer:
    def __init__(self, q: queue.Queue, cfg: AudioConfig):
        self.q = q
        self.cfg = cfg
        self.stream: Optional[sd.InputStream] = None
        self.paused = threading.Event()
        self.paused.clear()  # not paused initially
        self.running = False

    def _callback(self, indata, frames, time_info, status):
        if status:
            # Push status to queue in case UI wants to show it
            self.q.put(("status", str(status)))
        if self.paused.is_set() or not self.running:
            return
        # Convert to bytes
        data_bytes = indata.tobytes()
        self.q.put(("audio", data_bytes))

    def start(self):
        if self.running:
            return
        self.running = True
        blocksize = int(self.cfg.sample_rate * self.cfg.block_duration)
        self.stream = sd.InputStream(
            channels=self.cfg.channels,
            samplerate=self.cfg.sample_rate,
            dtype=self.cfg.dtype,
            blocksize=blocksize,
            callback=self._callback,
        )
        if self.stream is not None:
            self.stream.start()

    def stop(self):
        self.running = False
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
        finally:
            self.stream = None

    def set_paused(self, p: bool):
        if p:
            self.paused.set()
        else:
            self.paused.clear()


# -------------------- WebSocket Controller --------------------

import time

class WSController:
    def __init__(self, api_key: str, target_lang: str = "en"):
        self.client = GladiaWebsocketClient(api_key)
        self.session = None
        self.target_lang = target_lang
        self.connected = threading.Event()
        self.finished = threading.Event()
        self.lock = threading.Lock()
        self._last_ack = None
        self._last_ack_time = 0.0

    def build_init_request(self) -> InitializeSessionRequest:
        messages_config = InitializeSessionRequest.MessagesConfig(
            receive_final_transcripts=True,
            receive_post_processing_events=True,
            receive_partial_transcripts=True,  # Real-time transcripts
            receive_realtime_processing_events=True,  # Translation events
            receive_speech_events=True,
            receive_lifecycle_events=True,
        )

        # Auto-detect source language: do not set source, only target
        translation_cfg = InitializeSessionRequest.RealtimeProcessing.TranslationConfig(
            model=InitializeSessionRequest.RealtimeProcessing.TranslationConfig.Model.BASE,
            target_languages=[self.target_lang],
            match_original_utterances=True,
            lipsync=False,
        )

        realtime = InitializeSessionRequest.RealtimeProcessing(
            translation=True,
            translation_config=translation_cfg,
        )

        init = InitializeSessionRequest(
            region=InitializeSessionRequest.Region.US_WEST,
            encoding=InitializeSessionRequest.Encoding.WAV_PCM,
            bit_depth=InitializeSessionRequest.BitDepth.BIT_DEPTH_16,
            sample_rate=InitializeSessionRequest.SampleRate.SAMPLE_RATE_16000,
            channels=1,
            model=InitializeSessionRequest.Model.SOLARIA_1,
            endpointing=0.5,  # Wait 0.5s of silence before finalizing (was 0.05)
            maximum_duration_without_endpointing=5,  # Max 5s without speech before endpointing 
            messages_config=messages_config,
            realtime_processing=realtime
        )
        return init

    def connect(self, on_transcript, on_translation, on_status):
        # Prevent creating multiple sessions
        with self.lock:
            if self.session is not None:
                # Try to close previous session before creating a new one
                print("[WSController] WARNING: Previous session exists. Attempting to close it before creating a new one.")
                try:
                    self.session.send_stop_signal()
                    self.session.disconnect()
                    print("[WSController] Previous session closed.")
                except Exception as e:
                    print(f"[WSController] Error closing previous session: {e}")
                self.session = None

            print("[WSController] Creating new session...")
            init = self.build_init_request()
            self.session = self.client.connect(init)
            # Inform about session id
            try:
                info = self.session.get_session_info()
                on_status(f"Session created: {info.get('id')}")
                print(f"[WSController] Session created: {info.get('id')}")
            except Exception:
                print("[WSController] Failed to get session info after creation.")

            # Register/refresh callbacks
            def _connected_cb():
                self.connected.set()
                on_status("Connected")
                print("[WSController] Connected callback triggered.")
            self.session.set_on_connected_callback(_connected_cb)
            self.session.set_on_disconnected_callback(lambda: on_status("Disconnected"))
            self.session.set_on_error_callback(lambda msg: on_status(f"Error: {msg}"))
            self.session.set_on_transcript_callback(on_transcript)
            self.session.set_on_translation_callback(on_translation)

            # Optional: surface acks and lifecycle for diagnostics, too verbose otherwise
            def throttled_ack(a):
                now = time.time()
                ack_val = getattr(a, 'acknowledged', False)
                # Only log if value changes or at least 1s has passed
                if ack_val != self._last_ack or (now - self._last_ack_time) > 1.0:
                    on_status(f"Ack: {ack_val}")
                    self._last_ack = ack_val
                    self._last_ack_time = now
            # self.session.set_on_audio_chunk_acknowledged_callback(throttled_ack)

            self.session.set_on_start_session_callback(lambda e: on_status("Start session"))
            self.session.set_on_start_recording_callback(lambda e: on_status("Start recording"))
            self.session.set_on_end_recording_callback(lambda e: on_status("End recording"))
            self.session.set_on_end_session_callback(lambda e: on_status("Stop session"))

            # Only start the socket thread if we just created the session
            t = getattr(self.session, "_thread", None)
            if self.session and (t is None or not t.is_alive()):
                print("[WSController] Connecting and starting session thread...")
                self.session.connect_and_start()
            else:
                print("[WSController] Session thread already running.")

    def send_audio(self, data: bytes):
        if not self.session:
            return
        # Use binary as ws expects raw pcm frames
        self.session.send_audio_binary(data, len(data))

    def stop_and_close(self):
        try:
            if self.session:
                self.session.send_stop_signal()
        except Exception:
            pass
        finally:
            try:
                if self.session:
                    info = self.session.get_session_info()
                    self.session.disconnect()
                    # Optional: cleanup result
                    sid = info.get("id")
                    if sid:
                        try:
                            self.client.delete_result(sid)
                        except Exception:
                            pass
            finally:
                self.session = None


# -------------------- Textual UI --------------------

class StatusBar(Static):
    text = reactive("Idle")
    level = reactive(0.0)
    paused = reactive(False)
    lang = reactive("en")

    def watch_text(self, value: str):
        self._update_display()
    
    def watch_level(self, value: float):
        self._update_display()
    
    def watch_paused(self, value: bool):
        self._update_display()
    
    def watch_lang(self, value: str):
        self._update_display()
    
    def _update_display(self):
        # Display level as simple bar
        bar_len = 40
        filled = min(bar_len, int(self.level * bar_len))
        bar = "█" * filled + "─" * (bar_len - filled)
        mic_level = f"Mic: [{bar}]"
        
        full_text = f"{self.text} | {mic_level}"
        self.update(Panel(Text(full_text), title=f"Status | Lang: {self.lang} | {'Paused' if self.paused else 'Live'}"))

    def set_level(self, rms: float):
        self.level = rms


class TranscriptPane(RichLog):
    def add_text(self, is_final: bool, lang: str, text: str):
        if not is_final:
            self.write(Text.from_markup(f"[bold cyan][PARTIAL] {lang} - {text}[/]"))
        else:
            self.write(Text.from_markup(f"[bold green][FINAL] {lang} - {text}[/]"))


    def clear_all(self):
        self.clear()


class TranslationPane(RichLog):
    def add_translation(self, text: str, original_lang: str, lang: str):
        self.write(Text.from_markup(f"[magenta]{original_lang} -> {lang} : {text}[/]"))

    def clear_all(self):
        self.clear()


class EventLog(RichLog):
    pass


import queue

class GladiaRichApp(App):
    CSS_PATH = None
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("space", "toggle_pause", "Pause/Resume"),
        Binding("enter", "finalize", "Finalize"),
        Binding("c", "clear", "Clear"),
    ]

    def __init__(self):
        super().__init__()
        self.audio_cfg = AudioConfig()
        self.audio_q: queue.Queue = queue.Queue()
        self.rms_q: queue.Queue = queue.Queue(maxsize=5)
        self.mic = MicStreamer(self.audio_q, self.audio_cfg)
        self.ws: Optional[WSController] = None
        self._sender_thread: Optional[threading.Thread] = None
        self._running = False
        self.current_lang = "en"  # Only used for target, not toggled
        # Track the UI thread id so we can safely decide when to call call_from_thread
        self._app_thread_ident: Optional[int] = None

    # Helper: ensure UI updates run on the UI thread without misusing call_from_thread
    def _to_ui(self, func, *args, **kwargs):
        try:
            if self._app_thread_ident is not None and threading.get_ident() == self._app_thread_ident:
                # Already on UI thread; call directly
                func(*args, **kwargs)
            else:
                # Background thread; schedule on UI thread
                self.call_from_thread(func, *args, **kwargs)
        except Exception:
            # As a last resort, avoid crashing the background thread
            try:
                func(*args, **kwargs)
            except Exception:
                pass

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            self.status = StatusBar()
            yield self.status
            with Horizontal():
                self.transcript = TranscriptPane(id="transcript")
                yield self.transcript
                self.translation = TranslationPane(id="translation")
                yield self.translation
            self.events = EventLog(id="events")
            yield self.events
        yield Footer()

    def on_mount(self):
        # Start heavy init in a background thread to keep UI responsive
        # Record the UI thread ident for safe UI dispatching
        self._app_thread_ident = threading.get_ident()
        threading.Thread(target=self._start_services, daemon=True).start()
        # Periodically update mic level in status bar from RMS queue
        self.set_interval(0.05, self._update_mic_level)

    def _start_services(self):
        api_key = os.getenv("GLADIA_API_KEY")
        if not api_key:
            self._to_ui(setattr, self.status, "text", "No API key. Set GLADIA_API_KEY.")
            return
        self._to_ui(setattr, self.status, "lang", self.current_lang)
        self._to_ui(setattr, self.status, "text", "Starting microphone...")

        # Start mic
        try:
            self.mic.start()
            self._to_ui(lambda: self.events.write(Text.from_markup("[green]Microphone started[/]")))
        except Exception as e:
            self._to_ui(setattr, self.status, "text", f"Mic error: {e}")
            self._to_ui(lambda: self.events.write(Text.from_markup(f"[red]Mic error: {e}[/]")))
            return

        self._to_ui(setattr, self.status, "text", "Connecting WebSocket...")

        # Connect WS
        self.ws = WSController(api_key, target_lang=self.current_lang)
        def _on_transcript(t: Transcript):
            try:
                self._to_ui(self._on_transcript, t)
            except Exception as ex:
                print("Transcript error:", ex)


        def _on_translation(tr: Translation):
            try:
                self._to_ui(self._on_translation, tr)
            except Exception as ex:
                print("Translation error:", ex)
                self._to_ui(lambda: self.events.write(Text.from_markup(f"[red]Translation error: {ex}[/]")))

        def _on_status(msg: str):
            self._to_ui(lambda: self.events.write(Text.from_markup(f"[yellow]{msg}[/]")))
            self._to_ui(setattr, self.status, "text", msg)

        try:
            self.ws.connect(_on_transcript, _on_translation, _on_status)
        except Exception as e:
            self._to_ui(setattr, self.status, "text", f"WS error: {e}")
            self._to_ui(lambda: self.events.write(Text.from_markup(f"[red]WS error: {e}[/]")))
            return

        self._running = True
        # Ensure connection confirmed before streaming
        self._sender_thread = threading.Thread(target=self._audio_sender_loop, daemon=True)
        self._sender_thread.start()

    def on_unmount(self):
        self._cleanup_resources()

    def _cleanup_resources(self):
        self._running = False
        try:
            self.mic.stop()
        except Exception:
            pass
        try:
            if self.ws:
                self.ws.stop_and_close()
        except Exception:
            pass

    def _audio_sender_loop(self):
        # Consume audio queue and send audio frames; push RMS to rms_q for UI update
        window: List[float] = []
        max_window = 5
        self._to_ui(lambda: self.events.write(Text.from_markup("[blue]Audio sender loop started[/]")))
        while self._running:
            try:
                kind, payload = self.audio_q.get(timeout=0.2)
            except queue.Empty:
                continue
            if kind == "status":
                self._to_ui(lambda: self.events.write(Text.from_markup(f"[yellow]Audio: {payload}[/]")))
                continue
            if kind != "audio":
                continue
            data: bytes = payload
            
            # Calculate RMS ALWAYS (regardless of WS connection state)
            try:
                arr = np.frombuffer(data, dtype=np.int16)
                rms = float(np.sqrt(np.mean(np.square(arr)))) / 60.0
                window.append(rms)
                if len(window) > max_window:
                    window.pop(0)
                avg = sum(window) / len(window)
                # Push to RMS queue for UI thread
                if not self.rms_q.full():
                    self.rms_q.put(avg)
            except Exception as e:
                self._to_ui(lambda e=e: self.events.write(Text.from_markup(f"[red]RMS Error: {e}[/]")))
            
            # Only send audio to WS if connected
            if self.ws and self.ws.connected.is_set():
                try:
                    self.ws.send_audio(data)
                except Exception as e:
                    #self.call_from_thread(lambda: self.events.write(Text.from_markup(f"[red]Send error: {e}[/]")))
                    self.exit(message=f"Send error: {e}")
                    break

    def _update_mic_level(self):
        # Periodically update status bar with latest RMS from queue
        try:
            count = 0
            while not self.rms_q.empty():
                rms = self.rms_q.get_nowait()
                self.status.set_level(rms)
                count += 1

        except Exception as e:
            # self.events.write(Text.from_markup(f"[red]Level update error: {e}[/]"))
            pass

    # -------------------- Actions --------------------
    def action_quit(self):
        self._cleanup_resources()
        self.exit()

    def action_toggle_pause(self):
        new_state = not self.mic.paused.is_set()
        self.mic.set_paused(new_state)
        self.status.paused = new_state
        self.status.text = "Paused" if new_state else "Live"

    def action_finalize(self):
        # Send a stop signal to let server finalize current buffers
        if self.ws and self.ws.session:
            try:
                self.ws.session.send_stop_signal()
                self.events.write(Text.from_markup("[green]Sent stop signal[/]"))
            except Exception as e:
                self.events.write(Text.from_markup(f"[red]Stop error: {e}[/]"))

    def action_clear(self):
        self.transcript.clear_all()
        self.translation.clear_all()
        self.events.clear()

    def _on_transcript(self, transcript: Transcript):
        try:
            text = (transcript.data.utterance.text or "").strip()
            lang = transcript.data.utterance.language or "?"
            self.transcript.add_text(transcript.data.is_final,lang, text)
        except Exception as ex:
            # Already on UI thread in normal flow; log directly to avoid call_from_thread misuse
            self.events.write(Text.from_markup(f"[red]Partial error: {ex}[/]"))


    def _on_translation(self, translation: Translation):
        try:
            if translation.data is not None:
                translations = translation.data.translated_utterance
                self.translation.add_translation(translations.text, translation.data.original_language, translations.language)
            else:
                self.translation.add_translation("?", "?", "[No translation data]")
        except Exception as ex:
            self.events.write(Text.from_markup(f"[red]Translation error: {ex}[/]"))


# -------------------- Entrypoint --------------------
if __name__ == "__main__":
    GladiaRichApp().run()
