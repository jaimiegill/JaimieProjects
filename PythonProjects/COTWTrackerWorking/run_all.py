"""Run the COTW data-processing scripts in sequence with a loading window."""

from __future__ import annotations

import subprocess
import sys
import queue
import re
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
STEPS = (
    "Build_COTW_Archive_Index.py",
    "Extract_Static_COTW_Catalog.py",
    "Animal_pop_decode.py",
    "ADF_Reader.py",
    "ADF_Reader_Need_Zone.py",
    "Output_Results_to_table.py",
    "Need_Zone_Table_Conversion_txt.py",
    "COTW_Mapper4.0.py",
)
PRE_MAPPER_STEPS = STEPS[:-1]


class LoadingWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.spinner_frames = ("|", "/", "-", "\\")
        self.spinner_index = 0
        self.process_thread = threading.Thread(
            target=self._run_pre_mapper_steps,
            daemon=True,
        )

        root.title("COTW Tracker")
        root.geometry("520x230")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self._close)

        frame = ttk.Frame(root, padding=28)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text="Preparing COTW Tracker",
            font=("Segoe UI", 15, "bold"),
        ).pack(pady=(0, 18))
        self.spinner_label = ttk.Label(
            frame,
            text="|",
            font=("Consolas", 24, "bold"),
        )
        self.spinner_label.pack()
        self.status_label = ttk.Label(frame, text="Starting...", anchor="center")
        self.status_label.pack(fill="x", pady=(10, 0))
        self.progress_bar = ttk.Progressbar(
            frame,
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )
        self.progress_bar.pack(fill="x", pady=(14, 0))
        self.progress_label = ttk.Label(frame, text="0%", anchor="center")
        self.progress_label.pack(pady=(5, 0))

        self._animate_spinner()
        self._poll_events()
        self.process_thread.start()

    def _animate_spinner(self) -> None:
        self.spinner_label.configure(
            text=self.spinner_frames[self.spinner_index % len(self.spinner_frames)]
        )
        self.spinner_index += 1
        self.root.after(120, self._animate_spinner)

    def _run_pre_mapper_steps(self) -> None:
        try:
            for number, script_name in enumerate(PRE_MAPPER_STEPS, start=1):
                script_path = SCRIPT_DIR / script_name
                if not script_path.is_file():
                    raise FileNotFoundError(f"Missing step: {script_path}")

                self.events.put(
                    ("status", f"Step {number}/{len(STEPS)}: {script_name}")
                )
                self.events.put(
                    ("progress", ((number - 1) / len(PRE_MAPPER_STEPS)) * 100)
                )
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    cwd=SCRIPT_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                if process.stdout is not None:
                    for output_line in process.stdout:
                        output_line = output_line.strip()
                        if not output_line:
                            continue
                        print(f"[{script_name}] {output_line}", flush=True)
                        progress_match = re.search(
                            r"Completed\s+(\d+)\s+of\s+(\d+)",
                            output_line,
                            re.IGNORECASE,
                        )
                        if progress_match:
                            completed = int(progress_match.group(1))
                            total = int(progress_match.group(2))
                            fraction = completed / total if total else 0
                            progress = (
                                (number - 1 + fraction)
                                / len(PRE_MAPPER_STEPS)
                                * 100
                            )
                            self.events.put(("progress", progress))
                        self.events.put(
                            ("status", f"{script_name}: {output_line[-75:]}")
                        )

                return_code = process.wait()
                if return_code != 0:
                    raise RuntimeError(
                        f"{script_name} failed with exit code {return_code}"
                    )
                self.events.put(
                    ("progress", (number / len(PRE_MAPPER_STEPS)) * 100)
                )

            self.events.put(("complete", None))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _poll_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "status":
                    self.status_label.configure(text=str(value))
                elif event == "progress":
                    progress = max(0.0, min(100.0, float(value)))
                    self.progress_bar.configure(value=progress)
                    self.progress_label.configure(text=f"{progress:.1f}%")
                elif event == "complete":
                    self._launch_mapper()
                    return
                elif event == "error":
                    self.status_label.configure(text=f"Error: {value}")
                    self.spinner_label.configure(text="!")
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _launch_mapper(self) -> None:
        mapper_path = SCRIPT_DIR / STEPS[-1]
        self.root.destroy()
        subprocess.Popen([sys.executable, str(mapper_path)], cwd=SCRIPT_DIR)

    def _close(self) -> None:
        if self.process_thread.is_alive():
            return
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    LoadingWindow(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
