#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import pygame
import sys
import socket
import os
from datetime import datetime

# ================= CONFIG =================
BASE_ASSETS = "stk-assets/tracks/"
UDP_PORT = 9999
SERVER_IP = "127.0.0.1"
SERVER_PORT = 9998

MAP_WIDTH = 800
SIDEBAR_WIDTH = 250
HEIGHT = 800
WINDOW_WIDTH = MAP_WIDTH + SIDEBAR_WIDTH

WARNED_MISSING_POS = False

# CORES
COLOR_BG = (10, 10, 10)
COLOR_ALT1 = (35, 35, 35)
COLOR_ALT2 = (25, 25, 25)
COLOR_ORANGE = (255, 140, 0)
COLOR_ORANGE_SOFT = (255, 180, 80)
COLOR_TEXT = (240, 240, 240)

# ================= TRACK =================
def load_track(track_id):
    xml_path = os.path.join(BASE_ASSETS, track_id, "quads.xml")

    if not os.path.exists(xml_path):
        print(f"[ERRO] Track não encontrada: {xml_path}")
        return None

    tree = ET.parse(xml_path)
    root = tree.getroot()

    quads = []

    for quad in root.findall('quad'):
        pontos = []

        for i in range(4):
            value = quad.attrib[f'p{i}']

            if ":" in value:
                idx, pt = map(int, value.split(":"))
                pontos.append(quads[idx][pt])
            else:
                x, _, z = map(float, value.split())
                pontos.append((x, z))

        quads.append(pontos)

    xs = [p[0] for q in quads for p in q]
    zs = [p[1] for q in quads for p in q]

    return {
        "quads": quads,
        "min_x": min(xs),
        "min_z": min(zs),
        "width": max(xs) - min(xs),
        "height": max(zs) - min(zs)
    }


def build_track_surface(track):
    surface = pygame.Surface((MAP_WIDTH, HEIGHT))
    surface.fill((15, 15, 15))

    for quad in track["quads"]:
        pts = [
            (
                50 + ((x - track["min_x"]) / track["width"]) * 700,
                750 - ((z - track["min_z"]) / track["height"]) * 700
            )
            for x, z in quad
        ]
        pygame.draw.polygon(surface, (70, 70, 70), pts, 1)

    return surface


# ================= NETWORK =================
def setup_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    sock.setblocking(False)

    sock.sendto(b"MAP_CONNECT", (SERVER_IP, SERVER_PORT))
    return sock


def receive_packets(sock, jogadores, current_track_id):
    global WARNED_MISSING_POS

    new_track = None

    try:
        while True:
            data, _ = sock.recvfrom(1024)

            try:
                msg = data.decode().strip()
            except:
                continue

            if "|" not in msg:
                continue

            parts = msg.split("|")

            if len(parts) < 5:
                continue

            track_id, nome, kart, x, z = parts[:5]
            pos = None

            if len(parts) >= 6:
                try:
                    pos = int(parts[5].strip())
                except ValueError:
                    pos = None
            elif not WARNED_MISSING_POS:
                print(f"[WARN] Pacote sem pos recebido: {msg}")
                print('[WARN] O cliente continua compatível, mas a leaderboard nao pode usar a classificacao real sem o 6.o campo.')
                WARNED_MISSING_POS = True

            if track_id != current_track_id:
                new_track = track_id
                jogadores.clear()

            jogadores[nome] = {
                "x": float(x),
                "z": float(z),
                "kart": kart,
                "pos": pos
            }

    except BlockingIOError:
        pass

    return new_track


def get_sorted_players(jogadores):
    return sorted(
        jogadores.items(),
        key=lambda item: (
            item[1].get('pos') is None,
            item[1].get('pos') if item[1].get('pos') is not None else 999999,
            item[0].lower()
        )
    )


def save_leaderboard(jogadores, track_id):
    if not jogadores:
        return

    os.makedirs("pontuacoes", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_track = track_id or "unknown_track"
    file_path = os.path.join("pontuacoes", f"{safe_track}_{timestamp}.txt")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"track: {safe_track}\n")
        f.write(f"saved_at: {datetime.now().isoformat(timespec='seconds')}\n\n")

        for idx, (nome, dados) in enumerate(get_sorted_players(jogadores), start=1):
            race_pos = dados.get("pos")
            pos_text = str(race_pos) if race_pos is not None else "?"
            f.write(
                f"{idx}. nome={nome} kart={dados['kart']} pos={pos_text} "
                f"x={dados['x']:.3f} z={dados['z']:.3f}\n"
            )

    print(f"[INFO] Pontuacoes guardadas em: {file_path}")


# ================= RENDER =================
def draw_map(screen, surface):
    if surface:
        screen.blit(surface, (0, 0))
    else:
        pygame.draw.rect(screen, (15, 15, 15), (0, 0, MAP_WIDTH, HEIGHT))


def draw_leaderboard(screen, jogadores, font_title, font_name, font_kart):
    title = font_title.render("LEADERBOARD", True, COLOR_ORANGE)
    screen.blit(title, (MAP_WIDTH + 20, 20))

    pygame.draw.line(screen, COLOR_ORANGE,
                     (MAP_WIDTH + 20, 50),
                     (WINDOW_WIDTH - 20, 50), 2)

    y = 70

    players_sorted = get_sorted_players(jogadores)

    for i, (nome, dados) in enumerate(players_sorted):
        bg = COLOR_ALT1 if i % 2 == 0 else COLOR_ALT2

        pygame.draw.rect(screen, bg,
                         (MAP_WIDTH + 10, y, SIDEBAR_WIDTH - 20, 50),
                         border_radius=6)

        display_pos = dados.get('pos')
        pos_label = f"{display_pos}." if display_pos is not None else "?."
        player = font_name.render(f"{pos_label} {nome[:12]}", True, COLOR_ORANGE_SOFT)
        kart = font_kart.render(f"Kart: {dados['kart']}", True, COLOR_TEXT)

        screen.blit(player, (MAP_WIDTH + 20, y + 5))
        screen.blit(kart, (MAP_WIDTH + 20, y + 28))

        y += 60


def draw_players(screen, jogadores, track, font):
    if not track:
        return

    for nome, dados in jogadores.items():
        px = 50 + ((dados['x'] - track["min_x"]) / track["width"]) * 700
        py = 750 - ((dados['z'] - track["min_z"]) / track["height"]) * 700

        pygame.draw.circle(screen, (255, 255, 255), (int(px), int(py)), 9, 1)
        pygame.draw.circle(screen, COLOR_ORANGE, (int(px), int(py)), 7)

        label = font.render(nome, True, COLOR_TEXT)
        screen.blit(label, (int(px) + 10, int(py) - 10))


# ================= MAIN =================
def main():
    pygame.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, HEIGHT))
    pygame.display.set_caption("STK Live")

    font_small = pygame.font.SysFont("Arial", 12, bold=True)
    font_title = pygame.font.SysFont("Orbitron", 20, bold=True)
    font_name = pygame.font.SysFont("Segoe UI", 18, bold=True)
    font_kart = pygame.font.SysFont("Consolas", 14)

    sock = setup_socket()

    jogadores = {}
    track = None
    track_surface = None
    current_track_id = ""

    clock = pygame.time.Clock()

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

            new_track_id = receive_packets(sock, jogadores, current_track_id)

            if new_track_id:
                track = load_track(new_track_id)
                if track:
                    track_surface = build_track_surface(track)
                    current_track_id = new_track_id

            screen.fill(COLOR_BG)

            draw_map(screen, track_surface)
            draw_leaderboard(screen, jogadores, font_title, font_name, font_kart)
            draw_players(screen, jogadores, track, font_small)

            pygame.display.flip()
            clock.tick(60)
    finally:
        save_leaderboard(jogadores, current_track_id)
        sock.close()
        pygame.quit()


if __name__ == "__main__":
    main()
