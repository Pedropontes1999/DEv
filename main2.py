# -*- coding: utf-8 -*-
import cv2
import mediapipe as mp
import numpy as np
import time
import webbrowser
import os
import ctypes

# ====== Config ======
w, h = 640, 480

# Gestos:
def detectar_gesto_pinca(hand_landmarks):
    polegar = hand_landmarks.landmark[4]
    indicador = hand_landmarks.landmark[8]
    dist = np.hypot(polegar.x - indicador.x, polegar.y - indicador.y)
    return dist < 0.05


def detectar_swipe_direita_esquerda(historico_x, limiar=0.18):
    if len(historico_x) < 6:
        return False
    for i in range(1, len(historico_x)):
        if historico_x[i] >= historico_x[i-1]:
            return False
    return (historico_x[0] - historico_x[-1]) > limiar


# ==================== Win32 move ====================
user32 = ctypes.windll.user32


def active_window_is_browser():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False
    buff = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buff, 512)
    title = buff.value.lower()
    return 'chrome' in title or 'edge' in title or 'firefox' in title or 'google' in title


def mover_janela_ativo_para_segundo_monitor():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False

    if not active_window_is_browser():
        return False

    largura = user32.GetSystemMetrics(0)
    altura = user32.GetSystemMetrics(1)
    x_pos = -largura
    y_pos = 0

    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040

    user32.ShowWindow(hwnd, 9)
    return bool(user32.SetWindowPos(hwnd, 0, x_pos, y_pos, 0, 0, SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOSIZE | SWP_SHOWWINDOW))


# ==================== Loop de controle ====================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

pinca_direita_anterior = False
posicoes_maos = []
max_posicoes = 10
movimento_detectado = False
ultimo_movimento = 0
ultima_acao = 0
cooldown_acao = 2.0

print('Iniciado: pin�a direita=abrir Google | swipe= mover janela do navegador ativo para 2� monitor')

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (w, h))

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    pinca_direita_atual = False
    posicao_atual = None

    if results.multi_hand_landmarks and results.multi_handedness:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            label = handedness.classification[0].label
            if label == 'Right':
                pinca_direita_atual = detectar_gesto_pinca(hand_landmarks)
                posicao_atual = sum([lm.x for lm in hand_landmarks.landmark]) / len(hand_landmarks.landmark)
                break

    if posicao_atual is not None:
        posicoes_maos.append(posicao_atual)
        if len(posicoes_maos) > max_posicoes:
            posicoes_maos.pop(0)

    if detectar_swipe_direita_esquerda(posicoes_maos) and not movimento_detectado:
        if time.time() - ultimo_movimento > cooldown_acao:
            if mover_janela_ativo_para_segundo_monitor():
                print('Movimento detectado: moveu a janela do navegador ativo para monitor secund�rio.')
            else:
                print('Movimento detectado, mas a janela ativa n�o � navegador.')
            movimento_detectado = True
            ultimo_movimento = time.time()
            posicoes_maos.clear()

    if movimento_detectado and time.time() - ultimo_movimento > 1.0:
        movimento_detectado = False

    if pinca_direita_atual and not pinca_direita_anterior:
        if time.time() - ultima_acao > cooldown_acao:
            webbrowser.open('https://www.google.com')
            print('Abrindo Google no browser padr�o.')
            ultima_acao = time.time()

    pinca_direita_anterior = pinca_direita_atual

    cv2.imshow('Controle por Gestos', frame)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
print('Finalizado.')
