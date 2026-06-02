#!/usr/bin/env python3

import os
import socket
import xml.etree.ElementTree as ET
from datetime import datetime

import pygame

BASE_ASSETS = "stk-assets/tracks/"
WINDOW_WIDTH = 1672
WINDOW_HEIGHT = 972
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 520
FPS = 60

SERVER_CONFIGS = [
    {"label": "Server 1", "server_ip": "127.0.0.1", "server_port": 9998, "client_port": 9999},
    {"label": "Server 2", "server_ip": "192.168.55.86", "server_port": 9998, "client_port": 9999},
    {"label": "Server 3", "server_ip": "127.0.0.1", "server_port": 9998, "client_port": 9999},
    {"label": "Server 4", "server_ip": "172.20.10.4", "server_port": 9998, "client_port": 9999},
]

CARD_WIDTH = 800
CARD_HEIGHT = 450
MAP_AREA = pygame.Rect(18, 70, 500, 350)
LEADERBOARD_X = 540
LEADERBOARD_W = 242
LEADERBOARD_TITLE_Y = 86
LEADERBOARD_ROWS_Y = 136

COLOR_BG = (12, 12, 14)
COLOR_PANEL = (26, 27, 33)
COLOR_PANEL_ALT = (33, 35, 43)
COLOR_TRACK_BG = (15, 15, 15)
COLOR_TRACK_LINE = (75, 75, 82)
COLOR_TEXT = (240, 240, 240)
COLOR_MUTED = (160, 160, 168)
COLOR_ORANGE = (255, 145, 40)
COLOR_ORANGE_SOFT = (255, 185, 90)
COLOR_ROW_A = (38, 40, 49)
COLOR_ROW_B = (31, 33, 41)

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


def build_track_surface(track, width, height):
    surface = pygame.Surface((width, height))
    surface.fill(COLOR_TRACK_BG)

    usable_w = width - 40
    usable_h = height - 40
    track_w = track["width"] if track["width"] > 0 else 1.0
    track_h = track["height"] if track["height"] > 0 else 1.0
    scale = min(usable_w / track_w, usable_h / track_h)
    offset_x = (width - track_w * scale) / 2
    offset_y = (height - track_h * scale) / 2

    for quad in track["quads"]:
        pts = [
            (
                offset_x + ((x - track["min_x"]) * scale),
                height - (offset_y + ((z - track["min_z"]) * scale)),
            )
            for x, z in quad
        ]
        pygame.draw.polygon(surface, COLOR_TRACK_LINE, pts, 1)

    return surface


def normalize_sender_ip(ip):
    if ip == "::ffff:127.0.0.1":
        return "127.0.0.1"
    if ip == "::1":
        return "127.0.0.1"
    return ip


def setup_socket():
    client_port = SERVER_CONFIGS[0]["client_port"]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", client_port))
    sock.setblocking(False)

    print(f"[INFO] Shared socket ligado em 0.0.0.0:{client_port}")

    for config in SERVER_CONFIGS:
        try:
            sock.sendto(b"MAP_CONNECT", (config["server_ip"], config["server_port"]))
        except OSError as exc:
            print(
                f"[WARN] {config['label']} nao foi registado agora: "
                f"{config['server_ip']}:{config['server_port']} ({exc})"
            )
            continue

        print(
            f"[INFO] {config['label']} registado: "
            f"0.0.0.0:{client_port} -> {config['server_ip']}:{config['server_port']}"
        )

    return sock


def build_ip_map():
    ip_map = {}
    for config in SERVER_CONFIGS:
        ip_map[config["server_ip"]] = config["label"]
    return ip_map


def process_packet_for_state(config, state, msg):
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
            sender_ip, sender_port = addr
            sender_ip = normalize_sender_ip(sender_ip)

            try:
                msg = data.decode().strip()
            except UnicodeDecodeError:
                continue

            if sender_ip not in ip_map:
                print(f"[IGNORADO] {sender_ip}:{sender_port} -> {msg}")
                continue

            label = ip_map[sender_ip]
            state = states[label]
            config = state["config"]

            print(f"[{label}] FROM {sender_ip}:{sender_port} -> {msg}")
            process_packet_for_state(config, state, msg)

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
    file_path = os.path.join("pontuacoes", f"quad_servers_{timestamp}.txt")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"saved_at: {datetime.now().isoformat(timespec='seconds')}\n\n")
        for label, state in states.items():
            f.write(
                f"[{label}] ip={state['config']['server_ip']} "
                f"server_port={state['config']['server_port']} "
                f"client_port={state['config']['client_port']} "
                f"track={state['track_id'] or 'unknown'}\n"
            )
            for idx, (name, data) in enumerate(get_sorted_players(state["players"]), start=1):
                pos_text = str(data.get("pos")) if data.get("pos") is not None else "?"
                f.write(
                    f"{idx}. nome={name} kart={data['kart']} pos={pos_text} "
                    f"x={data['x']:.3f} z={data['z']:.3f}\n"
                )
            f.write("\n")

    print(f"[INFO] Pontuacoes guardadas em: {file_path}")


def world_to_surface(track, x, z, width, height):
    track_w = track["width"] if track["width"] > 0 else 1.0
    track_h = track["height"] if track["height"] > 0 else 1.0
    usable_w = width - 40
    usable_h = height - 40
    scale = min(usable_w / track_w, usable_h / track_h)
    offset_x = (width - track_w * scale) / 2
    offset_y = (height - track_h * scale) / 2
    px = offset_x + ((x - track["min_x"]) * scale)
    py = height - (offset_y + ((z - track["min_z"]) * scale))
    return px, py


def draw_players_on_map(card_surface, state, font_small, map_box):
    if not state["track"]:
        return

    for nome, dados in state["players"].items():
        px, py = world_to_surface(
            state["track"],
            dados["x"],
            dados["z"],
            map_box.width,
            map_box.height,
        )
        center = (map_box.x + int(px), map_box.y + int(py))
        pygame.draw.circle(card_surface, (255, 255, 255), center, 8, 1)
        pygame.draw.circle(card_surface, COLOR_ORANGE, center, 6)
        label = font_small.render(nome[:12], True, COLOR_TEXT)
        card_surface.blit(label, (center[0] + 10, center[1] - 10))


def get_card_layouts(window_size):
    width, height = window_size
    margin_x = 24
    margin_y = 24
    gap_x = 24
    gap_y = 24
    card_width = max(360, (width - margin_x * 2 - gap_x) // 2)
    card_height = max(260, (height - margin_y * 2 - gap_y) // 2)
    cards = []

    for row in range(2):
        for col in range(2):
            x = margin_x + col * (card_width + gap_x)
            y = margin_y + row * (card_height + gap_y)
            cards.append(pygame.Rect(x, y, card_width, card_height))

    return cards


def get_card_inner_layout(card_rect):
    map_width = max(180, int(card_rect.width * 0.62))
    map_height = max(130, card_rect.height - 100)
    map_box = pygame.Rect(18, 70, map_width, map_height)
    leaderboard_x = map_box.right + 22
    leaderboard_w = max(80, card_rect.width - leaderboard_x - 18)
    return {
        "map_box": map_box,
        "leaderboard_x": leaderboard_x,
        "leaderboard_w": leaderboard_w,
        "leaderboard_title_y": 86,
        "leaderboard_rows_y": 136,
    }


def rebuild_track_surface(state, map_box):
    size = (map_box.width, map_box.height)
    if state["track"] and state.get("track_surface_size") != size:
        state["track_surface"] = build_track_surface(state["track"], *size)
        state["track_surface_size"] = size


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


def draw_server_card(screen, rect, state, fonts):
    title_font, font_name, font_kart, font_small = fonts
    layout = get_card_inner_layout(rect)
    map_box = layout["map_box"]
    leaderboard_x = layout["leaderboard_x"]
    leaderboard_w = layout["leaderboard_w"]
    leaderboard_title_y = layout["leaderboard_title_y"]
    leaderboard_rows_y = layout["leaderboard_rows_y"]
    rebuild_track_surface(state, map_box)

    panel = pygame.Surface((rect.width, rect.height))
    panel.fill(COLOR_PANEL)
    pygame.draw.rect(panel, COLOR_PANEL_ALT, panel.get_rect(), width=2, border_radius=16)

    title = title_font.render(fit_text(title_font, state["config"]["label"], rect.width - 36), True, COLOR_ORANGE)
    track_line = font_kart.render(
        fit_text(
            font_kart,
            f"Track: {state['track_id'] or 'sem dados'} | IP: {state['config']['server_ip']}",
            rect.width - 36,
        ),
        True,
        COLOR_MUTED,
    )
    panel.blit(title, (18, 16))
    panel.blit(track_line, (18, 44))

    pygame.draw.rect(panel, COLOR_TRACK_BG, map_box, border_radius=12)

    if state["track_surface"]:
        panel.blit(state["track_surface"], map_box.topleft)
        draw_players_on_map(panel, state, font_small, map_box)
    else:
        empty = font_kart.render("Sem mapa recebido.", True, COLOR_MUTED)
        panel.blit(empty, (map_box.x + 18, map_box.y + 18))

    leaderboard_title = title_font.render("LEADERBOARD", True, COLOR_ORANGE)
    panel.blit(leaderboard_title, (leaderboard_x, leaderboard_title_y))
    pygame.draw.line(
        panel,
        COLOR_ORANGE,
        (leaderboard_x, leaderboard_title_y + 28),
        (leaderboard_x + leaderboard_w, leaderboard_title_y + 28),
        2,
    )

    players_sorted = get_sorted_players(state["players"])
    row_y = leaderboard_rows_y
    row_height = 46
    row_gap = 8
    max_rows = max(0, (rect.height - row_y - 30) // (row_height + row_gap))
    visible_players = players_sorted[:max_rows]

    for i, (nome, dados) in enumerate(visible_players):
        bg = COLOR_ROW_A if i % 2 == 0 else COLOR_ROW_B
        pygame.draw.rect(panel, bg, (leaderboard_x, row_y, leaderboard_w, row_height), border_radius=6)

        pos_label = f"{dados['pos']}." if dados.get("pos") is not None else "?."
        text_width = leaderboard_w - 20
        player_text = fit_text(font_name, f"{pos_label} {nome}", text_width)
        kart_text = fit_text(font_kart, f"Kart: {dados['kart']}", text_width)
        player = font_name.render(player_text, True, COLOR_ORANGE_SOFT)
        kart = font_kart.render(kart_text, True, COLOR_TEXT)

        panel.blit(player, (leaderboard_x + 10, row_y + 5))
        panel.blit(kart, (leaderboard_x + 10, row_y + 26))

        row_y += row_height + row_gap

    if not players_sorted:
        empty = font_kart.render("Sem jogadores recebidos.", True, COLOR_MUTED)
        panel.blit(empty, (leaderboard_x, leaderboard_rows_y))

    hidden_count = len(players_sorted) - len(visible_players)
    if hidden_count > 0:
        footer_text = fit_text(font_kart, f"+{hidden_count} jogadores fora da vista", leaderboard_w)
        footer = font_kart.render(footer_text, True, COLOR_MUTED)
        panel.blit(footer, (leaderboard_x, rect.height - 24))

    screen.blit(panel, rect.topleft)


def main():
    pygame.init()
    window_size = (WINDOW_WIDTH, WINDOW_HEIGHT)
    screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)
    pygame.display.set_caption("STK Live Quad")

    title_font = pygame.font.SysFont("Orbitron", 16, bold=True)
    font_name = pygame.font.SysFont("Segoe UI", 13, bold=True)
    font_kart = pygame.font.SysFont("Consolas", 11)
    font_small = pygame.font.SysFont("Arial", 10, bold=True)

    sock = setup_socket()
    ip_map = build_ip_map()

    states = {
        config["label"]: {
            "config": config,
            "track_id": "",
            "track": None,
            "track_surface": None,
            "track_surface_size": None,
            "players": {},
        }
        for config in SERVER_CONFIGS
    }

    card_positions = get_card_layouts(window_size)
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
                    card_positions = get_card_layouts(window_size)
                    for state in states.values():
                        state["track_surface_size"] = None

            receive_packets(sock, states, ip_map)

            screen.fill(COLOR_BG)

            for rect, config in zip(card_positions, SERVER_CONFIGS):
                draw_server_card(
                    screen,
                    rect,
                    states[config["label"]],
                    (title_font, font_name, font_kart, font_small),
                )

            pygame.display.flip()
            clock.tick(FPS)

    finally:
        save_leaderboard(states)
        sock.close()
        pygame.quit()


if __name__ == "__main__":
    main()
