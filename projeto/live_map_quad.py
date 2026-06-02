#!/usr/bin/env python3

import os
import socket
import xml.etree.ElementTree as ET
from datetime import datetime

import pygame

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "stk-assets", "tracks")
SCORES_DIR = os.path.join(SCRIPT_DIR, "pontuacoes")

SERVER_CONFIGS = [
    {"label": "Server 1", "server_ip": "127.0.0.1", "server_port": 9998},
    {"label": "Server 2", "server_ip": "192.168.55.86", "server_port": 9998},
    {"label": "Server 3", "server_ip": "127.0.0.1", "server_port": 9998},
    {"label": "Server 4", "server_ip": "172.20.10.4", "server_port": 9998},
]

CLIENT_PORT = 9999
WINDOW_SIZE = (1400, 850)
MIN_SIZE = (900, 520)
FPS = 60

BG = (12, 12, 14)
CARD = (28, 29, 35)
TRACK_BG = (18, 18, 20)
TRACK_LINE = (80, 80, 86)
ROW_A = (38, 40, 48)
ROW_B = (31, 32, 39)
ORANGE = (255, 145, 40)
TEXT = (240, 240, 240)
MUTED = (160, 160, 168)


def load_track(track_id):
    path = os.path.join(ASSETS_DIR, track_id, "quads.xml")
    if not os.path.exists(path):
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
    padding = 20
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

    for server in SERVER_CONFIGS:
        try:
            sock.sendto(b"MAP_CONNECT", (server["server_ip"], server["server_port"]))
            print(
                f"[INFO] Pedido enviado para {server['label']} "
                f"{server['server_ip']}:{server['server_port']}"
            )
        except OSError as error:
            print(f"[WARN] {server['label']} nao recebeu pedido: {error}")

    return sock


def make_states():
    return [
        {
            "label": server["label"],
            "server_ip": server["server_ip"],
            "track_id": "",
            "track": None,
            "players": {},
        }
        for server in SERVER_CONFIGS
    ]


def find_state(states, ip):
    for state in states:
        if state["server_ip"] == ip:
            return state
    return None


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


def read_packets(sock, states):
    try:
        while True:
            data, address = sock.recvfrom(1024)
            state = find_state(states, address[0])
            packet = parse_packet(data)

            if not state or not packet:
                continue

            track_id, name, player = packet
            if track_id != state["track_id"]:
                state["track_id"] = track_id
                state["track"] = load_track(track_id)
                state["players"].clear()

            state["players"][name] = player
    except BlockingIOError:
        pass


def card_rects(window_size):
    width, height = window_size
    margin = 20
    gap = 20
    card_width = (width - margin * 2 - gap) // 2
    card_height = (height - margin * 2 - gap) // 2
    rects = []

    for row in range(2):
        for col in range(2):
            x = margin + col * (card_width + gap)
            y = margin + row * (card_height + gap)
            rects.append(pygame.Rect(x, y, card_width, card_height))

    return rects


def draw_card(screen, rect, state, fonts):
    title_font, name_font, small_font = fonts
    pygame.draw.rect(screen, CARD, rect, border_radius=8)

    title = title_font.render(state["label"], True, ORANGE)
    subtitle = small_font.render(
        f"{state['track_id'] or 'sem dados'} | {state['server_ip']}",
        True,
        MUTED,
    )
    screen.blit(title, (rect.x + 15, rect.y + 12))
    screen.blit(subtitle, (rect.x + 15, rect.y + 38))

    map_rect = pygame.Rect(rect.x + 15, rect.y + 65, int(rect.width * 0.58), rect.height - 82)
    board_rect = pygame.Rect(
        map_rect.right + 15,
        map_rect.y,
        rect.right - map_rect.right - 30,
        map_rect.height,
    )

    draw_track(screen, state["track"], map_rect)
    draw_players(screen, state["track"], state["players"], map_rect, small_font)
    draw_leaderboard(screen, state["players"], board_rect, name_font, small_font)


def draw_track(screen, track, rect):
    pygame.draw.rect(screen, TRACK_BG, rect, border_radius=6)
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
        pygame.draw.circle(screen, ORANGE, (x, y), 5)
        label = font.render(fit_text(font, name, 70), True, TEXT)
        screen.blit(label, (x + 8, y - 8))


def draw_leaderboard(screen, players, rect, name_font, small_font):
    player_list = sorted_players(players)
    row_height = 40
    y = rect.y
    max_rows = max(0, rect.height // row_height)

    for index, (name, data) in enumerate(player_list[:max_rows]):
        row = pygame.Rect(rect.x, y, rect.width, row_height - 4)
        color = ROW_A if index % 2 == 0 else ROW_B
        pygame.draw.rect(screen, color, row, border_radius=5)

        pos = data["pos"] if data["pos"] is not None else "?"
        name_text = fit_text(name_font, f"{pos}. {name}", row.width - 12)
        kart_text = fit_text(small_font, data["kart"], row.width - 12)

        screen.blit(name_font.render(name_text, True, ORANGE), (row.x + 6, row.y + 4))
        screen.blit(small_font.render(kart_text, True, TEXT), (row.x + 6, row.y + 22))
        y += row_height + 6

    hidden = len(player_list) - max_rows
    if hidden > 0:
        footer = small_font.render(f"+{hidden} jogadores", True, MUTED)
        screen.blit(footer, (rect.x, rect.bottom - 18))


def save_scores(states):
    os.makedirs(SCORES_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(SCORES_DIR, f"quad_servers_{timestamp}.txt")

    with open(path, "w", encoding="utf-8") as file:
        for state in states:
            file.write(f"[{state['label']}] track={state['track_id'] or 'unknown'}\n")
            for index, (name, data) in enumerate(sorted_players(state["players"]), start=1):
                pos = data["pos"] if data["pos"] is not None else "?"
                file.write(f"{index}. nome={name} kart={data['kart']} pos={pos}\n")
            file.write("\n")

    print(f"[INFO] Pontuacoes guardadas em: {path}")


def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("STK Live Quad")

    title_font = pygame.font.SysFont("Arial", 16, bold=True)
    name_font = pygame.font.SysFont("Arial", 13, bold=True)
    small_font = pygame.font.SysFont("Arial", 11)
    clock = pygame.time.Clock()

    sock = open_socket()
    states = make_states()
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

            read_packets(sock, states)

            screen.fill(BG)
            for rect, state in zip(card_rects(window_size), states):
                draw_card(screen, rect, state, (title_font, name_font, small_font))

            pygame.display.flip()
            clock.tick(FPS)
    finally:
        save_scores(states)
        sock.close()
        pygame.quit()


if __name__ == "__main__":
    main()
