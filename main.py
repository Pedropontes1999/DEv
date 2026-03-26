"""
main.py — JJK Cursed Energy v3
Você aparece direto sobre o fundo orgânico + orbes.
Sem segmentação, sem aura — limpo e rápido.

Gestos:
  Pinça mão ESQUERDA       → toggle bola azul  (Gojo)
  Pinça mão DIREITA        → toggle bola vermelha (Sukuna)
  Aproximar as duas bolas  → Hollow Purple
  Pinça dupla simultânea   → resetar tudo
"""

import cv2
import mediapipe as mp
import math
import time

from effects import EffectRenderer

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
W, H         = 640, 480
PINCH_THRESH = 0.055
MERGE_DIST   = 130

# ─────────────────────────────────────────────
# MEDIAPIPE — só mãos
# ─────────────────────────────────────────────
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.70,
    min_tracking_confidence=0.60,
)

def is_pinch(lm):
    t, i = lm.landmark[4], lm.landmark[8]
    return math.hypot(t.x - i.x, t.y - i.y) < PINCH_THRESH

def tip_px(lm):
    i = lm.landmark[8]
    return (int(i.x * W), int(i.y * H))

# ─────────────────────────────────────────────
# ESTADO
# ─────────────────────────────────────────────
state = {
    "blue_active":    False,
    "blue_pos":       (W//3,   H//2),
    "red_active":     False,
    "red_pos":        (2*W//3, H//2),
    "hollow_active":  False,
    "hollow_pos":     (W//2,   H//2),
    "hollow_created": False,
}
prev_L = prev_R = prev_dual = False

# ─────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────
renderer = EffectRenderer(W, H)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)

t0 = time.time()

# ─────────────────────────────────────────────
# LOOP
# ─────────────────────────────────────────────
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (W, H))
    t     = time.time() - t0

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False
    result = hands.process(rgb)
    rgb.flags.writeable = True

    pinch_L = pinch_R = False

    if result.multi_hand_landmarks and result.multi_handedness:
        for lm, hw in zip(result.multi_hand_landmarks,
                          result.multi_handedness):
            label = hw.classification[0].label
            pinch = is_pinch(lm)
            pos   = tip_px(lm)

            if label == "Left":
                pinch_L = pinch
                if pinch and not prev_L and not state["hollow_created"]:
                    state["blue_active"] = not state["blue_active"]
                if state["blue_active"] and not state["hollow_created"]:
                    state["blue_pos"] = pos
            else:
                pinch_R = pinch
                if pinch and not prev_R and not state["hollow_created"]:
                    state["red_active"] = not state["red_active"]
                if state["red_active"] and not state["hollow_created"]:
                    state["red_pos"] = pos
                if state["hollow_created"]:
                    state["hollow_pos"] = pos

    dual = pinch_L and pinch_R
    if dual and not prev_dual and state["hollow_created"]:
        state.update({
            "blue_active":    False,
            "red_active":     False,
            "hollow_active":  False,
            "hollow_created": False,
        })

    if (not state["hollow_created"]
            and state["blue_active"] and state["red_active"]):
        d = math.hypot(state["blue_pos"][0] - state["red_pos"][0],
                       state["blue_pos"][1] - state["red_pos"][1])
        if d < MERGE_DIST:
            state["hollow_created"] = True
            state["hollow_active"]  = True
            state["hollow_pos"] = (
                (state["blue_pos"][0] + state["red_pos"][0]) // 2,
                (state["blue_pos"][1] + state["red_pos"][1]) // 2,
            )

    prev_L, prev_R, prev_dual = pinch_L, pinch_R, dual

    # ── Render ───────────────────────────────
    output = renderer.render(frame, state, t)

    # ── HUD ──────────────────────────────────
    COR_AZUL = (255, 180,  60)
    COR_VERM = ( 30,  30, 255)
    COR_ROXO = (220,  60, 200)
    COR_OFF  = ( 55,  55,  55)

    cv2.putText(output, "◈ INFINITO",
                (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                COR_AZUL if state["blue_active"] else COR_OFF, 1, cv2.LINE_AA)
    cv2.putText(output, "MALDIÇÃO ◈",
                (W-138, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                COR_VERM if state["red_active"] else COR_OFF, 1, cv2.LINE_AA)

    if state["hollow_created"]:
        txt = "HOLLOW PURPLE"
        (tw, _), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_DUPLEX, 0.80, 2)
        tx = (W - tw) // 2
        cv2.putText(output, txt, (tx+2, H-14),
                    cv2.FONT_HERSHEY_DUPLEX, 0.80, (0,0,0), 3, cv2.LINE_AA)
        cv2.putText(output, txt, (tx,   H-16),
                    cv2.FONT_HERSHEY_DUPLEX, 0.80, COR_ROXO, 2, cv2.LINE_AA)

    cv2.imshow("呪術廻戦 — Cursed Energy", output)
    if cv2.waitKey(1) == 27:
        break

cap.release()
renderer.release()
hands.close()
cv2.destroyAllWindows()