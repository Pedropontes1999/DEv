import cv2
import mediapipe as mp
import numpy as np
import random
import math
import time

# =========================
# CONFIG
# =========================
w, h = 640, 480
tempo_inicio = time.time()

# =========================
# FUNCAO: DETECTAR GESTO (polegar + indicador próximos = pinça)
# =========================
def detectar_gesto_pinça(hand_landmarks):
    """Detecta se está fazendo gesto de pinça (polegar + indicador próximos)"""
    polegar = hand_landmarks.landmark[4]
    indicador = hand_landmarks.landmark[8]
    
    dist = math.hypot(polegar.x - indicador.x, polegar.y - indicador.y)
    
    return dist < 0.05  # Limite para considerar como pinça

# =========================
# FUNCAO: DESENHAR BOLA COM EFEITO DE ENERGIA (GOJO STYLE)
# =========================
# =========================
# FUNCAO: DESENHAR BOLA COM EFEITO DE ENERGIA (GOJO STYLE)
# =========================
def desenhar_bola_energia(image, centro, raio, cor_base, tempo, intensidade=1.0):
    """Desenha uma bola com efeito de energia espiral (estilo Gojo)"""
    x, y = int(centro[0]), int(centro[1])
    
    # Camadas de energia (efeito de profundidade)
    for camada in range(4):
        raio_atual = raio + camada * 4
        alpha = 0.9 - camada * 0.15
        
        # Espiral de energia (mais partículas)
        for i in range(12):
            angulo = (tempo * 3 + i * 30) % 360
            rad = math.radians(angulo)
            
            # Pontos da espiral
            px = x + int(math.cos(rad) * raio_atual * 0.7)
            py = y + int(math.sin(rad) * raio_atual * 0.7)
            
            # Cor com variação pulsante
            intensidade_cor = int(255 * alpha * intensidade * (0.6 + 0.4 * math.sin(tempo * 4 + i * 0.5)))
            cor = tuple(int(c * intensidade_cor / 255) for c in cor_base)
            
            # Tamanho variável das partículas
            tamanho_particula = 1 + int(math.sin(tempo * 2 + i) * 0.5)
            cv2.circle(image, (px, py), tamanho_particula, cor, -1)
    
    # Raios externos (mais dinâmicos)
    for i in range(16):
        angulo = (tempo * 2 + i * 22.5) % 360
        rad = math.radians(angulo)
        
        # Comprimento variável dos raios
        comprimento = raio * (1.5 + 0.5 * math.sin(tempo * 3 + i))
        
        # Raio externo
        px1 = x + int(math.cos(rad) * raio * 1.1)
        py1 = y + int(math.sin(rad) * raio * 1.1)
        
        # Raio interno
        px2 = x + int(math.cos(rad) * comprimento)
        py2 = y + int(math.sin(rad) * comprimento)
        
        # Espessura variável
        espessura = 1 + int(math.sin(tempo * 5 + i) * 0.5)
        cv2.line(image, (px1, py1), (px2, py2), cor_base, espessura)
    
    # Bola central brilhante
    cv2.circle(image, (x, y), raio, cor_base, -1)
    
    # Brilho interno (ponto branco pulsante)
    brilho_raio = int(raio * 0.5 + math.sin(tempo * 6) * 3)
    cv2.circle(image, (x - raio//3, y - raio//3), brilho_raio, (255, 255, 255), -1)
    
    # Partículas flutuando ao redor
    for i in range(8):
        angulo_particula = (tempo * 1.5 + i * 45) % 360
        rad_particula = math.radians(angulo_particula)
        distancia = raio * (1.2 + 0.3 * math.sin(tempo * 2 + i))
        
        px = x + int(math.cos(rad_particula) * distancia)
        py = y + int(math.sin(rad_particula) * distancia)
        
        # Partículas menores flutuando
        tamanho_mini = 1 + int(math.sin(tempo * 4 + i) * 0.5)
        intensidade_mini = int(200 * (0.5 + 0.5 * math.sin(tempo * 3 + i)))
        cor_mini = tuple(int(c * intensidade_mini / 255) for c in cor_base)
        cv2.circle(image, (px, py), tamanho_mini, cor_mini, -1)

# =========================
# FUNCAO: GERAR PARTÍCULAS DE EFEITO SPACE
# =========================
def gerar_stars(num_stars=50):
    """Gera estrelas para efeito de espaço"""
    stars = []
    for _ in range(num_stars):
        stars.append({
            "x": random.randint(0, w),
            "y": random.randint(0, h),
            "brilho": random.randint(50, 200),
            "vel": random.uniform(0.1, 0.5)
        })
    return stars

stars = gerar_stars(50)

# =========================
# MEDIAPIPE - DETECÇÃO DE MÃOS
# =========================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

# =========================
# LOOP PRINCIPAL
# =========================
frame_count = 0
bola_azul_ativa = False
bola_vermelha_ativa = False
bola_azul_pos = None
bola_vermelha_pos = None
bola_roxa_ativa = False
bola_roxa_pos = None
bola_roxa_criada = False  # Flag para manter bolas individuais desativadas

# Estados para detectar mudança de gesto
pinca_esquerda_anterior = False
pinca_direita_anterior = False
pinca_dupla_anterior = False

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (w, h))
    frame_count += 1
    
    tempo_atual = time.time() - tempo_inicio
    
    # Fundo com tema space (gradiente escuro)
    canvas = frame.copy()
    overlay = np.zeros((h, w, 3), dtype=np.uint8)
    
    # =========================
    # RENDERIZAR STARS (SPACE)
    # =========================
    for star in stars:
        x, y = int(star["x"]), int(star["y"])
        
        # Pulsação de brilho
        novo_brilho = int(star["brilho"] + np.sin(tempo_atual * 3 + star["x"]) * 50)
        novo_brilho = max(20, min(255, novo_brilho))
        
        # Desenha estrela
        cv2.circle(overlay, (x, y), 1, (novo_brilho, novo_brilho, novo_brilho), -1)
        
        # Movimento lento (animação)
        star["y"] += star["vel"]
        if star["y"] > h:
            star["y"] = 0
            star["x"] = random.randint(0, w)
    
    # Mistura o overlay de stars com a câmera
    canvas = cv2.addWeighted(overlay, 0.3, canvas, 0.7, 0)

    # =========================
    # DETECÇÃO DE MÃOS
    # =========================
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    pinca_esquerda_atual = False
    pinca_direita_atual = False

    if results.multi_hand_landmarks and results.multi_handedness:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            label = handedness.classification[0].label  # 'Left' ou 'Right'
            
            # Detecta gesto de pinça
            pinca_atual = detectar_gesto_pinça(hand_landmarks)
            
            if label == "Left":
                pinca_esquerda_atual = pinca_atual
                if pinca_atual and not pinca_esquerda_anterior:
                    # Toggle bola azul
                    bola_azul_ativa = not bola_azul_ativa
                    if bola_azul_ativa:
                        indicador = hand_landmarks.landmark[8]
                        bola_azul_pos = (int(indicador.x * w), int(indicador.y * h))
                
                # Atualiza posição se ativa
                if bola_azul_ativa:
                    indicador = hand_landmarks.landmark[8]
                    bola_azul_pos = (int(indicador.x * w), int(indicador.y * h))
                    
            else:  # Right
                pinca_direita_atual = pinca_atual
                if pinca_atual and not pinca_direita_anterior:
                    # Toggle bola vermelha
                    bola_vermelha_ativa = not bola_vermelha_ativa
                    if bola_vermelha_ativa:
                        indicador = hand_landmarks.landmark[8]
                        bola_vermelha_pos = (int(indicador.x * w), int(indicador.y * h))
                
                # Atualiza posição se ativa
                if bola_vermelha_ativa:
                    indicador = hand_landmarks.landmark[8]
                    bola_vermelha_pos = (int(indicador.x * w), int(indicador.y * h))

    # Atualiza estados anteriores
    pinca_dupla_atual = pinca_esquerda_atual and pinca_direita_atual
    
    # Se ambas as mãos fazem pinça simultaneamente, desativa a bola roxa
    if pinca_dupla_atual and not pinca_dupla_anterior and bola_roxa_ativa:
        bola_roxa_ativa = False
        bola_roxa_pos = None
        bola_roxa_criada = False  # Reseta a flag
    
    pinca_esquerda_anterior = pinca_esquerda_atual
    pinca_direita_anterior = pinca_direita_atual
    pinca_dupla_anterior = pinca_dupla_atual
    # =========================
    # DESENHAR BOLINHAS (COM EFEITO GOJO) - SÓ SE NÃO HOUVER BOLA ROXA CRIADA
    # =========================
    if not bola_roxa_criada:
        if bola_azul_ativa and bola_azul_pos:
            # Azul mais brilhante (estilo Gojo)
            desenhar_bola_energia(canvas, bola_azul_pos, 22, (255, 150, 150), tempo_atual, 1.2)  # Azul brilhante
        
        if bola_vermelha_ativa and bola_vermelha_pos:
            # Vermelho mais intenso (estilo Sukuna/Domain Expansion)
            desenhar_bola_energia(canvas, bola_vermelha_pos, 22, (100, 100, 255), tempo_atual, 1.2)  # Vermelho intenso

    # =========================
    # EFEITO ROXO (JUNÇÃO DAS BOLINHAS) - MAIS DRAMÁTICO
    # =========================
    if not bola_roxa_criada:
        # Verifica se deve criar a bola roxa
        if bola_azul_ativa and bola_vermelha_ativa and bola_azul_pos and bola_vermelha_pos:
            dist = math.hypot(bola_azul_pos[0] - bola_vermelha_pos[0], bola_azul_pos[1] - bola_vermelha_pos[1])
            
            # Se estão próximas (menos de 120px) - CRIA BOLA ROXA
            if dist < 120:
                bola_roxa_criada = True
                bola_roxa_pos = ((bola_azul_pos[0] + bola_vermelha_pos[0]) // 2, 
                                (bola_azul_pos[1] + bola_vermelha_pos[1]) // 2)
    
    # Se a bola roxa foi criada, mantém ela ativa e permite controle pela mão direita
    if bola_roxa_criada and bola_roxa_pos:
        bola_roxa_ativa = True
        
        # Atualiza posição da bola roxa baseada na mão direita (se detectada)
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label
                if label == "Right":  # Mão direita controla a bola roxa
                    indicador_direita = hand_landmarks.landmark[8]
                    x_direita = int(indicador_direita.x * w)
                    y_direita = int(indicador_direita.y * h)
                    bola_roxa_pos = (x_direita, y_direita)
                    break  # Usa apenas a primeira mão direita detectada
        
        centro_x, centro_y = bola_roxa_pos
        
        # Raio fixo para bola roxa mantida
        raio = 40
        
        # Bola roxa (mistura de azul e vermelho) - mais intensa
        desenhar_bola_energia(canvas, (centro_x, centro_y), raio, (255, 120, 255), tempo_atual, 1.5)
        
        # Partículas flutuando ao redor da junção (efeito especial)
        for particula_extra in range(20):
            angulo_extra = (tempo_atual * 2 + particula_extra * 18) % 360
            rad_extra = math.radians(angulo_extra)
            distancia_extra = 40 + particula_extra * 3
            
            px_extra = centro_x + int(math.cos(rad_extra) * distancia_extra)
            py_extra = centro_y + int(math.sin(rad_extra) * distancia_extra)
            
            # Movimento ondulante adicional
            offset_extra_x = int(math.sin(tempo_atual * 4 + particula_extra) * 8)
            offset_extra_y = int(math.cos(tempo_atual * 3 + particula_extra) * 6)
            
            # Partículas com cores variadas (azul, roxo, branco)
            cores_extras = [(255, 200, 200), (200, 150, 255), (255, 255, 255)]
            cor_extra = cores_extras[particula_extra % 3]
            
            tamanho_extra = 1 + int(math.sin(tempo_atual * 6 + particula_extra) * 1)
            cv2.circle(canvas, (px_extra + offset_extra_x, py_extra + offset_extra_y), 
                      tamanho_extra, cor_extra, -1)
        
        # Texto flutuante
        texto_y = centro_y - 60
        cv2.putText(canvas, "DOMAIN EXPANSION", (centro_x - 120, texto_y + 2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.putText(canvas, "DOMAIN EXPANSION", (centro_x - 120, texto_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # Efeito de brilho global quando bolas estão ativas
    if bola_azul_ativa or bola_vermelha_ativa:
        # Overlay de brilho sutil
        overlay_brilho = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Brilho pulsante baseado no tempo
        intensidade_brilho = int(20 + 10 * math.sin(tempo_atual * 2))
        overlay_brilho[:, :] = (intensidade_brilho, intensidade_brilho, intensidade_brilho * 1.2)
        
        canvas = cv2.addWeighted(canvas, 0.95, overlay_brilho, 0.05, 0)

    # Mistura canvas com webcam (mais destaque para os efeitos)
    canvas = cv2.addWeighted(canvas, 0.85, frame, 0.15, 0)

    cv2.imshow("Jujutsu Kaisen - Cursed Energy Orbs", canvas)

    if cv2.waitKey(1) == 27:  # ESC para sair
        break

cap.release()
cv2.destroyAllWindows()