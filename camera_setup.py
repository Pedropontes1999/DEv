# -*- coding: utf-8 -*-
"""
camera_setup.py — Seletor de câmera (PC ou celular via Wi-Fi)
Importado por main3.py, main4.py e estoque.py.

Retorna a fonte correta para cv2.VideoCapture().
"""

import tkinter as tk
from tkinter import messagebox


def escolher_camera():
    """
    Abre uma janela para o usuário escolher entre câmera do PC ou celular.
    Retorna:
      - 0                             → webcam do PC
      - "http://IP:PORTA/video"       → câmera IP do celular
    """
    resultado = [0]   # default: PC

    root = tk.Tk()
    root.title("Selecionar Câmera")
    root.geometry("380x260")
    root.resizable(False, False)
    root.configure(bg="#0F1923")
    root.eval("tk::PlaceWindow . center")

    BG      = "#0F1923"
    SURFACE = "#162230"
    ACCENT  = "#00C2FF"
    TEXT    = "#E8F0FA"
    DIM     = "#7A95B0"
    BTN_FG  = "#0A1520"

    tk.Frame(root, bg=ACCENT, height=3).pack(fill="x")

    tk.Label(root, text="Selecionar Câmera",
             font=("Segoe UI", 13, "bold"),
             bg=BG, fg=TEXT).pack(pady=(18, 4))
    tk.Label(root, text="Escolha a origem do vídeo para detecção de gestos",
             font=("Segoe UI", 8), bg=BG, fg=DIM).pack()

    tk.Frame(root, bg="#243548", height=1).pack(fill="x", pady=12, padx=20)

    # ── Botão PC ──
    def usar_pc():
        resultado[0] = 0
        root.destroy()

    btn_pc = tk.Button(root, text="  Câmera do PC  (webcam)",
                       command=usar_pc,
                       bg=ACCENT, fg=BTN_FG,
                       activebackground="#009ECC", activeforeground=BTN_FG,
                       relief="flat", bd=0,
                       font=("Segoe UI", 10, "bold"),
                       cursor="hand2", width=28, pady=8)
    btn_pc.pack(padx=30)

    tk.Label(root, text="— ou —", font=("Segoe UI", 8),
             bg=BG, fg=DIM).pack(pady=8)

    # ── Campo IP ──
    ip_frame = tk.Frame(root, bg=BG)
    ip_frame.pack(padx=30, fill="x")

    tk.Label(ip_frame, text="IP do celular:",
             font=("Segoe UI", 8), bg=BG, fg=DIM).pack(anchor="w")

    entry_wrap = tk.Frame(ip_frame, bg="#243548", padx=1, pady=1)
    entry_wrap.pack(fill="x", pady=(3, 6))
    inner = tk.Frame(entry_wrap, bg="#0A1520")
    inner.pack(fill="x")
    ip_var = tk.StringVar(value="192.168.1.")
    entry = tk.Entry(inner, textvariable=ip_var, bg="#0A1520", fg=TEXT,
                     insertbackground=ACCENT, relief="flat",
                     font=("Consolas", 10), bd=0)
    entry.pack(fill="x", padx=10, pady=7)
    entry.bind("<FocusIn>",  lambda e: entry_wrap.config(bg=ACCENT))
    entry.bind("<FocusOut>", lambda e: entry_wrap.config(bg="#243548"))

    # ── Botão Celular ──
    def usar_celular():
        ip = ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Aviso", "Digite o IP do celular.", parent=root)
            return
        # Monta a URL — porta padrão do DroidCam é 4747
        if ip.startswith("http"):
            url = ip if "/video" in ip else ip.rstrip("/") + "/video"
        else:
            porta = "4747"
            if ":" in ip:
                ip, porta = ip.rsplit(":", 1)
            url = f"http://{ip}:{porta}/mjpegfeed"
        resultado[0] = url
        root.destroy()

    btn_cel = tk.Button(root, text="  Câmera do Celular  (Wi-Fi)",
                        command=usar_celular,
                        bg=SURFACE, fg=TEXT,
                        activebackground="#243548", activeforeground=TEXT,
                        relief="flat", bd=0,
                        font=("Segoe UI", 10, "bold"),
                        cursor="hand2", width=28, pady=8)
    btn_cel.pack(padx=30, pady=(0, 4))

    tk.Label(root,
             text="App: DroidCam (porta 4747)  |  IP Webcam: digite IP:8080",
             font=("Segoe UI", 7), bg=BG, fg="#3D5570").pack(pady=(6, 0))

    entry.focus_set()
    root.mainloop()

    return resultado[0]


if __name__ == "__main__":
    src = escolher_camera()
    print(f"Fonte selecionada: {src}")
