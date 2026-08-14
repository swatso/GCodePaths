"""
getPath.py

Captures the X,Y,Z path of an object on a diorama by listening for G-code
"G1 X.. Y.. Z.." messages published on an MQTT topic, and saves the captured
path as a paired SVG polyline and G-code file.

Buttons:
    Record - clears the currently stored path and starts capturing new
             incoming points (up to MAX_POINTS).
    Save   - opens a file browser (defaulting to OUTPUT_DIR, or the last
             folder used) with a suggested filename of the form
             PATH_n.GCO, where n is the next free index in whichever
             folder is currently selected. A matching .svg is written
             alongside it under the same base name.
"""

import os
import re
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import paho.mqtt.client as mqtt

# --------------------------------------------------------------------------
# CONFIGURATION - edit these four values to match your setup
# --------------------------------------------------------------------------
MQTT_BROKER_HOST = "192.168.0.2"      # fixed IP address of the MQTT broker
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "track/reporter/2720"            # fixed topic the coordinates are published on
OUTPUT_DIR = r"C:\PathCaptures"        # fixed directory where SVG files are saved

# If the captured path appears mirrored/flipped compared to the object's
# real movement on the diorama, flip the matching axis here (True/False).
INVERT_X = True
INVERT_Y = True
# --------------------------------------------------------------------------

MAX_POINTS = 100

# Statements placed around the first captured G1 line in each .gc file.
GCODE_BEFORE_FIRST = [
    "M106 S0 ; Detach Object",
    "G4 S2 ; Pause",
]
GCODE_AFTER_FIRST = [
    "M106 S255 ; Attach Object",
    "G4 S2 ; Pause",
]

# Add any required statements here later. They are written after the final G1.
GCODE_TRAILING = []

# Matches G1/G01 statements containing X, Y and Z. Matching is
# case-insensitive and extra parameters after Z are ignored.
GCODE_RE = re.compile(
    r"^\s*G0?1\b.*?X\s*(?P<x>[+-]?(?:\d+(?:\.\d*)?|\.\d+))"
    r".*?Y\s*(?P<y>[+-]?(?:\d+(?:\.\d*)?|\.\d+))"
    r".*?Z\s*(?P<z>[+-]?(?:\d+(?:\.\d*)?|\.\d+))",
    re.IGNORECASE,
)


def parse_gcode_line(payload: str):
    """Parse a G1 X.. Y.. Z.. line and return (x, y, z), or None."""
    match = GCODE_RE.search(payload)
    if not match:
        return None
    return (
        float(match.group("x")),
        float(match.group("y")),
        float(match.group("z")),
    )


def next_path_paths(directory: str):
    """Return paired PATH_n.svg and PATH_n.GCO paths for directory.

    The index is folder-aware: it is based on the highest PATH_n.GCO
    already present in the given directory, so saving into a different
    folder restarts/continues numbering relative to that folder's own
    existing files, using the .GCO file as the master.
    """
    os.makedirs(directory, exist_ok=True)
    pattern = re.compile(r"^PATH_(\d+)\.GCO$", re.IGNORECASE)
    max_n = 0
    for name in os.listdir(directory):
        match = pattern.match(name)
        if match:
            max_n = max(max_n, int(match.group(1)))

    base_path = os.path.join(directory, f"PATH_{max_n + 1}")
    return base_path + ".svg", base_path + ".GCO"


def points_to_gcode(points) -> str:
    """Build G-code, wrapping setup statements around the first G1 line."""
    lines = list(GCODE_BEFORE_FIRST)

    for index, (x, y, z) in enumerate(points):
        lines.append(f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f}")
        if index == 0:
            lines.extend(GCODE_AFTER_FIRST)

    lines.extend(GCODE_TRAILING)
    return "\n".join(lines) + "\n"


def corrected_xy(x: float, y: float):
    """Apply the display/plot axis inversion to a raw X,Y pair."""
    if INVERT_X:
        x = -x
    if INVERT_Y:
        y = -y
    return x, y


def points_to_svg(points, margin: float = 10.0) -> str:
    """Build an SVG polyline from the corrected X,Y of raw X,Y,Z points."""
    points = [corrected_xy(x, y) for x, y, _z in points]
    if not points:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" '
            'viewBox="0 0 100 100"></svg>\n'
        )

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width = max(max_x - min_x, 1.0) + margin * 2
    height = max(max_y - min_y, 1.0) + margin * 2

    coords = " ".join(
        f"{x - min_x + margin:.3f},{y - min_y + margin:.3f}" for x, y in points
    )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}mm" '
        f'height="{height:.3f}mm" viewBox="0 0 {width:.3f} {height:.3f}">\n'
        f'  <polyline points="{coords}" fill="none" stroke="black" '
        'stroke-width="0.1" stroke-linejoin="round" stroke-linecap="round"/>\n'
        "</svg>\n"
    )


class GetPathApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("getPath")
        self.resizable(False, False)

        self.points = []
        self.recording = False
        self.msg_queue = queue.Queue()
        self.last_save_dir = OUTPUT_DIR

        self._build_ui()
        self._start_mqtt()
        self.after(100, self._poll_queue)

    # ---------------------------------------------------------- UI ----
    def _build_ui(self):
        top = tk.Frame(self, padx=10, pady=10)
        top.pack(fill="x")

        self.status_var = tk.StringVar(value="Connecting…")
        tk.Label(top, textvariable=self.status_var, fg="orange").pack(side="left")

        self.count_var = tk.StringVar(value=f"Points: 0/{MAX_POINTS}")
        tk.Label(top, textvariable=self.count_var).pack(side="right")

        self.canvas = tk.Canvas(self, width=420, height=420, bg="white",
                                 highlightthickness=1, highlightbackground="grey")
        self.canvas.pack(padx=10, pady=(0, 10))

        btns = tk.Frame(self, padx=10, pady=5)
        btns.pack(fill="x", pady=(0, 10))

        self.record_btn = tk.Button(btns, text="Record", width=14,
                                     command=self.on_record)
        self.record_btn.pack(side="left")

        self.save_btn = tk.Button(btns, text="Save", width=14,
                                   command=self.on_save)
        self.save_btn.pack(side="right")

    # -------------------------------------------------------- MQTT ----
    def _start_mqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        def connect_worker():
            try:
                self.client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
                self.client.loop_start()
            except Exception as exc:
                self.msg_queue.put(("status", f"Broker unreachable: {exc}"))

        threading.Thread(target=connect_worker, daemon=True).start()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(MQTT_TOPIC)
            self.msg_queue.put(("status", "Connected"))
        else:
            self.msg_queue.put(("status", f"Connect failed (rc={rc})"))

    def _on_disconnect(self, client, userdata, rc):
        self.msg_queue.put(("status", "Disconnected"))

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8", errors="ignore")
        except Exception:
            return
        point = parse_gcode_line(payload)
        if point is not None:
            self.msg_queue.put(("point", point))

    # -------------------------------------------------------- queue ----
    def _poll_queue(self):
        try:
            while True:
                kind, data = self.msg_queue.get_nowait()
                if kind == "status":
                    self._set_status(data)
                elif kind == "point":
                    self._add_point(data)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _set_status(self, text):
        self.status_var.set(text)

    def _add_point(self, point):
        if not self.recording:
            return
        if len(self.points) >= MAX_POINTS:
            return
        self.points.append(point)
        self.count_var.set(f"Points: {len(self.points)}/{MAX_POINTS}")
        self._redraw_canvas()

    # ------------------------------------------------------ drawing ----
    def _redraw_canvas(self):
        self.canvas.delete("all")
        if not self.points:
            return
        if len(self.points) == 1:
            x, y = self._to_canvas_coords(self.points[0], self.points)
            self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="blue")
            return

        coords = []
        for p in self.points:
            cx, cy = self._to_canvas_coords(p, self.points)
            coords.extend([cx, cy])
        self.canvas.create_line(*coords, fill="blue", width=2)

    def _to_canvas_coords(self, point, points, size=420, pad=20):
        corrected = [corrected_xy(p[0], p[1]) for p in points]
        xs = [p[0] for p in corrected]
        ys = [p[1] for p in corrected]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)
        scale = min((size - 2 * pad) / span_x, (size - 2 * pad) / span_y)
        x, y = corrected_xy(point[0], point[1])
        cx = pad + (x - min_x) * scale
        cy = pad + (y - min_y) * scale
        return cx, cy

    # ------------------------------------------------------- buttons ----
    def on_record(self):
        self.points = []
        self.recording = True
        self.count_var.set(f"Points: 0/{MAX_POINTS}")
        self.canvas.delete("all")

    def on_save(self):
        if not self.points:
            messagebox.showwarning("getPath", "No points captured yet.")
            return

        default_svg, default_gc = next_path_paths(self.last_save_dir)

        gc_path = filedialog.asksaveasfilename(
            title="Save G-code path as",
            initialdir=os.path.dirname(default_gc),
            initialfile=os.path.basename(default_gc),
            defaultextension=".GCO",
            filetypes=[("GCO files", "*.GCO"), ("All files", "*.*")],
        )
        if not gc_path:
            return  # user cancelled

        base, _ext = os.path.splitext(gc_path)
        svg_path = base + ".svg"

        svg = points_to_svg(self.points)
        gcode = points_to_gcode(self.points)

        try:
            # The .GCO file is the master file, so write it first.
            with open(gc_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(gcode)
            # An SVG at the same location/name may be overwritten.
            with open(svg_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(svg)
        except OSError as exc:
            messagebox.showerror("getPath", f"Could not save files:\n{exc}")
            return

        # Remember this folder so the next Save suggests numbering from here.
        self.last_save_dir = os.path.dirname(gc_path)

        messagebox.showinfo(
            "getPath",
            f"Saved {len(self.points)} points to:\n{gc_path}\n{svg_path}",
        )


if __name__ == "__main__":
    app = GetPathApp()
    app.mainloop()
