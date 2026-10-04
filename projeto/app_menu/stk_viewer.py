"""Leitura das pistas, comunicação UDP e ficheiros de pontuações."""

import os
import socket
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from math import isfinite

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_DIR, "stk-assets", "tracks")
SCORES_DIR = os.path.join(PROJECT_DIR, "pontuacoes")
SERVER_PORT = 9998
CLIENT_PORT = 9999


def load_track(track_id):
    path = os.path.join(ASSETS_DIR, track_id, "quads.xml")
    print("[XML] Ler pista:", path)
    if not os.path.exists(path):
        return None

    quads = []
    root = ET.parse(path).getroot()

    for quad in root.findall("quad"):
        points = []
        for i in range(4):
            value = quad.attrib[f"p{i}"]
            if ":" in value:
                reference = value.split(":")
                quad_index = int(reference[0])
                point_index = int(reference[1])
                points.append(quads[quad_index][point_index])
            else:
                coordinates = value.split()
                points.append((float(coordinates[0]), float(coordinates[2])))
        quads.append(points)

    xs = []
    zs = []
    for quad in quads:
        for x, z in quad:
            xs.append(x)
            zs.append(z)

    return {
        "quads": quads,
        "min_x": min(xs),
        "min_z": min(zs),
        "width": max(xs) - min(xs),
        "height": max(zs) - min(zs),
    }


def player_order(item):
    name = item[0]
    player = item[1]
    return player["pos"], name.lower()


def sorted_players(players):
    return sorted(players.items(), key=player_order)


def parse_packet(data):
    # track|nome|kart|x|z|posição, enviado por world.cpp.
    parts = data.decode(errors="ignore").strip().split("|")
    if len(parts) != 6:
        return None

    track_id = parts[0]
    name = parts[1]
    kart = parts[2]
    try:
        x = float(parts[3])
        z = float(parts[4])
        position = int(parts[5])
    except ValueError:
        return None
    if not isfinite(x) or not isfinite(z):
        return None

    player = {"kart": kart, "x": x, "z": z, "pos": position}
    return track_id, name, player


class Viewer:
    def __init__(self):
        self.sock = None
        self.states = []
        self.next_request = 0

    def open(self, servers):
        self.states = []
        self.next_request = 0
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(("0.0.0.0", CLIENT_PORT))
            sock.setblocking(False)
        except OSError:
            sock.close()
            raise
        self.sock = sock
        print(f"[UDP] Listener iniciado em 0.0.0.0:{CLIENT_PORT}")
        for server in servers:
            state = {
                "game_port": server.get("game_port"),
                "local": server.get("local", False),
                "label": server["label"],
                "ip": server["ip"],
                "address": server["ip"],
                "track_id": "",
                "track": None,
                "players": {},
                "error": "",
                "scroll": 0,
                "board_rect": None,
                "receiving": False,
            }
            self.states.append(state)
            try:
                if state["ip"] == "localhost":
                    state["address"] = "127.0.0.1"
                socket.inet_aton(state["address"])
                sock.sendto(b"MAP_CONNECT", (state["address"], SERVER_PORT))
                print(f"[PEDIDO] {state['label']} · {state['ip']}:{SERVER_PORT} (à espera de dados)")
            except OSError as error:
                state["error"] = str(error)
                print(f"[ERRO] {state['label']} · {state['ip']}: {error}")

    def close(self):
        try:
            if self.states:
                self.save_scores()
        finally:
            if self.sock:
                self.sock.close()
                print("[UDP] Listener fechado.")
            self.sock = None
            self.states = []

    def read_packets(self):
        if not self.sock:
            return

        # O STK abre a telemetria quando a corrida começa; repete pedidos pendentes.
        now = time.monotonic()
        if now >= self.next_request:
            self.next_request = now + 1
            for state in self.states:
                if not state["receiving"] and not state["error"]:
                    try:
                        self.sock.sendto(b"MAP_CONNECT", (state["address"], SERVER_PORT))
                    except OSError as error:
                        state["error"] = str(error)
                        print("[ERRO UDP]", error)
        while True:
            try:
                data, address = self.sock.recvfrom(1024)
            except BlockingIOError:
                return
            except OSError as error:
                print("[ERRO UDP] Receção interrompida:", error)
                self.sock.close()
                self.sock = None
                for state in self.states:
                    state["error"] = f"UDP interrompido: {error}"
                return
            state = None
            for server in self.states:
                if server["address"] == address[0]:
                    state = server
                    break
            if not state:
                continue
            packet = parse_packet(data)
            if not packet:
                print(f"[AVISO] {state['label']}: pacote inválido ignorado: {data!r}")
                continue
            if not state["receiving"]:
                print(f"[DADOS] Primeira atualização de {state['label']} · {address[0]}")
                state["receiving"] = True

            track_id, name, player = packet
            if track_id != state["track_id"]:
                state["track_id"] = track_id
                state["error"] = ""
                try:
                    state["track"] = load_track(track_id)
                except (OSError, ET.ParseError, ValueError, KeyError, IndexError) as error:
                    state["track"] = None
                    state["error"] = str(error)
                    print(f"[ERRO] {state['label']} · pista {track_id}: {error}")
                print(f"[PISTA] {state['label']} · {track_id}")
                if state["track"] is None:
                    if not state["error"]:
                        state["error"] = "Mapa indisponível: " + track_id
                    print(f"[AVISO] Mapa indisponível: {os.path.join(ASSETS_DIR, track_id, 'quads.xml')}")
                state["players"].clear()
                state["scroll"] = 0

            if name not in state["players"]:
                print(f"[JOGADOR] {state['label']} · {name} · kart={player['kart']} · pos={player['pos']}")
            state["players"][name] = player

    def save_scores(self):
        os.makedirs(SCORES_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = os.path.join(SCORES_DIR, f"app_viewer_{timestamp}.txt")

        # Duas saídas no mesmo segundo não devem substituir a primeira classificação.
        suffix = 2
        while os.path.exists(path):
            path = os.path.join(SCORES_DIR, f"app_viewer_{timestamp}_{suffix}.txt")
            suffix += 1
        with open(path, "w", encoding="utf-8") as file:
            for state in self.states:
                track_id = state["track_id"]
                if not track_id:
                    track_id = "unknown"
                header = f"[{state['label']}] ip={state['ip']} track={track_id}"
                print(header)
                file.write(header + "\n")
                players = sorted_players(state["players"])
                for index in range(len(players)):
                    name = players[index][0]
                    data = players[index][1]
                    position = data["pos"]
                    line = f"{index + 1}. nome={name} kart={data['kart']} pos={position}"
                    print(line)
                    file.write(line + "\n")
                file.write("\n")
        print(f"[GUARDADO] {path}")
