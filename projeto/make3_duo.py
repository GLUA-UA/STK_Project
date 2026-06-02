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
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 520
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


def get_panel_layout(window_size):
    width, height = window_size
    panel_width = width // 2
    sidebar_width = min(320, max(180, int(panel_width * 0.28)))
    map_width = max(240, panel_width - sidebar_width)
    if map_width + sidebar_width > panel_width:
        map_width = max(1, panel_width - sidebar_width)
    layouts = []

    for index in range(2):
        x = index * panel_width
        panel_rect = pygame.Rect(x, 0, panel_width, height)
        map_rect = pygame.Rect(x, 0, map_width, height)
        sidebar_rect = pygame.Rect(x + map_width, 0, sidebar_width, height)
        layouts.append({"panel": panel_rect, "map": map_rect, "sidebar": sidebar_rect})

    return layouts


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
        state["track_surface"] = None
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


def rebuild_track_surface(state, map_rect):
    if state["track"] and state["track_surface"] is None:
        state["track_surface"] = build_track_surface(state["track"], (map_rect.width, map_rect.height))


def draw_map(screen, surface, map_rect):
    if surface:
        screen.blit(surface, map_rect.topleft)
    else:
        pygame.draw.rect(screen, (15, 15, 15), map_rect)


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


def draw_players(screen, state, font, map_rect):
    track = state["track"]
    if not track:
        return

    for nome, dados in state["players"].items():
        px, py = track_to_screen(track, dados["x"], dados["z"], map_rect)
        pygame.draw.circle(screen, (255, 255, 255), (int(px), int(py)), 11, 1)
        pygame.draw.circle(screen, COLOR_ORANGE, (int(px), int(py)), 9)
        label = font.render(nome[:12], True, COLOR_TEXT)
        screen.blit(label, (int(px) + 12, int(py) - 12))


def draw_leaderboard(screen, state, font_title, font_name, font_kart, sidebar_rect):
    old_clip = screen.get_clip()
    screen.set_clip(sidebar_rect)

    panel_x = sidebar_rect.x
    text_width = sidebar_rect.width - 40
    title = font_title.render(fit_text(font_title, state["config"]["label"], text_width), True, COLOR_ORANGE)
    screen.blit(title, (panel_x + 20, 28))

    track_label = state["track_id"] or "sem dados"
    track_text = font_kart.render(fit_text(font_kart, f"Track: {track_label}", text_width), True, COLOR_MUTED)
    screen.blit(track_text, (panel_x + 20, 64))

    leaderboard_title = font_title.render("LEADERBOARD", True, COLOR_ORANGE)
    screen.blit(leaderboard_title, (panel_x + 20, 118))
    pygame.draw.line(
        screen,
        COLOR_ORANGE,
        (panel_x + 20, 154),
        (sidebar_rect.right - 20, 154),
        3,
    )

    start_y = 178
    row_height = 54
    row_gap = 8
    y = start_y
    players_sorted = get_sorted_players(state["players"])
    max_rows = max(0, (sidebar_rect.height - start_y - 32) // (row_height + row_gap))
    visible_players = players_sorted[:max_rows]

    for i, (nome, dados) in enumerate(visible_players):
        bg = COLOR_ALT1 if i % 2 == 0 else COLOR_ALT2
        pygame.draw.rect(
            screen,
            bg,
            (panel_x + 10, y, sidebar_rect.width - 20, row_height),
            border_radius=8,
        )

        pos_label = f"{dados['pos']}." if dados.get("pos") is not None else "?."
        player_text = fit_text(font_name, f"{pos_label} {nome}", text_width)
        kart_text = fit_text(font_kart, f"Kart: {dados['kart']}", text_width)
        player = font_name.render(player_text, True, COLOR_ORANGE_SOFT)
        kart = font_kart.render(kart_text, True, COLOR_TEXT)
        screen.blit(player, (panel_x + 20, y + 7))
        screen.blit(kart, (panel_x + 20, y + 31))
        y += row_height + row_gap

    if not players_sorted:
        empty = font_kart.render("Sem jogadores recebidos.", True, COLOR_MUTED)
        screen.blit(empty, (panel_x + 20, start_y))

    hidden_count = len(players_sorted) - len(visible_players)
    if hidden_count > 0:
        footer_text = fit_text(font_kart, f"+{hidden_count} jogadores fora da vista", text_width)
        footer = font_kart.render(footer_text, True, COLOR_MUTED)
        screen.blit(footer, (panel_x + 20, sidebar_rect.bottom - 26))

    screen.set_clip(old_clip)


def main():
    pygame.init()
    window_size = (WINDOW_WIDTH, HEIGHT)
    screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)
    pygame.display.set_caption("STK Live Duo")

    font_small = pygame.font.SysFont("Arial", 12, bold=True)
    font_title = pygame.font.SysFont("Orbitron", 18, bold=True)
    font_name = pygame.font.SysFont("Segoe UI", 16, bold=True)
    font_kart = pygame.font.SysFont("Consolas", 12)

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
    panel_layouts = get_panel_layout(window_size)

    clock = pygame.time.Clock()

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
                if event.type == pygame.VIDEORESIZE:
                    window_size = (
                        max(event.w, MIN_WINDOW_WIDTH),
                        max(event.h, MIN_WINDOW_HEIGHT),
                    )
                    screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)
                    panel_layouts = get_panel_layout(window_size)
                    for state in states.values():
                        state["track_surface"] = None

            receive_packets(sock, states, ip_map)

            screen.fill(COLOR_BG)
            for index, config in enumerate(SERVER_CONFIGS[:2]):
                state = states[config["label"]]
                layout = panel_layouts[index]
                rebuild_track_surface(state, layout["map"])
                draw_map(screen, state["track_surface"], layout["map"])
                draw_players(screen, state, font_small, layout["map"])
                draw_leaderboard(screen, state, font_title, font_name, font_kart, layout["sidebar"])

            pygame.display.flip()
            clock.tick(60)
    finally:
        save_leaderboard(states)
        sock.close()
        pygame.quit()


if __name__ == "__main__":
    main()
