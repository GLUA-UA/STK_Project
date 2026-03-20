#!/usr/bin/env python3

import os
import socket
import xml.etree.ElementTree as ET
from datetime import datetime

import pygame

BASE_ASSETS = "stk-assets/tracks/"
WINDOW_WIDTH = 1672
WINDOW_HEIGHT = 972
FPS = 60

SERVER_CONFIGS = [
    {"label": "Server 1", "server_ip": "127.0.0.1", "server_port": 9998, "client_port": 9999},
    {"label": "Server 2", "server_ip": "192.168.55.86", "server_port": 9998, "client_port": 9999},
    {"label": "Server 3", "server_ip": "172.20.10.8", "server_port": 9998, "client_port": 9999},
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
        sock.sendto(b"MAP_CONNECT", (config["server_ip"], config["server_port"]))
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
        state["track_surface"] = (
            build_track_surface(state["track"], MAP_AREA.width, MAP_AREA.height)
            if state["track"]
            else None
        )
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


def draw_players_on_map(card_surface, state, font_small):
    if not state["track"]:
        return

    for nome, dados in state["players"].items():
        px, py = world_to_surface(
            state["track"],
            dados["x"],
            dados["z"],
            MAP_AREA.width,
            MAP_AREA.height,
        )
        center = (MAP_AREA.x + int(px), MAP_AREA.y + int(py))
        pygame.draw.circle(card_surface, (255, 255, 255), center, 8, 1)
        pygame.draw.circle(card_surface, COLOR_ORANGE, center, 6)
        label = font_small.render(nome[:12], True, COLOR_TEXT)
        card_surface.blit(label, (center[0] + 10, center[1] - 10))


def draw_server_card(screen, rect, state, fonts):
    title_font, font_name, font_kart, font_small = fonts

    panel = pygame.Surface((rect.width, rect.height))
    panel.fill(COLOR_PANEL)
    pygame.draw.rect(panel, COLOR_PANEL_ALT, panel.get_rect(), width=2, border_radius=16)

    title = title_font.render(state["config"]["label"], True, COLOR_ORANGE)
    track_line = font_kart.render(
        f"Track: {state['track_id'] or 'sem dados'} | IP: {state['config']['server_ip']}",
        True,
        COLOR_MUTED,
    )
    panel.blit(title, (18, 16))
    panel.blit(track_line, (18, 44))

    map_box = pygame.Rect(MAP_AREA)
    pygame.draw.rect(panel, COLOR_TRACK_BG, map_box, border_radius=12)

    if state["track_surface"]:
        panel.blit(state["track_surface"], map_box.topleft)
        draw_players_on_map(panel, state, font_small)
    else:
        empty = font_kart.render("Sem mapa recebido.", True, COLOR_MUTED)
        panel.blit(empty, (map_box.x + 18, map_box.y + 18))

    leaderboard_title = title_font.render("LEADERBOARD", True, COLOR_ORANGE)
    panel.blit(leaderboard_title, (LEADERBOARD_X, LEADERBOARD_TITLE_Y))
    pygame.draw.line(
        panel,
        COLOR_ORANGE,
        (LEADERBOARD_X, LEADERBOARD_TITLE_Y + 28),
        (LEADERBOARD_X + LEADERBOARD_W, LEADERBOARD_TITLE_Y + 28),
        2,
    )

    players_sorted = get_sorted_players(state["players"])
    row_y = LEADERBOARD_ROWS_Y

    for i, (nome, dados) in enumerate(players_sorted[:5]):
        bg = COLOR_ROW_A if i % 2 == 0 else COLOR_ROW_B
        pygame.draw.rect(panel, bg, (LEADERBOARD_X, row_y, LEADERBOARD_W, 50), border_radius=6)

        pos_label = f"{dados['pos']}." if dados.get("pos") is not None else "?."
        player = font_name.render(f"{pos_label} {nome[:16]}", True, COLOR_ORANGE_SOFT)
        kart = font_kart.render(f"Kart: {dados['kart']}", True, COLOR_TEXT)

        panel.blit(player, (LEADERBOARD_X + 10, row_y + 5))
        panel.blit(kart, (LEADERBOARD_X + 10, row_y + 28))

        row_y += 60

    if not players_sorted:
        empty = font_kart.render("Sem jogadores recebidos.", True, COLOR_MUTED)
        panel.blit(empty, (LEADERBOARD_X, LEADERBOARD_ROWS_Y))

    screen.blit(panel, rect.topleft)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("STK Live Quad")

    title_font = pygame.font.SysFont("Orbitron", 20, bold=True)
    font_name = pygame.font.SysFont("Segoe UI", 18, bold=True)
    font_kart = pygame.font.SysFont("Consolas", 14)
    font_small = pygame.font.SysFont("Arial", 12, bold=True)

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

    card_positions = []
    margin_x = 24
    margin_y = 24
    gap_x = 24
    gap_y = 24

    for row in range(2):
        for col in range(2):
            x = margin_x + col * (CARD_WIDTH + gap_x)
            y = margin_y + row * (CARD_HEIGHT + gap_y)
            card_positions.append(pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT))

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