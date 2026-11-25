"""A window the live tests drive. It records what it receives to a JSON file.

Usage: python target_app.py STATE.json
Layout (client coordinates): a solid colour block at the top, a text box below.
State: {"ready", "x", "y" (screen origin of the client area), "text",
        "clicks": [[button, x, y, double]], "scroll": int, "keys": [keysym...]}
"""
import json
import sys
import tkinter as tk

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

STATE_PATH = sys.argv[1]
BLOCK = (0, 0, 300, 120)          # x0, y0, x1, y1 of the colour block, client coords
BLOCK_RGB = (255, 0, 170)

state = {"ready": False, "x": 0, "y": 0, "text": "", "clicks": [], "scroll": 0, "keys": []}
root = tk.Tk()
root.title("deskwright-target")
root.geometry("420x320+120+120")
root.attributes("-topmost", True)

canvas = tk.Canvas(root, width=420, height=120, highlightthickness=0, bg="#202020")
canvas.place(x=0, y=0)
canvas.create_rectangle(*BLOCK, fill="#%02x%02x%02x" % BLOCK_RGB, width=0)
text = tk.Text(root, font=("Segoe UI", 11), wrap="none", undo=False)
text.place(x=0, y=130, width=420, height=190)


def save(*_):
    state["text"] = text.get("1.0", "end-1c")
    state["x"], state["y"] = root.winfo_rootx(), root.winfo_rooty()
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def on_click(btn, double):
    def h(e):
        state["clicks"].append([btn, e.x, e.y, double])
        save()
    return h


def on_wheel(e):
    if getattr(e, "num", None) in (4, 5):
        state["scroll"] += 1 if e.num == 4 else -1
    else:
        state["scroll"] += 1 if e.delta > 0 else -1
    save()


def on_key(e):
    state["keys"].append(e.keysym)
    root.after(30, save)


canvas.bind("<Button-1>", on_click(1, False))
canvas.bind("<Double-Button-1>", on_click(1, True))
canvas.bind("<Button-3>", on_click(3, False))
canvas.bind("<Button-2>" if sys.platform == "darwin" else "<Button-3>", on_click(3, False))
for w in (canvas, text):
    w.bind("<MouseWheel>", on_wheel)
    w.bind("<Button-4>", on_wheel)
    w.bind("<Button-5>", on_wheel)
text.bind("<KeyRelease>", on_key)
text.bind("<<Modified>>", lambda e: (text.edit_modified(False), root.after(30, save)))


def ready():
    root.lift()
    root.focus_force()
    text.focus_set()
    state["ready"] = True
    save()


def poll():
    save()
    root.after(250, poll)


root.after(400, ready)
root.after(600, poll)
root.mainloop()
