#!/usr/bin/env python3

import os
import socket
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

import pygame

BASE_ASSETS = "stk-assets/tracks/"
UDP_PORT = 9999
SERVER_CONFIGS = [
    {"label": "Server 1", "server_ip": "127.0.0.1", "server_port": 9998},
    {"label": "Server 2", "server_ip": "192.168.55.86", "server_port": 9998},
]

MAP_WIDTH = 680
SIDEBAR_WIDTH = 260
PANEL_WIDTH = MAP_WIDTH + SIDEBAR_WIDTH
HEIGHT = 1080
WINDOW_WIDTH = 1920
TOP_MARGIN = 40
BOTTOM_MARGIN = 40
MAP_INSET_X = 36
MAP_INSET_Y = 96
MAP_DRAW_WIDTH = MAP_WIDTH - MAP_INSET_X * 2
MAP_DRAW_HEIGHT = HEIGHT - TOP_MARGIN - BOTTOM_MARGIN - MAP_INSET_Y
COLOR_BG = (10, 10, 10)
COLOR_ALT1 = (35, 35, 35)
COLOR_ALT2 = (25, 25, 25)
COLOR_ORANGE = (255, 140, 0)
COLOR_ORANGE_SOFT = (255, 180, 80)
COLOR_TEXT = (240, 240, 240)
COLOR_MUTED = (160, 160, 160)
WARNED_MISSING_POS = set()


def load_track(track_id):
    xml_path = os.path.join(BASE_ASSETS, track_id, "quads.xml")
    if not os.path.exists(xml_path):
        print(f"[ERRO] Track nao encontrada: {xml_path}")
        return None

    tree = ET.parse(xml_path)
    root = tree.getroot()
    quads = []

    for quad in root.findall("quad"):
        pontos = []
        for i in range(4):
            value = quad.attrib[f"p{i}"]
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
        "height": max(zs) - min(zs),
    }


def build_track_surface(track):
    surface = pygame.Surface((MAP_WIDTH, HEIGHT))
    surface.fill((15, 15, 15))

    for quad in track["quads"]:
        pts = [
            (
                MAP_INSET_X + ((x - track["min_x"]) / track["width"]) * MAP_DRAW_WIDTH,
                HEIGHT - BOTTOM_MARGIN - ((z - track["min_z"]) / track["height"]) * MAP_DRAW_HEIGHT,
            )
            for x, z in quad
        ]
        pygame.draw.polygon(surface, (70, 70, 70), pts, 1)

    return surface


def normalize_sender_ip(ip):
    if ip == "::ffff:127.0.0.1" or ip == "::1":
        return "127.0.0.1"
    return ip


def setup_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    sock.setblocking(False)

    for config in SERVER_CONFIGS:
        sock.sendto(b"MAP_CONNECT", (config["server_ip"], config["server_port"]))
        print(f"[INFO] {config['label']} -> {config['server_ip']}:{config['server_port']}")

    return sock


def build_ip_map():
    return {config["server_ip"]: config["label"] for config in SERVER_CONFIGS}


def process_packet(config, state, msg):
    if "|" not in msg:
        return

    parts = msg.split("|")
    if len(parts) < 5:
        return

    track_id, nome, kart, x, z = parts[:5]
    pos = None
    if len(parts) >= 6:
        try:
            pos = int(parts[5].strip())
        except ValueError:
            pos = None
    elif config["label"] not in WARNED_MISSING_POS:
        print(f"[WARN] {config['label']} sem pos no pacote: {msg}")
        WARNED_MISSING_POS.add(config["label"])

    if track_id != state["track_id"]:
        state["track_id"] = track_id
        state["track"] = load_track(track_id)
        state["track_surface"] = build_track_surface(state["track"]) if state["track"] else None
        state["players"].clear()

    state["players"][nome] = {
        "x": float(x),
        "z": float(z),
        "kart": kart,
        "pos": pos,
    }


def receive_packets(sock, states, ip_map):
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            sender_ip = normalize_sender_ip(addr[0])
            try:
                msg = data.decode().strip()
            except UnicodeDecodeError:
                continue

            if sender_ip not in ip_map:
                continue

            label = ip_map[sender_ip]
            state = states[label]
            process_packet(state["config"], state, msg)
    except BlockingIOError:
        return


def get_sorted_players(players):
    return sorted(
        players.items(),
        key=lambda item: (
            item[1].get("pos") is None,
            item[1].get("pos") if item[1].get("pos") is not None else 999999,
            item[0].lower(),
        ),
    )


def save_leaderboard(states):
    os.makedirs("pontuacoes", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.join("pontuacoes", f"duo_servers_{timestamp}.txt")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"saved_at: {datetime.now().isoformat(timespec='seconds')}\n\n")
        for label, state in states.items():
            f.write(f"[{label}] track={state['track_id'] or 'unknown'}\n")
            for idx, (name, data) in enumerate(get_sorted_players(state["players"]), start=1):
                pos_text = str(data.get("pos")) if data.get("pos") is not None else "?"
                f.write(
                    f"{idx}. nome={name} kart={data['kart']} pos={pos_text} "
                    f"x={data['x']:.3f} z={data['z']:.3f}\n"
                )
            f.write("\n")

    print(f"[INFO] Pontuacoes guardadas em: {file_path}")


def draw_map(screen, surface, x_offset):
    if surface:
        screen.blit(surface, (x_offset, 0))
    else:
        pygame.draw.rect(screen, (15, 15, 15), (x_offset, 0, MAP_WIDTH, HEIGHT))


def draw_players(screen, state, font, x_offset):
    track = state["track"]
    if not track:
        return

    for nome, dados in state["players"].items():
        px = x_offset + MAP_INSET_X + ((dados["x"] - track["min_x"]) / track["width"]) * MAP_DRAW_WIDTH
        py = HEIGHT - BOTTOM_MARGIN - ((dados["z"] - track["min_z"]) / track["height"]) * MAP_DRAW_HEIGHT
        pygame.draw.circle(screen, (255, 255, 255), (int(px), int(py)), 11, 1)
        pygame.draw.circle(screen, COLOR_ORANGE, (int(px), int(py)), 9)
        label = font.render(nome[:12], True, COLOR_TEXT)
        screen.blit(label, (int(px) + 12, int(py) - 12))


def draw_leaderboard(screen, state, font_title, font_name, font_kart, x_offset):
    panel_x = x_offset + MAP_WIDTH
    title = font_title.render(state["config"]["label"], True, COLOR_ORANGE)
    screen.blit(title, (panel_x + 20, 28))

    track_label = state["track_id"] or "sem dados"
    track_text = font_kart.render(f"Track: {track_label}", True, COLOR_MUTED)
    screen.blit(track_text, (panel_x + 20, 64))

    leaderboard_title = font_title.render("LEADERBOARD", True, COLOR_ORANGE)
    screen.blit(leaderboard_title, (panel_x + 20, 118))
    pygame.draw.line(
        screen,
        COLOR_ORANGE,
        (panel_x + 20, 154),
        (panel_x + SIDEBAR_WIDTH - 20, 154),
        3,
    )

    y = 178
    players_sorted = get_sorted_players(state["players"])

    for i, (nome, dados) in enumerate(players_sorted[:10]):
        bg = COLOR_ALT1 if i % 2 == 0 else COLOR_ALT2
        pygame.draw.rect(
            screen,
            bg,
            (panel_x + 10, y, SIDEBAR_WIDTH - 20, 64),
            border_radius=8,
        )

        pos_label = f"{dados['pos']}." if dados.get("pos") is not None else "?."
        player = font_name.render(f"{pos_label} {nome[:16]}", True, COLOR_ORANGE_SOFT)
        kart = font_kart.render(f"Kart: {dados['kart']}", True, COLOR_TEXT)
        screen.blit(player, (panel_x + 20, y + 7))
        screen.blit(kart, (panel_x + 20, y + 38))
        y += 76

    if not players_sorted:
        empty = font_kart.render("Sem jogadores recebidos.", True, COLOR_MUTED)
        screen.blit(empty, (panel_x + 20, 178))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, HEIGHT))
    pygame.display.set_caption("STK Live Duo")

    font_small = pygame.font.SysFont("Arial", 16, bold=True)
    font_title = pygame.font.SysFont("Orbitron", 24, bold=True)
    font_name = pygame.font.SysFont("Segoe UI", 22, bold=True)
    font_kart = pygame.font.SysFont("Consolas", 17)

    sock = setup_socket()
    ip_map = build_ip_map()

    states = {
        config["label"]: {
            "config": config,
            "track_id": "",
            "track": None,
            "track_surface": None,
            "players": {},
        }
        for config in SERVER_CONFIGS
    }

    clock = pygame.time.Clock()

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            receive_packets(sock, states, ip_map)

            screen.fill(COLOR_BG)
            for index, config in enumerate(SERVER_CONFIGS[:2]):
                x_offset = index * PANEL_WIDTH
                state = states[config["label"]]
                draw_map(screen, state["track_surface"], x_offset)
                draw_players(screen, state, font_small, x_offset)
                draw_leaderboard(screen, state, font_title, font_name, font_kart, x_offset)

            pygame.display.flip()
            clock.tick(60)
    finally:
        save_leaderboard(states)
        sock.close()
        pygame.quit()


if __name__ == "__main__":
    main()
