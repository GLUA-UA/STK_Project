"""Leitura das pistas, comunicação UDP e ficheiros de pontuações."""

import os
import socket
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
    # Ordena primeiro pela posição; jogadores sem posição ficam no fim.
    name, player = item
    if player["pos"] is None:
        return (True, 0, name.lower())
    return (False, player["pos"], name.lower())


def sorted_players(players):
    return sorted(players.items(), key=player_order)


def parse_packet(data):
    # track|nome|kart|x|z|posição (a posição pode não vir no pacote).
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

    try:
        x, z = float(x), float(z)
    except ValueError:
        return None
    if not isfinite(x) or not isfinite(z):
        return None

    return track_id, name, {
        "kart": kart,
        "x": x,
        "z": z,
        "pos": pos,
    }


class Viewer:
    def __init__(self):
        self.sock = None
        self.states = []

    def open(self, servers):
        self.states = []
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
                "packet_warning": False,
            }
            self.states.append(state)
            try:
                state["address"] = socket.gethostbyname(state["ip"])
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

    def find_state(self, ip):
        for state in self.states:
            if state["address"] == ip:
                return state
        return None

    def read_packets(self):
        if not self.sock:
            return

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
            state = self.find_state(address[0])
            if not state:
                continue
            packet = parse_packet(data)
            if not packet:
                if not state["packet_warning"]:
                    print(f"[AVISO] {state['label']}: pacote inválido ignorado: {data!r}")
                    state["packet_warning"] = True
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
                header = f"[{state['label']}] ip={state['ip']} track={state['track_id'] or 'unknown'}"
                print(header)
                file.write(header + "\n")
                for index, (name, data) in enumerate(sorted_players(state["players"]), start=1):
                    pos = data["pos"]
                    if pos is None:
                        pos = "?"
                    line = f"{index}. nome={name} kart={data['kart']} pos={pos}"
                    print(line)
                    file.write(line + "\n")
                file.write("\n")
        print(f"[GUARDADO] {path}")
