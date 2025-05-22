import tkinter as tk
from tkinter import ttk
import numpy as np
import random
from synth import (
    set_freq, note_on, note_off,
    set_adsr, set_detune,
    set_volume, set_pan,
    set_wavetable, fs, get_buffer
)

# пастельная «небесная» палитра
BG        = "#E0F7FA"
FG        = "#004D40"
ACCENT    = "#80DEEA"
SLIDER_BG = "#B2EBF2"

root = tk.Tk()
root.title("CurveSynth")
root.geometry("780x750")
root.configure(bg=BG)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=12, pady=12)

# === Вкладка Synth ===
tab = tk.Frame(notebook, bg=BG)
notebook.add(tab, text="Synth")

tk.Label(tab, text="🐚 CurveSynth 🐚",
         font=("Helvetica", 26, "bold"),
         fg=FG, bg=BG).pack(pady=8)

# — Селектор волновой формы —
wav_names = ['Sine','Square','Saw','Triangle','Noise']
wt_frame = tk.Frame(tab, bg=BG)
wt_frame.pack(pady=6)
tk.Label(wt_frame, text="Waveform:", fg=FG, bg=BG).pack(side="left", padx=(0,8))
wt_var = tk.StringVar(value=wav_names[0])
wt_menu = ttk.Combobox(wt_frame, textvariable=wt_var,
                       values=wav_names, state="readonly", width=12)
wt_menu.pack(side="left")
wt_var.trace_add("write", lambda *a: set_wavetable(wt_var.get()))

# — Визуализация волны —
wave_frame = tk.LabelFrame(tab, text="Waveform", fg=FG, bg=BG,
                           font=("Helvetica",14))
wave_frame.pack(pady=6)
canvas = tk.Canvas(wave_frame, width=700, height=150,
                   bg=SLIDER_BG, highlightthickness=0)
canvas.pack()

def update_wave():
    buf = get_buffer()[:,0]  # только левый канал
    canvas.delete("grid")
    canvas.delete("wave")

    h, w = 150, 700
    N = buf.shape[0]
    mx = np.max(np.abs(buf)) or 1.0
    ys = (buf / mx) * (h / 2) + (h / 2)
    step_x = w / N

    # рисуем лёгкую сетку в цвете FG
    for x in range(0, w + 1, int(w / 10)):
        canvas.create_line(x, 0, x, h, fill=FG, dash=(2,4), tag="grid")
    canvas.create_line(0, h/2, w, h/2, fill=FG, dash=(2,4), tag="grid")

    # рисуем волну в цвете ACCENT
    for i in range(N - 1):
        x1, y1 = i * step_x, ys[i]
        x2, y2 = (i + 1) * step_x, ys[i + 1]
        canvas.create_line(x1, y1, x2, y2,
                           fill=ACCENT, width=2, tag="wave")

    root.after(50, update_wave)

# запуск анимации волны
update_wave()

# — Слайдер Частоты —
freq_var = tk.DoubleVar(value=440.0)
f_frame = tk.Frame(tab, bg=BG); f_frame.pack(pady=6)
tk.Label(f_frame, text="Frequency (Hz)",
         fg=FG, bg=BG, font=("Helvetica", 12)).pack(anchor="w")
tk.Scale(f_frame, from_=50, to=2000, resolution=1,
         variable=freq_var, orient=tk.HORIZONTAL,
         command=lambda v: set_freq(float(v)),
         bg=SLIDER_BG, fg=FG, troughcolor=ACCENT,
         length=600).pack()

# — ADSR огибающая —
adsr_frame = tk.LabelFrame(tab, text="ADSR Envelope",
                           fg=FG, bg=BG, font=("Helvetica", 14))
adsr_frame.pack(pady=12, fill="x", padx=8)
labels = ["A","D","S","R"]
ranges = [(0.001,1.0,0.001),(0.001,1.0,0.001),(0.0,1.0,0.01),(0.001,1.0,0.001)]
initial = (0.01, 0.1, 0.7, 0.2)
vars_ = [tk.DoubleVar(value=v) for v in initial]
for i,(lbl,var,(mi,ma,step)) in enumerate(zip(labels,vars_,ranges)):
    tk.Label(adsr_frame, text=lbl,
             fg=FG, bg=BG, font=("Helvetica",12)
    ).grid(row=0,column=i,padx=14)
    tk.Scale(adsr_frame, from_=mi, to=ma, resolution=step,
             variable=var, orient=tk.VERTICAL,
             bg=SLIDER_BG, fg=FG, troughcolor=ACCENT,
             length=180
    ).grid(row=1,column=i,padx=14)
def _upd_adsr(*_):
    set_adsr(vars_[0].get(), vars_[1].get(), vars_[2].get(), vars_[3].get())
for v in vars_: v.trace_add('write', _upd_adsr)

# — Стерео и микс —
mix_frame = tk.LabelFrame(tab, text="Stereo & Mix",
                          fg=FG, bg=BG, font=("Helvetica",14))
mix_frame.pack(pady=12, fill="x", padx=8)
# Детюн
det_var = tk.DoubleVar(value=0.0)
tk.Label(mix_frame, text="Detune (cents)", fg=FG, bg=BG).grid(row=0,column=0)
tk.Scale(mix_frame, from_=-100, to=100, resolution=1,
         variable=det_var, orient=tk.HORIZONTAL,
         command=lambda v: set_detune(float(v)),
         bg=SLIDER_BG, fg=FG, troughcolor=ACCENT,
         length=200
).grid(row=1,column=0,padx=10)
# Громкость
vol_var = tk.DoubleVar(value=0.8)
tk.Label(mix_frame, text="Volume", fg=FG, bg=BG).grid(row=0,column=1)
tk.Scale(mix_frame, from_=0.0, to=1.0, resolution=0.01,
         variable=vol_var, orient=tk.HORIZONTAL,
         command=lambda v: set_volume(float(v)),
         bg=SLIDER_BG, fg=FG, troughcolor=ACCENT,
         length=200
).grid(row=1,column=1,padx=10)
# Панорама
pan_var = tk.DoubleVar(value=0.0)
tk.Label(mix_frame, text="Pan", fg=FG, bg=BG).grid(row=0,column=2)
tk.Scale(mix_frame, from_=-1.0, to=1.0, resolution=0.01,
         variable=pan_var, orient=tk.HORIZONTAL,
         command=lambda v: set_pan(float(v)),
         bg=SLIDER_BG, fg=FG, troughcolor=ACCENT,
         length=200
).grid(row=1,column=2,padx=10)

# — Селектор октавы и клавиши —
octave_var = tk.IntVar(value=4)
oct_frame = tk.Frame(tab, bg=BG)
oct_frame.pack(pady=6)
tk.Label(oct_frame, text="Октава:", fg=FG, bg=BG,
         font=("Helvetica",12)).pack(side="left", padx=(0,8))
tk.Button(oct_frame, text="–", command=lambda: octave_var.set(max(1, octave_var.get()-1)),
          bg=ACCENT, fg=FG, width=2).pack(side="left")
tk.Label(oct_frame, textvariable=octave_var,
         fg=FG, bg=BG, font=("Helvetica",12,"bold")).pack(side="left", padx=4)
tk.Button(oct_frame, text="+", command=lambda: octave_var.set(min(7, octave_var.get()+1)),
          bg=ACCENT, fg=FG, width=2).pack(side="left")

notes = [
    ("C",261.63), ("C#",277.18), ("D",293.66), ("D#",311.13),
    ("E",329.63), ("F",349.23), ("F#",369.99), ("G",392.00),
    ("G#",415.30), ("A",440.00), ("A#",466.16), ("B",493.88)
]
keys_frame = tk.Frame(tab, bg=BG)
keys_frame.pack(pady=12)
for name, base_freq in notes:
    btn = tk.Label(keys_frame, text=name,
                   font=("Helvetica",14,"bold"),
                   bg="white" if "#" not in name else "#ECEFF1",
                   fg=FG, width=4, relief="raised", bd=2)
    btn.pack(side="left", padx=2)
    def _on_press(e, f=base_freq):
        freq = f * (2 ** (octave_var.get() - 4))
        set_freq(freq); note_on(); e.widget.config(bg=ACCENT)
    btn.bind("<ButtonPress-1>", _on_press)
    btn.bind("<ButtonRelease-1>",
             lambda e: (note_off(),
                        e.widget.config(bg="white" if "#" not in e.widget.cget("text") else "#ECEFF1")))

# — Кнопка «Случайные настройки» —
def do_random():
    choice = random.choice(wav_names)
    wt_var.set(choice)
    f = random.uniform(50, 2000)
    freq_var.set(f); set_freq(f)
    for var,(low,high,_) in zip(vars_, ranges):
        var.set(random.uniform(low, high))
    d = random.uniform(-100, 100)
    det_var.set(d); set_detune(d)
    v = random.uniform(0.0, 1.0)
    vol_var.set(v); set_volume(v)
    p = random.uniform(-1.0, 1.0)
    pan_var.set(p); set_pan(p)
    status.config(text="🔀 Randomized!", fg=ACCENT)

rnd_btn = tk.Button(tab, text="Randomize",
                    command=do_random,
                    bg=ACCENT, fg=FG,
                    font=("Helvetica",12,"bold"),
                    relief="flat", padx=20, pady=6)
rnd_btn.pack(pady=8)

# — Статус и выход —
status = tk.Label(tab, text="Press SPACE or click a key",
                  fg=FG, bg=BG,
                  font=("Helvetica",10,"italic"))
status.pack(pady=6)
tk.Label(tab, text=f"Sample rate: {fs} Hz",
         fg=FG, bg=BG,
         font=("Helvetica",10)).pack()

root.bind("<KeyPress-space>",
          lambda e: (
              set_freq(freq_var.get()),
              note_on(),
              status.config(text="▶ Playing…", fg=ACCENT)
          ))
root.bind("<KeyRelease-space>",
          lambda e: (
              note_off(),
              status.config(text="■ Stopped", fg=FG)
          ))

tk.Button(tab, text="Exit", command=root.destroy,
          bg=ACCENT, fg=FG,
          font=("Helvetica",12,"bold"),
          relief="flat", padx=20, pady=6
).pack(pady=14)

# === Вкладка О программе ===
tab2 = tk.Frame(notebook, bg=BG)
notebook.add(tab2, text="About")
about_text = (
    "CurveSynth\n\n"
    "Made by Oleg Dolgov\n"
    "IKBO 13-23\n\n"
    "A simple Python stereo synth\n"
    "with ADSR, detune, volume, pan & wavetables."
)
tk.Label(tab2, text=about_text,
         fg=FG, bg=BG,
         font=("Helvetica",14),
         justify="center").pack(expand=True)

root.mainloop()
