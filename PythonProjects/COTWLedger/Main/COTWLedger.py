from __future__ import annotations

import tkinter as tk
from customtkinter import CTk, CTkLabel, CTkProgressBar, set_appearance_mode


class LoadingScreen:
    def __init__(self, root: CTk) -> None:
        self.root = root
        self.root.title("COTW Ledger")
        self.root.geometry("700x420")
        self.root.resizable(False, False)
        self.root.configure(fg_color="#18191c")

        self.messages = [
            "Tracking field entries...",
            "Checking trail totals...",
            "Reviewing cache data...",
            "Preparing your camp ledger...",
        ]

        self.status_index = 0
        self.progress_value = 0.0
        self.spinner_angle = 0
        self._last_step = -1

        # --- Canvas Background Elements ---
        self.bg = tk.Canvas(root, width=700, height=420, bg="#18191c", highlightthickness=0)
        self.bg.place(x=0, y=0)

        # Main container card (Dark slate container)
        self.bg.create_rectangle(30, 30, 670, 390, fill="#212429", outline="#2d3138", width=1)

        # Center Hero Card with COTW's signature orange accent border
        self.bg.create_rectangle(180, 50, 520, 160, fill="#ffffff", outline="#ff9600", width=3)

        # --- Labels ---
        # Main Title (Inside the white hero card)
        self.logo = CTkLabel(
            root,
            text="COTW LEDGER",
            font=("Impact", 28),
            text_color="#111315",
            bg_color="#ffffff",
        )
        self.logo.place(relx=0.5, rely=0.21, anchor="center")

        # Tagline inside hero card
        self.tag = CTkLabel(
            root,
            text="WILDERNESS OVERVIEW",
            font=("Trebuchet MS", 10, "bold"),
            text_color="#555960",
            bg_color="#ffffff",
        )
        self.tag.place(relx=0.5, rely=0.31, anchor="center")

        # --- Spinner Canvas ---
        self.spinner_canvas = tk.Canvas(
            root,
            width=80,
            height=80,
            bg="#212429",
            highlightthickness=0,
        )
        self.spinner_canvas.place(relx=0.5, rely=0.53, anchor="center")

        # Subtle dark ring track
        self.spinner_canvas.create_arc(
            10, 10, 70, 70,
            start=0, extent=359,
            width=5, style="arc",
            outline="#2d3138"
        )

        # Active spinning arc in COTW orange
        self.spinner_ring = self.spinner_canvas.create_arc(
            10, 10, 70, 70,
            start=0, extent=120,
            width=5, style="arc",
            outline="#ff9600"
        )

        # --- Progress Bar ---
        self.progress = CTkProgressBar(
            root,
            width=360,
            height=12,
            mode="determinate",
            progress_color="#ff9600",
            fg_color="#111315",
            border_width=1,
            border_color="#2d3138",
            corner_radius=0,  # Angular edge matching COTW branding
        )
        self.progress.set(0)
        self.progress.place(relx=0.5, rely=0.74, anchor="center")

        # --- Status Text ---
        self.status = CTkLabel(
            root,
            text=self.messages[0],
            font=("Trebuchet MS", 12, "bold"),
            text_color="#a0a5ad",
            bg_color="#212429",
        )
        self.status.place(relx=0.5, rely=0.83, anchor="center")

        self.root.after(50, self.animate)

    def animate(self) -> None:
        self.progress_value += 0.0125
        if self.progress_value > 1.0:
            self.progress_value = 0.0
            self._last_step = -1

        self.progress.set(self.progress_value)

        # Rotate spinner
        self.spinner_angle = (self.spinner_angle + 10) % 360
        self.spinner_canvas.itemconfigure(self.spinner_ring, start=self.spinner_angle)

        # Update status message on 25% increments safely
        current_step = int(self.progress_value * 4)
        if current_step != self._last_step and current_step < len(self.messages):
            self.status_index = current_step
            self.status.configure(text=self.messages[self.status_index])
            self._last_step = current_step

        self.root.after(50, self.animate)


def main() -> None:
    set_appearance_mode("dark")
    app = CTk()
    LoadingScreen(app)
    app.mainloop()


if __name__ == "__main__":
    main()