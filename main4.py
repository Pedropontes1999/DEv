# -*- coding: utf-8 -*-
"""
main4.py — Desenho no ar (estilo Disney Channel)
Baseado na estrutura do main2/main3 com MediaPipe + OpenCV.

Como usar:
  Fechar pinça (polegar + indicador)  → começa a desenhar
  Abrir a mão                         → pausa (desenho fica na tela)
  Fechar pinça novamente              → continua desenhando
  Teclas:
    C       → limpar tela
    TAB     → trocar cor
    + / -   → aumentar / diminuir espessura
    ESC     → sair
"""

import cv2
import mediapipe as mp
import numpy as np
import math

# ==================== Config ====================
W, H          = 640, 480
PINCH_THRESH  = 0.055        # distância normalizada para considerar pinça
SMOOTH        = 0.4          # suavização do traço (0=sem, 1=instantâneo)

COLORS = [
    (0,   215, 255),   # amarelo-ouro
    (255,  80,  80),   # azul-ciano
    ( 80, 255, 120),   # verde-neon
    (255,  60, 200),   # rosa-roxo
    (255, 200,   0),   # azul-claro
    (255, 255, 255),   # branco
]
COLOR_NAMES = ["Ouro", "Ciano", "Verde", "Rosa", "Azul", "Branco"]

color_idx   = 0
brush_size  = 4

# ==================== MediaPipe ====================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.70,
    min_tracking_confidence=0.60,
)


def is_pinch(lm):
    t = lm.landmark[4]
    i = lm.landmark[8]
    return math.hypot(t.x - i.x, t.y - i.y) < PINCH_THRESH


def tip_px(lm):
    i = lm.landmark[8]
    return (int(i.x * W), int(i.y * H))


# ==================== Canvas e traços ====================
# Cada traço é uma lista de pontos; strokes guarda todos os traços finalizados
canvas  = np.zeros((H, W, 3), dtype=np.uint8)   # camada permanente
strokes = []          # lista de {"pts": [...], "color": ..., "size": int}
current_stroke = None # traço em andamento

prev_pinch  = False
smooth_pos  = None    # posição suavizada do dedo


def draw_glow(img, pt1, pt2, color, size):
    """Desenha linha com halo brilhante."""
    # Halo externo (mais grosso, mais transparente)
    overlay = img.copy()
    cv2.line(overlay, pt1, pt2, color, size + 6, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.25, img, 0.75, 0, img)
    # Linha principal
    cv2.line(img, pt1, pt2, color, size, cv2.LINE_AA)


def redraw_canvas(target):
    """Redesenha todos os traços salvos no canvas."""
    target[:] = 0
    for stroke in strokes:
        pts   = stroke["pts"]
        color = stroke["color"]
        size  = stroke["size"]
        for k in range(1, len(pts)):
            draw_glow(target, pts[k-1], pts[k], color, size)


def blend_canvas(frame, canvas):
    """Sobrepõe o canvas de desenho no frame da câmera."""
    mask = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(mask, 10, 255, cv2.THRESH_BINARY)
    mask3 = cv2.merge([mask, mask, mask])
    result = frame.copy()
    result = np.where(mask3 > 0, canvas, result)
    return result


# ==================== Main ====================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)

print("Desenho no ar iniciado!")
print("Pinça = desenhar | C = limpar | TAB = cor | +/- = espessura | ESC = sair")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (W, H))

    # Escurecer o feed para o desenho destacar
    frame = cv2.addWeighted(frame, 0.5, np.zeros_like(frame), 0.5, 0)

    # ── MediaPipe ──
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False
    result = hands.process(rgb)
    rgb.flags.writeable = True

    pinch_now = False
    raw_pos   = None

    if result.multi_hand_landmarks and result.multi_handedness:
        for lm, hw in zip(result.multi_hand_landmarks, result.multi_handedness):
            if hw.classification[0].label == "Right":
                pinch_now = is_pinch(lm)
                raw_pos   = tip_px(lm)
                break

    # ── Suavização da posição ──
    if raw_pos:
        if smooth_pos is None:
            smooth_pos = raw_pos
        else:
            sx = int(smooth_pos[0] + (raw_pos[0] - smooth_pos[0]) * SMOOTH)
            sy = int(smooth_pos[1] + (raw_pos[1] - smooth_pos[1]) * SMOOTH)
            smooth_pos = (sx, sy)

    # ── Lógica de pinça / traço ──
    color = COLORS[color_idx]

    if pinch_now and raw_pos:
        if not prev_pinch:
            # Início da pinça → novo traço
            current_stroke = {"pts": [smooth_pos], "color": color, "size": brush_size}
        else:
            # Continua pinçando → adiciona ponto
            if current_stroke and smooth_pos != current_stroke["pts"][-1]:
                current_stroke["pts"].append(smooth_pos)
                # Desenha o novo segmento no canvas permanente
                if len(current_stroke["pts"]) >= 2:
                    draw_glow(canvas,
                              current_stroke["pts"][-2],
                              current_stroke["pts"][-1],
                              color, brush_size)
    else:
        if prev_pinch and current_stroke and len(current_stroke["pts"]) >= 2:
            # Soltou a pinça → salva o traço
            strokes.append(current_stroke)
        current_stroke = None

    prev_pinch = pinch_now

    # ── Compor frame final ──
    output = blend_canvas(frame, canvas)

    # ── Cursor do dedo ──
    if smooth_pos:
        if pinch_now:
            cv2.circle(output, smooth_pos, brush_size + 4, color, -1)
            cv2.circle(output, smooth_pos, brush_size + 4, (255, 255, 255), 1)
        else:
            cv2.circle(output, smooth_pos, brush_size + 6, color, 2)
            cv2.circle(output, smooth_pos, 3, color, -1)

    # ── HUD ──
    status = "DESENHANDO" if pinch_now else "PAUSADO"
    st_cor = color if pinch_now else (120, 120, 120)

    cv2.putText(output, status, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(output, status, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, st_cor,    2, cv2.LINE_AA)

    cv2.putText(output, f"Cor: {COLOR_NAMES[color_idx]}  Tam: {brush_size}",
                (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(output, f"Cor: {COLOR_NAMES[color_idx]}  Tam: {brush_size}",
                (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

    # Amostra da cor atual (bolinha no canto)
    cv2.circle(output, (W - 24, 24), 14, color, -1)
    cv2.circle(output, (W - 24, 24), 14, (255, 255, 255), 1)

    cv2.putText(output, "C=limpar | TAB=cor | +/-=tam | ESC=sair",
                (10, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(output, "C=limpar | TAB=cor | +/-=tam | ESC=sair",
                (10, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                (160, 160, 160), 1, cv2.LINE_AA)

    cv2.imshow("Desenho no Ar — Disney Style", output)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:                        # ESC
        break
    elif key == ord('c') or key == ord('C'):
        canvas[:] = 0
        strokes.clear()
        current_stroke = None
    elif key == 9:                       # TAB
        color_idx = (color_idx + 1) % len(COLORS)
    elif key == ord('+') or key == ord('='):
        brush_size = min(brush_size + 1, 20)
    elif key == ord('-') or key == ord('_'):
        brush_size = max(brush_size - 1, 1)

cap.release()
hands.close()
cv2.destroyAllWindows()
print("Encerrado.")
