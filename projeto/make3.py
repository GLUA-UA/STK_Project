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
MIN_WINDOW_WIDTH = 700
MIN_WINDOW_HEIGHT = 520

WARNED_MISSING_POS = False

# CORES
COLOR_BG = (10, 10, 10)
COLOR_ALT1 = (35, 35, 35)
COLOR_ALT2 = (25, 25, 25)
COLOR_ORANGE = (255, 140, 0)
COLOR_ORANGE_SOFT = (255, 180, 80)
COLOR_TEXT = (240, 240, 240)
COLOR_MUTED = (160, 160, 160)

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


def get_layout(window_size):
    width, height = window_size
    sidebar_width = min(320, max(230, int(width * 0.25)))
    map_width = max(320, width - sidebar_width)
    return {
        "map_rect": pygame.Rect(0, 0, map_width, height),
        "sidebar_rect": pygame.Rect(map_width, 0, sidebar_width, height),
    }


def track_to_screen(track, x, z, rect):
    track_w = track["width"] if track["width"] > 0 else 1.0
    track_h = track["height"] if track["height"] > 0 else 1.0
    padding = max(24, min(rect.width, rect.height) * 0.06)
    usable_w = max(1, rect.width - padding * 2)
    usable_h = max(1, rect.height - padding * 2)
    scale = min(usable_w / track_w, usable_h / track_h)
    offset_x = rect.x + (rect.width - track_w * scale) / 2
    offset_y = rect.y + (rect.height - track_h * scale) / 2
    px = offset_x + ((x - track["min_x"]) * scale)
    py = rect.y + rect.height - (offset_y - rect.y + ((z - track["min_z"]) * scale))
    return px, py


def build_track_surface(track, size):
    width, height = size
    surface = pygame.Surface((width, height))
    surface.fill((15, 15, 15))
    rect = surface.get_rect()

    for quad in track["quads"]:
        pts = [track_to_screen(track, x, z, rect) for x, z in quad]
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
def fit_text(font, text, max_width):
    if font.size(text)[0] <= max_width:
        return text

    words = text.split()
    fitted = ""

    for word in words:
        candidate = word if not fitted else f"{fitted} {word}"
        if font.size(f"{candidate}...")[0] <= max_width:
            fitted = candidate
        else:
            break

    if fitted:
        return f"{fitted}..."

    trimmed = text
    while trimmed and font.size(f"{trimmed}...")[0] > max_width:
        trimmed = trimmed[:-1]
    return f"{trimmed}..." if trimmed else "..."


def draw_map(screen, surface, map_rect):
    if surface:
        screen.blit(surface, map_rect.topleft)
    else:
        pygame.draw.rect(screen, (15, 15, 15), map_rect)


def draw_leaderboard(screen, jogadores, font_title, font_name, font_kart, sidebar_rect):
    old_clip = screen.get_clip()
    screen.set_clip(sidebar_rect)

    title = font_title.render("LEADERBOARD", True, COLOR_ORANGE)
    screen.blit(title, (sidebar_rect.x + 20, 20))

    pygame.draw.line(screen, COLOR_ORANGE,
                     (sidebar_rect.x + 20, 50),
                     (sidebar_rect.right - 20, 50), 2)

    start_y = 70
    row_height = 50
    row_gap = 10
    y = start_y
    text_width = sidebar_rect.width - 40
    players_sorted = get_sorted_players(jogadores)
    max_rows = max(0, (sidebar_rect.height - start_y - 32) // (row_height + row_gap))
    visible_players = players_sorted[:max_rows]

    for i, (nome, dados) in enumerate(visible_players):
        bg = COLOR_ALT1 if i % 2 == 0 else COLOR_ALT2

        pygame.draw.rect(
            screen,
            bg,
            (sidebar_rect.x + 10, y, sidebar_rect.width - 20, row_height),
            border_radius=6,
        )

        display_pos = dados.get('pos')
        pos_label = f"{display_pos}." if display_pos is not None else "?."
        player_text = fit_text(font_name, f"{pos_label} {nome}", text_width)
        kart_text = fit_text(font_kart, f"Kart: {dados['kart']}", text_width)
        player = font_name.render(player_text, True, COLOR_ORANGE_SOFT)
        kart = font_kart.render(kart_text, True, COLOR_TEXT)

        screen.blit(player, (sidebar_rect.x + 20, y + 5))
        screen.blit(kart, (sidebar_rect.x + 20, y + 28))

        y += row_height + row_gap

    hidden_count = len(players_sorted) - len(visible_players)
    if hidden_count > 0:
        footer_text = fit_text(font_kart, f"+{hidden_count} jogadores fora da vista", text_width)
        footer = font_kart.render(footer_text, True, COLOR_MUTED)
        screen.blit(footer, (sidebar_rect.x + 20, sidebar_rect.bottom - 26))

    screen.set_clip(old_clip)


def draw_players(screen, jogadores, track, font, map_rect):
    if not track:
        return

    for nome, dados in jogadores.items():
        px, py = track_to_screen(track, dados["x"], dados["z"], map_rect)

        pygame.draw.circle(screen, (255, 255, 255), (int(px), int(py)), 9, 1)
        pygame.draw.circle(screen, COLOR_ORANGE, (int(px), int(py)), 7)

        label = font.render(nome, True, COLOR_TEXT)
        screen.blit(label, (int(px) + 10, int(py) - 10))


# ================= MAIN =================
def main():
    pygame.init()

    window_size = (WINDOW_WIDTH, HEIGHT)
    screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)
    pygame.display.set_caption("STK Live")

    font_small = pygame.font.SysFont("Arial", 12, bold=True)
    font_title = pygame.font.SysFont("Orbitron", 20, bold=True)
    font_name = pygame.font.SysFont("Segoe UI", 16, bold=True)
    font_kart = pygame.font.SysFont("Consolas", 12)

    sock = setup_socket()

    jogadores = {}
    track = None
    track_surface = None
    current_track_id = ""
    layout = get_layout(window_size)

    clock = pygame.time.Clock()

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.VIDEORESIZE:
                    window_size = (
                        max(event.w, MIN_WINDOW_WIDTH),
                        max(event.h, MIN_WINDOW_HEIGHT),
                    )
                    screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)
                    layout = get_layout(window_size)
                    if track:
                        track_surface = build_track_surface(
                            track,
                            (layout["map_rect"].width, layout["map_rect"].height),
                        )

            new_track_id = receive_packets(sock, jogadores, current_track_id)

            if new_track_id:
                track = load_track(new_track_id)
                if track:
                    track_surface = build_track_surface(
                        track,
                        (layout["map_rect"].width, layout["map_rect"].height),
                    )
                    current_track_id = new_track_id

            screen.fill(COLOR_BG)

            draw_map(screen, track_surface, layout["map_rect"])
            draw_leaderboard(screen, jogadores, font_title, font_name, font_kart, layout["sidebar_rect"])
            draw_players(screen, jogadores, track, font_small, layout["map_rect"])

            pygame.display.flip()
            clock.tick(60)
    finally:
        save_leaderboard(jogadores, current_track_id)
        sock.close()
        pygame.quit()


if __name__ == "__main__":
    main()
