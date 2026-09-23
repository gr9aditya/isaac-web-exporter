"""Thin, responsive Kit panel for the shared Isaac Web Exporter core.

Exports run in an isolated Isaac Python child process. This lets Kit continue
to repaint and process cancellation while the capture/converter advances.
"""

import asyncio
import functools
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

import omni.ext
import omni.ui as ui
import omni.usd
import omni.kit.app


class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._process = None
        self._task = None
        self._temporary = None
        self._httpd = None
        self._preview_thread = None
        self._last_output = None
        self._cancel_requested = False
        self._window = ui.Window("Isaac Replay Exporter", width=450, height=690)
        with self._window.frame:
            with ui.VStack(spacing=8):
                ui.Label("Recorded playback export", height=24)
                ui.Label("Source .usd/.usda or Python bootstrap")
                self.source = ui.StringField()
                ui.Label("Leave source empty to snapshot the loaded stage")
                ui.Label("Selected root prims (comma-separated; blank = /World)")
                self.roots = ui.StringField()
                self.roots.model.set_value("/World")
                ui.Label("Duration (seconds)")
                self.duration = ui.FloatField()
                self.duration.model.set_value(5.0)
                ui.Label("Samples per second")
                self.fps = ui.IntField()
                self.fps.model.set_value(30)
                ui.Label("Quality preset: standard or compact")
                self.quality = ui.StringField()
                self.quality.model.set_value("standard")
                ui.Label("Output directory (must not exist)")
                self.output = ui.StringField()
                self.output.model.set_value(str(Path.home() / "isaac-replay-export"))
                self.static = ui.CheckBox()
                ui.Label("Static scene mode", height=20)
                with ui.HStack(height=32):
                    ui.Button("Preflight", clicked_fn=self._preflight_clicked)
                    ui.Button("Save preset", clicked_fn=self._save_preset)
                    ui.Button("Load preset", clicked_fn=self._load_preset)
                with ui.HStack(height=32):
                    ui.Button("Record + export", clicked_fn=self._start_clicked)
                    ui.Button("Cancel", clicked_fn=self._cancel_clicked)
                    ui.Button("Preview", clicked_fn=self._preview_clicked)
                self.status = ui.Label("Ready", word_wrap=True, height=60)
                self.progress = ui.ProgressBar(height=16)
                self.progress.model.set_value(0.0)
                ui.Label("The ZIP is created beside the package folder.", word_wrap=True)

    def on_shutdown(self):
        self._cancel_clicked()
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
        self._window = None

    def _value(self, field):
        return field.model.get_value_as_string().strip()

    def _configuration(self):
        version = omni.kit.app.get_app().get_app_version()
        if not str(version).startswith("6.1"):
            raise RuntimeError(f"Isaac Sim 6.1 is required; running {version}")
        source = self._value(self.source)
        output = Path(self._value(self.output)).expanduser().resolve()
        if not str(output) or output.exists():
            raise ValueError(f"Output directory already exists or is empty: {output}")
        fps = self.fps.model.get_value_as_int()
        duration = self.duration.model.get_value_as_float()
        if fps < 1 or duration <= 0:
            raise ValueError("FPS and duration must be positive")
        quality = self._value(self.quality)
        if quality not in ("standard", "compact"):
            raise ValueError("Quality preset must be standard or compact")
        roots = [item.strip() for item in self._value(self.roots).split(",") if item.strip()]
        if not all(root.startswith("/") for root in roots):
            raise ValueError("Selected roots must be absolute prim paths")
        configuration = {
            "output_dir": str(output), "duration_seconds": duration, "fps": fps,
            "sample_every_updates": 1, "simulation_hz": fps,
            "capture_roots": roots or ["/World"], "quality_preset": quality,
        }
        if self.static.model.get_value_as_bool():
            configuration["mode"] = "static"
            configuration["capture_roots"] = []
        if source:
            path = Path(source).expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError(f"Source file not found: {path}")
            if path.suffix.lower() == ".py":
                configuration["bootstrap"] = str(path)
            else:
                configuration["input_usd"] = str(path)
                configuration["capture_roots"] = []
        else:
            stage = omni.usd.get_context().get_stage()
            if stage is None or not stage.GetPseudoRoot().GetChildren():
                raise ValueError("No loaded stage to snapshot")
            configuration["_snapshot_loaded_stage"] = True
        return configuration

    def _preflight_clicked(self):
        try:
            config = self._configuration()
            self.status.text = ("Preflight passed: " +
                                ("loaded stage" if config.get("_snapshot_loaded_stage") else
                                 config.get("bootstrap", config.get("input_usd"))))
        except Exception as error:
            self.status.text = f"Preflight failed: {error}"

    @staticmethod
    def _preset_path():
        return Path.home() / ".config" / "isaac-web-exporter" / "panel-preset.json"

    def _save_preset(self):
        try:
            config = self._configuration()
            path = self._preset_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(config, indent=2), encoding="utf-8")
            self.status.text = f"Preset saved: {path}"
        except Exception as error:
            self.status.text = f"Cannot save preset: {error}"

    def _load_preset(self):
        try:
            config = json.loads(self._preset_path().read_text(encoding="utf-8"))
            self.source.model.set_value(config.get("bootstrap", config.get("input_usd", "")))
            self.output.model.set_value(config["output_dir"])
            self.roots.model.set_value(", ".join(config.get("capture_roots", ["/World"])))
            self.duration.model.set_value(float(config["duration_seconds"]))
            self.fps.model.set_value(int(config["fps"]))
            self.quality.model.set_value(config.get("quality_preset", "standard"))
            self.static.model.set_value(config.get("mode") == "static")
            self.status.text = "Preset loaded"
        except Exception as error:
            self.status.text = f"Cannot load preset: {error}"

    def _start_clicked(self):
        if self._process and self._process.poll() is None:
            self.status.text = "An export is already running"
            return
        try:
            self._cancel_requested = False
            config = self._configuration()
            self._temporary = tempfile.TemporaryDirectory(prefix="isaac-replay-panel-")
            temporary = Path(self._temporary.name)
            if config.pop("_snapshot_loaded_stage", False):
                snapshot = temporary / "loaded-stage.usda"
                stage = omni.usd.get_context().get_stage()
                if not stage.Export(str(snapshot)):
                    raise RuntimeError("Loaded stage snapshot failed")
                config["input_usd"] = str(snapshot)
                config["capture_roots"] = []
            config_path = temporary / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            self._last_output = Path(config["output_dir"])
            self._log_file = (temporary / "export.log").open("w", encoding="utf-8")
            self._process = subprocess.Popen(
                [sys.executable, "-m", "isaac_web_exporter.export", "--config", str(config_path)],
                stdout=self._log_file, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            self.status.text = "Starting isolated Isaac export…"
            self.progress.model.set_value(0.0)
            self._task = asyncio.ensure_future(self._watch_export())
        except Exception as error:
            self.status.text = f"Export could not start: {error}"
            if self._temporary:
                self._temporary.cleanup()
                self._temporary = None

    async def _watch_export(self):
        try:
            while self._process and self._process.poll() is None:
                progress = self._last_output / "progress.json"
                if progress.is_file():
                    try:
                        data = json.loads(progress.read_text(encoding="utf-8"))
                        self.status.text = data.get("detail", "Exporting")
                        self.progress.model.set_value(float(data.get("fraction", 0)))
                    except (OSError, ValueError, KeyError):
                        pass
                await asyncio.sleep(0.1)
            if self._process:
                report = self._last_output / "report.json"
                result = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else {}
                if self._cancel_requested:
                    self.status.text = "Export cancelled; no completed package was published"
                elif self._process.returncode == 0 and result.get("status") == "success":
                    self.status.text = f"Ready: {self._last_output / 'package.zip'}"
                    self.progress.model.set_value(1.0)
                else:
                    self.status.text = ("Export failed: " +
                                        "; ".join(result.get("errors", []))[:300])
        finally:
            if getattr(self, "_log_file", None):
                self._log_file.close()
            if self._temporary:
                self._temporary.cleanup()
                self._temporary = None

    def _cancel_clicked(self):
        if self._process and self._process.poll() is None:
            self._cancel_requested = True
            self._process.terminate()
            self.status.text = "Cancelling export…"

    def _preview_clicked(self):
        package = self._last_output / "package" if self._last_output else None
        if package is None or not (package / "index.html").is_file():
            self.status.text = "No validated package to preview"
            return
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(package))
        self._httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._preview_thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._preview_thread.start()
        url = f"http://127.0.0.1:{self._httpd.server_port}/"
        self.status.text = f"Local preview: {url}"
        webbrowser.open(url)
