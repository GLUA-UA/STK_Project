#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import pygame  # Certifique-se de que o pygame está instalado: pip install pygame
import sys
import socket
import os

# --- CONFIGURAÇÃO ---
BASE_ASSETS = "stk-assets/tracks/"
PORTA_UDP = 9999
LARGURA_MAPA = 800
LARGURA_LATERAL = 250
ALTURA = 800
LARGURA_TOTAL = LARGURA_MAPA + LARGURA_LATERAL

def loadXML(track_id):
    xml_path = os.path.join(BASE_ASSETS, track_id, "quads.xml")
    if not os.path.exists(xml_path):
        print(f"Erro: Arquivo não encontrado em {xml_path}")
        return None, 0, 0, 1, 1

    print(f"Carregando novo mapa: {track_id}")
    tree = ET.parse(xml_path)
    root = tree.getroot()
    quadrados_processados = []
    for quad in root.findall('quad'):
        pontos = []
        for i in range(4):
            v = quad.attrib[f'p{i}']
            if ":" in v:
                idx, pt = map(int, v.split(":"))
                pontos.append(quadrados_processados[idx][pt])
            else:
                c = v.split()
                pontos.append((float(c[0]), float(c[2])))
        quadrados_processados.append(pontos)
    
    todas_x = [p[0] for q in quadrados_processados for p in q]
    todas_z = [p[1] for q in quadrados_processados for p in q]
    min_x, max_x = min(todas_x), max(todas_x)
    min_z, max_z = min(todas_z), max(todas_z)
    return quadrados_processados, min_x, min_z, (max_x - min_x), (max_z - min_z)

def create_track_surface(quadrados, min_x, min_z, larg_pista, alt_pista):
    surf = pygame.Surface((LARGURA_MAPA, ALTURA))
    surf.fill((20, 20, 25))
    for quad in quadrados:
        pts = [
            (50 + ((x - min_x) / larg_pista) * 700, 
             750 - ((z - min_z) / alt_pista) * 700) 
            for x, z in quad
        ]
        pygame.draw.polygon(surf, (80, 80, 80), pts, 1)
    return surf

def rodar():
    pygame.init()
    screen = pygame.display.set_mode((LARGURA_TOTAL, ALTURA))
    pygame.display.set_caption("STK Live")
    
    font_nome = pygame.font.SysFont("Arial", 12, bold=True)
    font_lb = pygame.font.SysFont("Verdana", 18, bold=True)
    font_stats = pygame.font.SysFont("Courier New", 14)
    
    current_track_id = ""
    quadrados = []
    track_surface = None
    min_x = min_z = 0
    larg_pista = alt_pista = 1

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORTA_UDP))
    sock.setblocking(False)

    IP_DO_SERVIDOR = "127.0.0.1" 
    print(f"Tentando conectar ao servidor STK em {IP_DO_SERVIDOR}...")
    sock.sendto(b"MAP_CONNECT", (IP_DO_SERVIDOR, 9998))

    jogadores = {} # { nome: {'x': x, 'z': z, 'kart': kart} }

    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        
        try:
            while True:
                data, addr = sock.recvfrom(1024)
                try:
                    mensagem = data.decode('utf-8', errors='ignore').strip()
                except:
                    continue

                if "|" not in mensagem:
                    continue
                parts = mensagem.split("|")
                if len(parts) < 5: continue
                
                t_id, nome, kart, kx, kz = parts
                
                if t_id != current_track_id:
                    quadrados, min_x, min_z, larg_pista, alt_pista = loadXML(t_id)
                    track_surface = create_track_surface(quadrados, min_x, min_z, larg_pista, alt_pista)
                    current_track_id = t_id

                jogadores[nome] = {'x': float(kx), 'z': float(kz), 'kart': kart}
        except BlockingIOError:
            pass

        screen.fill((40, 40, 50)) 
        if track_surface:
            screen.blit(track_surface, (0, 0))
        else:
            pygame.draw.rect(screen, (20, 20, 25), (0, 0, LARGURA_MAPA, ALTURA))

        lbl_titulo = font_lb.render("LEADERBOARD", True, (255, 215, 0))
        screen.blit(lbl_titulo, (LARGURA_MAPA + 20, 20))
        pygame.draw.line(screen, (255, 215, 0), (LARGURA_MAPA + 20, 50), (LARGURA_TOTAL - 20, 50), 2)

        y_offset = 70
        for i, nome in enumerate(sorted(jogadores.keys())):
            dados = jogadores[nome]
            
            cor_bg = (60, 60, 75) if i % 2 == 0 else (50, 50, 65)
            pygame.draw.rect(screen, cor_bg, (LARGURA_MAPA + 10, y_offset, LARGURA_LATERAL - 20, 45), border_radius=5)
            
            txt_player = font_stats.render(f"{i+1}. {nome[:12]}", True, (255, 255, 255))
            txt_kart = font_stats.render(f"Kart: {dados['kart']}", True, (200, 200, 200))
            
            screen.blit(txt_player, (LARGURA_MAPA + 20, y_offset + 5))
            screen.blit(txt_kart, (LARGURA_MAPA + 20, y_offset + 22))
            
            y_offset += 55

        for nome, dados in jogadores.items():
            px = 50 + ((dados['x'] - min_x) / larg_pista) * 700
            py = 750 - ((dados['z'] - min_z) / alt_pista) * 700
            
            pygame.draw.circle(screen, (255, 255, 255), (int(px), int(py)), 9, 1)
            pygame.draw.circle(screen, (255, 140, 0), (int(px), int(py)), 7)
            
            txt_mapa = font_nome.render(nome, True, (255, 255, 255))
            screen.blit(txt_mapa, (int(px) + 10, int(py) - 10))

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    rodar()
