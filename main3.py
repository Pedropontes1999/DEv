# -*- coding: utf-8 -*-
"""
main3.py — Flappy Bird com rastreamento de dedo
Baseado no main2.py (MediaPipe + OpenCV).

Como jogar:
  - Levante o dedo indicador direito na frente da câmera
  - O pássaro segue a posição VERTICAL do seu dedo
  - Passe pelos canos sem bater
  - ESC para sair | ENTER para reiniciar
"""

import cv2
import mediapipe as mp
import numpy as np
import random
import time

# ==================== Config ====================
W, H = 640, 480

BIRD_X        = 130          # posição horizontal fixa do pássaro
BIRD_RADIUS   = 18           # raio do pássaro
PIPE_WIDTH    = 60           # largura dos canos
PIPE_GAP      = 140          # abertura entre cano de cima e de baixo
PIPE_SPEED    = 4            # pixels por frame
PIPE_INTERVAL = 2.0          # segundos entre canos
SCORE_PER_PIPE = 1

# Cores (BGR)
COR_CANO    = (34, 139, 34)
COR_CANO_BD = (0, 100, 0)
COR_PASSARO = (0, 215, 255)
COR_OLHO    = (255, 255, 255)
COR_PUPILA  = (0, 0, 0)
COR_HUD     = (255, 255, 255)
COR_GAMEOVER= (0, 0, 220)
COR_DEDO    = (0, 255, 128)

# ==================== MediaPipe ====================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.70,
    min_tracking_confidence=0.60,
)


def get_finger_y(hand_landmarks):
    """Retorna a posição Y normalizada da ponta do indicador."""
    return hand_landmarks.landmark[8].y   # 0 = topo, 1 = base


# ==================== Estado do jogo ====================
class FlappyGame:
    def __init__(self):
        self.reset()

    def reset(self):
        self.bird_y      = H // 2
        self.target_y    = H // 2
        self.pipes       = []                 # lista de {x, top_h, passed}
        self.score       = 0
        self.best        = getattr(self, "best", 0)
        self.alive       = True
        self.started     = False              # começa quando dedo aparecer
        self.last_pipe_t = time.time()
        self.flash       = 0.0               # flash de hit

    def spawn_pipe(self):
        top_h = random.randint(60, H - PIPE_GAP - 60)
        self.pipes.append({"x": W + PIPE_WIDTH, "top_h": top_h, "passed": False})

    def update(self, finger_y_norm):
        if not self.alive:
            return

        # ── Mover pássaro suavemente até o dedo ──
        self.target_y = int(finger_y_norm * H)
        self.bird_y  += int((self.target_y - self.bird_y) * 0.25)

        # ── Spawnar canos ──
        now = time.time()
        if now - self.last_pipe_t > PIPE_INTERVAL:
            self.spawn_pipe()
            self.last_pipe_t = now

        # ── Mover e checar canos ──
        for pipe in self.pipes:
            pipe["x"] -= PIPE_SPEED

            # Passou pelo cano?
            if not pipe["passed"] and pipe["x"] + PIPE_WIDTH < BIRD_X - BIRD_RADIUS:
                pipe["passed"] = True
                self.score += SCORE_PER_PIPE
                if self.score > self.best:
                    self.best = self.score

            # Colisão
            if self._hit_pipe(pipe):
                self.alive = False
                self.flash = 1.0
                return

        # Remover canos que saíram da tela
        self.pipes = [p for p in self.pipes if p["x"] > -PIPE_WIDTH - 10]

        # Colisão com bordas
        if self.bird_y - BIRD_RADIUS <= 0 or self.bird_y + BIRD_RADIUS >= H:
            self.alive = False
            self.flash = 1.0

    def _hit_pipe(self, pipe):
        bx1 = BIRD_X - BIRD_RADIUS
        bx2 = BIRD_X + BIRD_RADIUS
        by1 = self.bird_y - BIRD_RADIUS
        by2 = self.bird_y + BIRD_RADIUS

        px1 = pipe["x"]
        px2 = pipe["x"] + PIPE_WIDTH

        # Sobreposição horizontal
        if bx2 < px1 or bx1 > px2:
            return False

        top_bottom = pipe["top_h"]
        bot_top    = pipe["top_h"] + PIPE_GAP

        # Sobreposição vertical com cano de cima OU de baixo
        return by1 < top_bottom or by2 > bot_top


# ==================== Render ====================
def draw_pipe(frame, pipe):
    x      = pipe["x"]
    top_h  = pipe["top_h"]
    bot_y  = top_h + PIPE_GAP

    # Cano de cima
    cv2.rectangle(frame, (x, 0), (x + PIPE_WIDTH, top_h),
                  COR_CANO, -1)
    cv2.rectangle(frame, (x - 4, top_h - 20), (x + PIPE_WIDTH + 4, top_h),
                  COR_CANO_BD, -1)
    # Borda
    cv2.rectangle(frame, (x, 0), (x + PIPE_WIDTH, top_h),
                  COR_CANO_BD, 2)

    # Cano de baixo
    cv2.rectangle(frame, (x, bot_y), (x + PIPE_WIDTH, H),
                  COR_CANO, -1)
    cv2.rectangle(frame, (x - 4, bot_y), (x + PIPE_WIDTH + 4, bot_y + 20),
                  COR_CANO_BD, -1)
    cv2.rectangle(frame, (x, bot_y), (x + PIPE_WIDTH, H),
                  COR_CANO_BD, 2)


def draw_bird(frame, y):
    cx, cy = BIRD_X, y

    # Corpo
    cv2.circle(frame, (cx, cy), BIRD_RADIUS, COR_PASSARO, -1)
    cv2.circle(frame, (cx, cy), BIRD_RADIUS, (0, 160, 200), 2)

    # Olho
    cv2.circle(frame, (cx + 7, cy - 5), 6, COR_OLHO, -1)
    cv2.circle(frame, (cx + 8, cy - 5), 3, COR_PUPILA, -1)

    # Bico
    pts = np.array([[cx + 14, cy + 2],
                    [cx + 22, cy - 1],
                    [cx + 14, cy + 6]], np.int32)
    cv2.fillPoly(frame, [pts], (0, 140, 255))


def overlay_hud(frame, game, finger_px):
    # Pontuação
    cv2.putText(frame, f"SCORE  {game.score}", (10, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0),    4, cv2.LINE_AA)
    cv2.putText(frame, f"SCORE  {game.score}", (10, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, COR_HUD,       2, cv2.LINE_AA)

    cv2.putText(frame, f"BEST   {game.best}", (10, 64),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0),    3, cv2.LINE_AA)
    cv2.putText(frame, f"BEST   {game.best}", (10, 64),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

    # Indicador do dedo
    if finger_px is not None:
        cv2.circle(frame, finger_px, 10, COR_DEDO, -1)
        cv2.circle(frame, finger_px, 10, (255, 255, 255), 2)
        cv2.line(frame, (finger_px[0], finger_px[1]),
                 (BIRD_X, game.bird_y), COR_DEDO, 1, cv2.LINE_AA)

    # Instrução inicial
    if not game.started:
        msg = "Mostre o dedo indicador para comecar!"
        tw, _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[:2]
        tx = (W - tw[0]) // 2
        cv2.putText(frame, msg, (tx + 2, H // 2 + 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, msg, (tx, H // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 100), 2, cv2.LINE_AA)


def overlay_gameover(frame, game):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (W, H), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

    cv2.putText(frame, "GAME OVER", (W//2 - 145, H//2 - 40),
                cv2.FONT_HERSHEY_DUPLEX, 1.4, (0, 0, 0),    5, cv2.LINE_AA)
    cv2.putText(frame, "GAME OVER", (W//2 - 147, H//2 - 42),
                cv2.FONT_HERSHEY_DUPLEX, 1.4, COR_GAMEOVER,  3, cv2.LINE_AA)

    cv2.putText(frame, f"Pontuacao: {game.score}", (W//2 - 100, H//2 + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, f"Recorde:   {game.best}", (W//2 - 100, H//2 + 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 215, 255),   2, cv2.LINE_AA)
    cv2.putText(frame, "ENTER para reiniciar | ESC para sair",
                (W//2 - 195, H//2 + 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)


# ==================== Main ====================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)

game = FlappyGame()
print("Flappy Bird por dedo — mostre o indicador na câmera!")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (W, H))

    # ── Escurecer levemente o feed para contrastar com o jogo ──
    frame = cv2.addWeighted(frame, 0.55, np.zeros_like(frame), 0.45, 0)

    # ── MediaPipe ──
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False
    results = hands.process(rgb)
    rgb.flags.writeable = True

    finger_y_norm = 0.5
    finger_px     = None

    if results.multi_hand_landmarks and results.multi_handedness:
        for lm, hw in zip(results.multi_hand_landmarks, results.multi_handedness):
            if hw.classification[0].label == "Right":
                finger_y_norm = get_finger_y(lm)
                finger_px     = (int(lm.landmark[8].x * W),
                                 int(lm.landmark[8].y * H))
                game.started  = True
                break

    # ── Atualizar lógica ──
    if game.started and game.alive:
        game.update(finger_y_norm)

    # ── Desenhar canos ──
    for pipe in game.pipes:
        draw_pipe(frame, pipe)

    # ── Flash de colisão ──
    if game.flash > 0:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (W, H), (0, 0, 255), -1)
        cv2.addWeighted(overlay, game.flash * 0.5, frame, 1 - game.flash * 0.5, 0, frame)
        game.flash = max(0.0, game.flash - 0.08)

    # ── Desenhar pássaro ──
    draw_bird(frame, game.bird_y)

    # ── HUD ──
    overlay_hud(frame, game, finger_px)

    if not game.alive:
        overlay_gameover(frame, game)

    cv2.imshow("Flappy Bird — Controle por Dedo", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:          # ESC
        break
    if key == 13:          # ENTER
        game.reset()

cap.release()
hands.close()
cv2.destroyAllWindows()
print("Fim de jogo. Obrigado!")
