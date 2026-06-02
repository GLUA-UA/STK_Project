#!/usr/bin/env python3

import os
import socket
import xml.etree.ElementTree as ET
from datetime import datetime

import pygame

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "stk-assets", "tracks")
SCORES_DIR = os.path.join(SCRIPT_DIR, "pontuacoes")

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9998
CLIENT_PORT = 9999

WINDOW_SIZE = (1100, 800)
MIN_SIZE = (700, 500)
FPS = 60

BG = (12, 12, 14)
TRACK_BG = (18, 18, 20)
TRACK_LINE = (80, 80, 86)
ROW_A = (36, 37, 44)
ROW_B = (28, 29, 35)
ORANGE = (255, 145, 40)
TEXT = (240, 240, 240)
MUTED = (160, 160, 168)


def load_track(track_id):
    path = os.path.join(ASSETS_DIR, track_id, "quads.xml")
    if not os.path.exists(path):
        print(f"[ERRO] Pista nao encontrada: {path}")
        return None

    quads = []
    root = ET.parse(path).getroot()

    for quad in root.findall("quad"):
        points = []
        for i in range(4):
            value = quad.attrib[f"p{i}"]
            if ":" in value:
                quad_index, point_index = map(int, value.split(":"))
                points.append(quads[quad_index][point_index])
            else:
                x, _, z = map(float, value.split())
                points.append((x, z))
        quads.append(points)

    xs = [x for quad in quads for x, _ in quad]
    zs = [z for quad in quads for _, z in quad]

    return {
        "quads": quads,
        "min_x": min(xs),
        "min_z": min(zs),
        "width": max(xs) - min(xs),
        "height": max(zs) - min(zs),
    }


def world_to_screen(track, x, z, rect):
    padding = 30
    track_width = track["width"] or 1
    track_height = track["height"] or 1
    scale = min(
        (rect.width - padding * 2) / track_width,
        (rect.height - padding * 2) / track_height,
    )
    offset_x = rect.x + (rect.width - track_width * scale) / 2
    offset_y = rect.y + (rect.height - track_height * scale) / 2
    screen_x = offset_x + (x - track["min_x"]) * scale
    screen_y = rect.bottom - (offset_y - rect.y + (z - track["min_z"]) * scale)
    return int(screen_x), int(screen_y)


def fit_text(font, text, width):
    if font.size(text)[0] <= width:
        return text
    while text and font.size(text + "...")[0] > width:
        text = text[:-1]
    return text + "..." if text else "..."


def sorted_players(players):
    return sorted(
        players.items(),
        key=lambda item: (
            item[1]["pos"] is None,
            item[1]["pos"] if item[1]["pos"] is not None else 999999,
            item[0].lower(),
        ),
    )


def open_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", CLIENT_PORT))
    sock.setblocking(False)
    sock.sendto(b"MAP_CONNECT", (SERVER_IP, SERVER_PORT))
    return sock


def parse_packet(data):
    parts = data.decode(errors="ignore").strip().split("|")
    if len(parts) < 5:
        return None

    track_id, name, kart, x, z = parts[:5]
    pos = None

    if len(parts) >= 6:
        try:
            pos = int(parts[5])
        except ValueError:
            pass

    return track_id, name, {
        "kart": kart,
        "x": float(x),
        "z": float(z),
        "pos": pos,
    }


def read_packets(sock, players, track_id):
    new_track_id = track_id

    try:
        while True:
            packet = parse_packet(sock.recvfrom(1024)[0])
            if not packet:
                continue

            received_track_id, name, data = packet
            if received_track_id != track_id:
                players.clear()
                new_track_id = received_track_id

            players[name] = data
    except BlockingIOError:
        pass

    return new_track_id


def draw_track(screen, track, rect):
    pygame.draw.rect(screen, TRACK_BG, rect)
    if not track:
        return

    for quad in track["quads"]:
        points = [world_to_screen(track, x, z, rect) for x, z in quad]
        pygame.draw.polygon(screen, TRACK_LINE, points, 1)


def draw_players(screen, track, players, rect, font):
    if not track:
        return

    for name, data in players.items():
        x, y = world_to_screen(track, data["x"], data["z"], rect)
        pygame.draw.circle(screen, ORANGE, (x, y), 7)
        label = font.render(fit_text(font, name, 90), True, TEXT)
        screen.blit(label, (x + 10, y - 10))


def draw_leaderboard(screen, players, rect, fonts):
    title_font, name_font, small_font = fonts
    pygame.draw.rect(screen, BG, rect)

    title = title_font.render("LEADERBOARD", True, ORANGE)
    screen.blit(title, (rect.x + 15, 18))

    row_height = 52
    y = rect.y + 60
    player_list = sorted_players(players)
    max_rows = max(0, (rect.height - 95) // row_height)

    for index, (name, data) in enumerate(player_list[:max_rows]):
        row = pygame.Rect(rect.x + 10, y, rect.width - 20, row_height)
        color = ROW_A if index % 2 == 0 else ROW_B
        pygame.draw.rect(screen, color, row, border_radius=6)

        pos = data["pos"] if data["pos"] is not None else "?"
        name_text = fit_text(name_font, f"{pos}. {name}", row.width - 20)
        kart_text = fit_text(small_font, f"Kart: {data['kart']}", row.width - 20)

        screen.blit(name_font.render(name_text, True, ORANGE), (row.x + 10, row.y + 6))
        screen.blit(small_font.render(kart_text, True, TEXT), (row.x + 10, row.y + 30))
        y += row_height + 8

    hidden = len(player_list) - max_rows
    if hidden > 0:
        footer = small_font.render(f"+{hidden} jogadores", True, MUTED)
        screen.blit(footer, (rect.x + 15, rect.bottom - 25))


def save_scores(players, track_id):
    if not players:
        return

    os.makedirs(SCORES_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(SCORES_DIR, f"{track_id or 'unknown'}_{timestamp}.txt")

    with open(path, "w", encoding="utf-8") as file:
        file.write(f"track: {track_id or 'unknown'}\n")
        file.write(f"saved_at: {datetime.now().isoformat(timespec='seconds')}\n\n")
        for index, (name, data) in enumerate(sorted_players(players), start=1):
            pos = data["pos"] if data["pos"] is not None else "?"
            file.write(f"{index}. nome={name} kart={data['kart']} pos={pos}\n")

    print(f"[INFO] Pontuacoes guardadas em: {path}")


def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("STK Live")

    title_font = pygame.font.SysFont("Arial", 20, bold=True)
    name_font = pygame.font.SysFont("Arial", 16, bold=True)
    small_font = pygame.font.SysFont("Arial", 12)
    clock = pygame.time.Clock()

    sock = open_socket()
    players = {}
    track_id = ""
    track = None
    window_size = WINDOW_SIZE

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
                if event.type == pygame.VIDEORESIZE:
                    window_size = (max(event.w, MIN_SIZE[0]), max(event.h, MIN_SIZE[1]))
                    screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)

            new_track_id = read_packets(sock, players, track_id)
            if new_track_id != track_id:
                track_id = new_track_id
                track = load_track(track_id)

            width, height = window_size
            sidebar_width = min(280, max(220, width // 4))
            map_rect = pygame.Rect(0, 0, width - sidebar_width, height)
            leaderboard_rect = pygame.Rect(map_rect.right, 0, sidebar_width, height)

            screen.fill(BG)
            draw_track(screen, track, map_rect)
            draw_players(screen, track, players, map_rect, small_font)
            draw_leaderboard(screen, players, leaderboard_rect, (title_font, name_font, small_font))

            pygame.display.flip()
            clock.tick(FPS)
    finally:
        save_scores(players, track_id)
        sock.close()
        pygame.quit()


if __name__ == "__main__":
    main()
