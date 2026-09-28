#!/usr/bin/env python3
"""Menu STK. Requer pygame-ce 2.5.7+ (SVG e janela com suporte Retina).
Na raiz do repositório: .venv/bin/python projeto/app_menu/app_menu.py
"""

import os
import random
import socket
import xml.etree.ElementTree as ET
from datetime import datetime
from math import isfinite

import pygame

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
ASSETS_DIR = os.path.join(PROJECT_DIR, "stk-assets", "tracks")
SCORES_DIR = os.path.join(PROJECT_DIR, "pontuacoes")
MENU_IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")

SERVER_PORT = 9998
CLIENT_PORT = 9999
WINDOW_SIZE = (1280, 820)
MIN_SIZE = (980, 640)
FPS = 60
MAX_PARTICIPANTS = 32
DEFAULT_GROUP_COUNT = 4
MAX_GROUPS = 16

# Cores da interface: fundo escuro, texto branco e laranja nos controlos.
BG = (16, 16, 16)
FIELD = (30, 30, 30)
BORDER = (75, 75, 75)
ORANGE = (247, 127, 28)
TEXT = (240, 240, 240)
MUTED = (165, 165, 165)
ERROR = (235, 110, 110)


def load_image(filename, width, height):
    path = os.path.join(MENU_IMAGES_DIR, filename)
    try:
        root = ET.parse(path).getroot()
        _, _, svg_width, svg_height = map(float, root.attrib["viewBox"].split())
        scale = min(width / svg_width, height / svg_height)
        size = (round(svg_width * scale), round(svg_height * scale))
        # Renderiza o SVG a 2x os píxeis de destino; nunca amplia um bitmap pequeno.
        image = pygame.image.load_sized_svg(path, (size[0] * 2, size[1] * 2))
        return pygame.transform.smoothscale(image, size)
    except (OSError, pygame.error, ET.ParseError, KeyError, ValueError) as error:
        print(f"[AVISO] Imagem indisponível: {filename}: {error}")
        return None


def draw_scrollbar(screen, area, scroll, maximum):
    if maximum <= 0:
        return
    height = max(24, area.height * area.height // (area.height + maximum))
    y = area.y + (area.height - height) * scroll // maximum
    pygame.draw.rect(screen, ORANGE, (area.right - 4, y, 4, height))


class Button:
    def __init__(self, text, accent=False):
        self.text = text
        self.accent = accent
        self.rect = pygame.Rect(0, 0, 1, 1)

    def draw(self, screen, font, rect):
        self.rect = pygame.Rect(rect)
        color = ORANGE if self.accent else FIELD
        pygame.draw.rect(screen, color, self.rect)

        label_color = (20, 20, 20) if self.accent else TEXT
        label = font.render(self.text, True, label_color)
        screen.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        return self.rect.collidepoint(event.pos)


class TextBox:
    def __init__(self, text=""):
        self.text = text
        self.active = False
        self.rect = pygame.Rect(0, 0, 1, 1)

    def draw(self, screen, font, rect, placeholder=""):
        self.rect = pygame.Rect(rect)
        pygame.draw.rect(screen, FIELD, self.rect)
        pygame.draw.rect(screen, ORANGE if self.active else BORDER, self.rect, 1)

        value = self.text if self.text else placeholder
        text_color = TEXT if self.text else MUTED
        label = font.render(fit_text(font, value, self.rect.width - self.rect.height // 2), True, text_color)
        position = (self.rect.x + self.rect.height // 4, self.rect.centery)
        screen.blit(label, label.get_rect(midleft=position))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False

        if event.type == pygame.TEXTINPUT and self.active and len(self.text) < 32:
            self.text += event.text


def fit_text(font, text, width):
    if font.size(text)[0] <= width:
        return text
    while text and font.size(text + "...")[0] > width:
        text = text[:-1]
    return text + "..." if text else "..."


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


def world_to_screen(track, x, z, rect, padding=22):
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


def player_order(item):
    name, player = item
    if player["pos"] is None:
        return (True, 0, name.lower())
    return (False, player["pos"], name.lower())


def sorted_players(players):
    return sorted(players.items(), key=player_order)


class MenuApp:
    def __init__(self):
        pygame.init()
        self.window = pygame.Window("GLUA — STK", size=WINDOW_SIZE,
                                    resizable=True, allow_high_dpi=True)
        self.window.minimum_size = MIN_SIZE
        self.scale = 0
        self.resize()
        self.clock = pygame.time.Clock()
        self.mouse_pos = (0, 0)

        self.mode = "menu"
        self.server_count = 1
        self.ip_boxes = []
        self.server_names = []
        for index in range(4):
            self.ip_boxes.append(TextBox("127.0.0.1"))
            self.server_names.append(TextBox(f"Server {index + 1}"))
        self.status = "Escolhe os servidores e indica os IPs."
        self.status_color = MUTED

        self.start_button = Button("Iniciar mapa", True)
        self.group_button = Button("Configurar grupos")
        self.back_button = Button("Voltar")
        self.clear_button = Button("Limpar")
        self.random_button = Button("Randomizar", True)
        self.count_buttons = {
            1: Button("1", True),
            2: Button("2"),
            4: Button("4"),
        }

        self.viewer_sock = None
        self.viewer_states = []

        self.total_box = TextBox("8")
        self.group_total_box = TextBox(str(DEFAULT_GROUP_COUNT))
        self.name_boxes = []
        for index in range(8):
            self.name_boxes.append(TextBox())
        self.group_scroll = 0
        self.group_name_area = pygame.Rect(0, 0, 1, 1)
        self.group_result_scroll = 0
        self.group_result_area = pygame.Rect(0, 0, 1, 1)
        self.groups = []
        icon = load_image("Logo_Penguin_Orange.svg", 64, 64)
        if icon:
            self.window.set_icon(icon)
        self.previous_screen = None
        self.transition_start = 0

    def resize(self):
        # SDL distingue o tamanho da janela dos píxeis físicos (2x em Retina).
        self.screen = self.window.get_surface()
        self.window_size = self.screen.get_size()
        scale = self.screen.get_width() / self.window.size[0]
        if scale != self.scale:
            self.scale = scale
            self.title_font = pygame.font.SysFont("Arial", round(24 * scale), bold=True)
            self.heading_font = pygame.font.SysFont("Arial", round(20 * scale), bold=True)
            self.font = pygame.font.SysFont("Arial", round(16 * scale))
            self.small_font = pygame.font.SysFont("Arial", round(14 * scale))
            self.logo = load_image("Logo_White.svg", 144 * scale, 60 * scale)
        width, height = self.window_size
        content_width = min(760 * scale, width - 64 * scale)
        self.content = pygame.Rect((width - content_width) // 2, 0, content_width, height)
        self.previous_screen = None

    def change_mode(self, mode):
        # Uma cópia do ecrã desaparece durante 140 ms, sem parar os eventos ou UDP.
        self.previous_screen = self.screen.copy()
        self.transition_start = pygame.time.get_ticks()
        if self.mode == "viewer" and mode != "viewer":
            self.close_viewer()
        self.mode = mode
        for box in self.ip_boxes + self.server_names + self.name_boxes + [self.total_box, self.group_total_box]:
            box.active = False

    def close_viewer(self):
        if not self.viewer_states:
            return

        try:
            self.save_scores()
            self.status = "Pontuações guardadas em projeto/pontuacoes/."
            self.status_color = ORANGE
        except OSError as error:
            self.status = f"Erro ao guardar pontuações: {error}"
            self.status_color = ERROR
            print(f"[ERRO] {self.status}")

        if self.viewer_sock:
            self.viewer_sock.close()
            self.viewer_sock = None

        self.viewer_states = []

    def make_states(self):
        states = []
        for index in range(self.server_count):
            state = {
                "label": self.server_names[index].text.strip() or f"Server {index + 1}",
                "ip": self.ip_boxes[index].text.strip() or "127.0.0.1",
                "track_id": "",
                "track": None,
                "players": {},
                "error": "",
                "scroll": 0,
                "board_rect": pygame.Rect(0, 0, 0, 0),
            }
            states.append(state)
        return states

    def open_viewer(self):
        self.close_viewer()
        self.viewer_states = self.make_states()

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", CLIENT_PORT))
            sock.setblocking(False)

            self.viewer_sock = sock
            print(f"[UDP] A receber em 0.0.0.0:{CLIENT_PORT}")
            for state in self.viewer_states:
                try:
                    state["address"] = socket.gethostbyname(state["ip"])
                    sock.sendto(b"MAP_CONNECT", (state["address"], SERVER_PORT))
                    print(f"[PEDIDO] {state['label']} · {state['ip']}:{SERVER_PORT}")
                except OSError as error:
                    state["error"] = str(error)
                    print(f"[ERRO] {state['label']}: {error}")
            self.status = "Voltar guarda as pontuações. O STK deve estar a correr no servidor."
            self.status_color = ORANGE
        except OSError as error:
            if sock is not None:
                sock.close()
            self.viewer_sock = None
            self.status = f"Viewer aberto sem UDP: {error}"
            self.status_color = ERROR
            print(f"[WARN] {self.status}")

        self.change_mode("viewer")

    def find_state(self, ip):
        for state in self.viewer_states:
            if state.get("address", state["ip"]) == ip:
                return state
        return None

    def parse_packet(self, data):
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

    def read_packets(self):
        if not self.viewer_sock:
            return

        try:
            while True:
                data, address = self.viewer_sock.recvfrom(1024)
                state = self.find_state(address[0])
                if not state:
                    continue
                packet = self.parse_packet(data)
                if not packet:
                    continue

                track_id, name, player = packet
                if track_id != state["track_id"]:
                    state["track_id"] = track_id
                    try:
                        state["track"] = load_track(track_id)
                    except (OSError, ET.ParseError, ValueError, KeyError, IndexError) as error:
                        state["track"] = None
                        print(f"[ERRO] {state['label']} · pista {track_id}: {error}")
                    print(f"[PISTA] {state['label']} · {track_id}")
                    if state["track"] is None:
                        print(f"[AVISO] Mapa indisponível: {os.path.join(ASSETS_DIR, track_id, 'quads.xml')}")
                    state["players"].clear()
                    state["scroll"] = 0

                state["players"][name] = player
        except BlockingIOError:
            pass

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
            for state in self.viewer_states:
                file.write(f"[{state['label']}] ip={state['ip']} track={state['track_id'] or 'unknown'}\n")
                for index, (name, data) in enumerate(sorted_players(state["players"]), start=1):
                    pos = data["pos"] if data["pos"] is not None else "?"
                    file.write(f"{index}. nome={name} kart={data['kart']} pos={pos}\n")
                file.write("\n")
        print(f"[GUARDADO] {path}")

    def update_participant_count(self):
        value = self.total_box.text.strip()
        if not value.isdigit():
            self.status = "Numero de participantes invalido."
            self.status_color = ERROR
            return False

        total = max(2, min(MAX_PARTICIPANTS, int(value)))
        if total != len(self.name_boxes):
            self.name_boxes = self.name_boxes[:total]
            while len(self.name_boxes) < total:
                self.name_boxes.append(TextBox())
            self.groups = []

        self.total_box.text = str(total)
        self.group_scroll = min(self.group_scroll, self.max_group_scroll())
        self.status = f"{total} participantes preparados."
        self.status_color = ORANGE
        return True

    def group_count(self):
        value = self.group_total_box.text.strip()
        if not value.isdigit():
            return DEFAULT_GROUP_COUNT
        return max(1, min(MAX_GROUPS, int(value)))

    def randomize_groups(self):
        names = []
        for box in self.name_boxes:
            name = box.text.strip()
            if name:
                names.append(name)
        if len(names) < 2:
            self.status = "Escreve pelo menos dois nomes."
            self.status_color = ERROR
            return

        random.shuffle(names)
        group_count = self.group_count()
        self.group_total_box.text = str(group_count)
        self.groups = []
        for index in range(group_count):
            self.groups.append([])

        for index, name in enumerate(names):
            self.groups[index % group_count].append(name)

        self.group_result_scroll = 0
        self.status = "Grupos criados."
        self.status_color = ORANGE

    def handle_menu_event(self, event):
        for count, button in self.count_buttons.items():
            if button.clicked(event):
                self.server_count = count
                for selected_count, selected_button in self.count_buttons.items():
                    selected_button.accent = selected_count == count

        for box in self.ip_boxes[:self.server_count] + self.server_names[:self.server_count]:
            box.handle_event(event)

        if self.start_button.clicked(event):
            self.open_viewer()

        if self.group_button.clicked(event):
            self.change_mode("groups")
            self.status = ""
            self.status_color = MUTED

    def handle_group_event(self, event):
        total_was_active = self.total_box.active
        self.total_box.handle_event(event)
        self.group_total_box.handle_event(event)

        if total_was_active:
            if event.type == pygame.MOUSEBUTTONDOWN and not self.total_box.active:
                self.update_participant_count()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.update_participant_count()

        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = self.mouse_pos
            if self.group_name_area.collidepoint(mouse_pos):
                self.group_scroll -= event.y * 36 * self.scale
                self.group_scroll = max(0, min(self.group_scroll, self.max_group_scroll()))
            if self.group_result_area.collidepoint(mouse_pos):
                self.group_result_scroll -= event.y * 36 * self.scale
                self.group_result_scroll = max(0, min(self.group_result_scroll, self.max_group_result_scroll()))

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.group_name_area.collidepoint(event.pos):
                for box in self.name_boxes:
                    box.handle_event(event)
            else:
                for box in self.name_boxes:
                    box.active = False

        if event.type in (pygame.KEYDOWN, pygame.TEXTINPUT):
            for box in self.name_boxes:
                if box.active:
                    box.handle_event(event)

        if self.clear_button.clicked(event):
            for box in self.name_boxes:
                box.text = ""
                box.active = False
            self.groups = []
            self.group_scroll = 0
            self.group_result_scroll = 0
            self.status = ""
            self.status_color = MUTED

        if self.random_button.clicked(event):
            if self.update_participant_count():
                self.randomize_groups()

    def max_group_scroll(self):
        rows = (len(self.name_boxes) + 1) // 2
        return max(0, rows * 44 * self.scale - self.group_name_area.height)

    def max_group_result_scroll(self):
        content_height = 0
        for group in self.groups:
            content_height += (32 + len(group) * 24) * self.scale
        return max(0, content_height - self.group_result_area.height)

    def handle_events(self):
        x, y = pygame.mouse.get_pos()
        self.mouse_pos = (round(x * self.scale), round(y * self.scale))
        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.WINDOWCLOSE):
                return False
            if event.type in (pygame.WINDOWSIZECHANGED, pygame.WINDOWDISPLAYCHANGED):
                self.resize()
                self.draw()
                continue
            # Os cliques chegam em coordenadas da janela; o desenho usa píxeis físicos.
            if hasattr(event, "pos"):
                x, y = event.pos
                event.pos = (round(x * self.scale), round(y * self.scale))
            escape = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            back = self.mode != "menu" and self.back_button.clicked(event)
            if escape or back:
                if self.mode == "menu":
                    return False
                self.change_mode("menu")
                self.draw()
                continue

            if self.mode == "menu":
                self.handle_menu_event(event)
            elif self.mode == "groups":
                self.handle_group_event(event)
            elif self.mode == "viewer" and event.type == pygame.MOUSEWHEEL:
                for state in self.viewer_states:
                    if state["board_rect"].collidepoint(self.mouse_pos):
                        state["scroll"] = max(0, state["scroll"] - event.y)
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.draw()  # Mantém as áreas de clique certas ao mudar de ecrã.
        return True

    def draw_header(self):
        s = self.scale
        width, height = self.window_size
        top, bottom = self.content.top, self.content.bottom
        left, right = self.content.left, self.content.right
        if self.mode == "viewer":
            left, right = 32 * s, width - 32 * s
        if self.logo:
            self.screen.blit(self.logo, (left, top + 12 * s))
        else:
            self.screen.blit(self.title_font.render("GLUA", True, TEXT), (left, top + 28 * s))
        self.screen.blit(self.title_font.render("STK", True, TEXT), (left + 166 * s, top + 28 * s))
        page = "Servidores"
        if self.mode == "groups":
            page = "Participantes e grupos"
        elif self.mode == "viewer":
            page = "Mapa da corrida"
        label = self.small_font.render(page, True, MUTED)
        self.screen.blit(label, label.get_rect(midright=(right, top + 42 * s)))
        pygame.draw.line(self.screen, BORDER, (left, top + 84 * s), (right, top + 84 * s))
        pygame.draw.line(self.screen, BORDER, (left, bottom - 42 * s), (right, bottom - 42 * s))
        status = fit_text(self.small_font, self.status, right - left)
        self.screen.blit(self.small_font.render(status, True, self.status_color), (left, bottom - 30 * s))

    def draw_menu(self):
        s = self.scale
        left, right = self.content.left, self.content.right
        # O bloco cresce com os servidores e fica centrado no espaço entre cabeçalho e rodapé.
        block_height = (204 + self.server_count * 68) * s
        top = self.content.top + 84 * s + (self.content.height - 126 * s - block_height) // 2
        field_width = (self.content.width - 24 * s) // 2
        second = left + field_width + 24 * s
        self.screen.blit(self.heading_font.render("Mapa da corrida", True, TEXT), (left, top))
        self.screen.blit(self.font.render("Número de servidores", True, MUTED), (left, top + 38 * s))
        for index, count in enumerate((1, 2, 4)):
            self.count_buttons[count].draw(self.screen, self.font, (left + index * 64 * s, top + 64 * s, 52 * s, 36 * s))
        for index in range(self.server_count):
            y = top + (120 + index * 68) * s
            label = self.small_font.render(f"Servidor {index + 1} · Nome", True, MUTED)
            self.screen.blit(label, (left, y))
            self.screen.blit(self.small_font.render("IP / endereço", True, MUTED), (second, y))
            self.server_names[index].draw(self.screen, self.font, (left, y + 24 * s, field_width, 40 * s))
            self.ip_boxes[index].draw(self.screen, self.font, (second, y + 24 * s, field_width, 40 * s), "127.0.0.1")
        y = top + (132 + self.server_count * 68) * s
        pygame.draw.line(self.screen, BORDER, (left, y), (right, y))
        self.group_button.draw(self.screen, self.font, (left, y + 24 * s, 192 * s, 40 * s))
        self.start_button.draw(self.screen, self.font, (right - 192 * s, y + 24 * s, 192 * s, 40 * s))

    def draw_groups(self):
        s = self.scale
        left, right = self.content.left, self.content.right
        height = self.window_size[1]
        column = (self.content.width - 32 * s) // 2
        second = left + column + 32 * s
        self.screen.blit(self.heading_font.render("Participantes e grupos", True, TEXT), (left, 112 * s))
        self.screen.blit(self.font.render("Participantes", True, MUTED), (left, 166 * s))
        self.total_box.draw(self.screen, self.font, (left + 120 * s, 154 * s, 72 * s, 40 * s))
        self.screen.blit(self.font.render("Grupos", True, MUTED), (second, 166 * s))
        self.group_total_box.draw(self.screen, self.font, (second + 88 * s, 154 * s, 72 * s, 40 * s))
        self.group_name_area = pygame.Rect(left, 200 * s, column, height - 320 * s)
        self.group_result_area = pygame.Rect(second, 200 * s, column, height - 320 * s)
        self.group_scroll = max(0, min(self.group_scroll, self.max_group_scroll()))
        box_width = (column - 16 * s) // 2
        self.screen.set_clip(self.group_name_area)
        for index, box in enumerate(self.name_boxes):
            x = left + (index % 2) * (box_width + 12 * s)
            y = self.group_name_area.y + (index // 2) * 44 * s - self.group_scroll
            box.draw(self.screen, self.font, (x, y, box_width, 36 * s), f"Jogador {index + 1}")
        self.screen.set_clip(None)
        draw_scrollbar(self.screen, self.group_name_area, self.group_scroll, self.max_group_scroll())
        self.group_result_scroll = max(0, min(self.group_result_scroll, self.max_group_result_scroll()))
        self.screen.set_clip(self.group_result_area)
        y = self.group_result_area.y - self.group_result_scroll
        if not self.groups:
            self.screen.blit(self.font.render("Sem grupos criados.", True, MUTED), (second, y))
        for index, names in enumerate(self.groups):
            self.screen.blit(self.font.render(f"Grupo {index + 1}", True, ORANGE), (second, y))
            y += 28 * s
            for name in names:
                label = fit_text(self.font, name, column - 16 * s)
                self.screen.blit(self.font.render(label, True, TEXT), (second, y))
                y += 24 * s
            y += 4 * s
        self.screen.set_clip(None)
        draw_scrollbar(self.screen, self.group_result_area, self.group_result_scroll, self.max_group_result_scroll())
        y = height - 96 * s
        pygame.draw.line(self.screen, BORDER, (left, y - 16 * s), (right, y - 16 * s))
        self.random_button.draw(self.screen, self.font, (left, y, 144 * s, 40 * s))
        self.clear_button.draw(self.screen, self.font, (left + 160 * s, y, 104 * s, 40 * s))
        self.back_button.draw(self.screen, self.font, (right - 144 * s, y, 144 * s, 40 * s))

    def draw_track(self, track, rect):
        pygame.draw.rect(self.screen, FIELD, rect)
        if not track:
            return

        for quad in track["quads"]:
            points = []
            for x, z in quad:
                points.append(world_to_screen(track, x, z, rect, 22 * self.scale))
            pygame.draw.polygon(self.screen, BORDER, points, 1)

    def draw_players(self, track, players, rect):
        if not track:
            return

        for name, data in players.items():
            x, y = world_to_screen(track, data["x"], data["z"], rect, 22 * self.scale)
            pygame.draw.circle(self.screen, ORANGE, (x, y), round(5 * self.scale))
            label = self.small_font.render(fit_text(self.small_font, name, 90 * self.scale), True, TEXT)
            label_rect = label.get_rect(topleft=(x + 8 * self.scale, y - 8 * self.scale))
            if label_rect.right > rect.right:
                label_rect.right = x - 8 * self.scale
            label_rect.clamp_ip(rect)
            self.screen.blit(label, label_rect)

    def draw_leaderboard(self, state, rect):
        s = self.scale
        players = sorted_players(state["players"])
        rows = max(1, int((rect.height - 46 * s) // (38 * s)))
        state["board_rect"] = rect
        state["scroll"] = min(state["scroll"], max(0, len(players) - rows))
        start = state["scroll"]
        self.screen.blit(self.font.render("Classificação", True, TEXT), rect.topleft)
        y = rect.y + 28 * s
        for name, player in players[start:start + rows]:
            pos = player["pos"] if player["pos"] is not None else "?"
            label = fit_text(self.font, f"{pos}. {name}", rect.width)
            kart = fit_text(self.small_font, player["kart"], rect.width)
            self.screen.blit(self.font.render(label, True, ORANGE), (rect.x, y))
            self.screen.blit(self.small_font.render(kart, True, MUTED), (rect.x, y + 20 * s))
            y += 38 * s
        if len(players) > rows:
            label = f"{start + 1}–{min(start + rows, len(players))} / {len(players)} · scroll"
            self.screen.blit(self.small_font.render(label, True, MUTED), (rect.x, rect.bottom - 18 * s))

    def draw_viewer(self):
        self.read_packets()
        s = self.scale
        width, height = self.window_size
        columns = 1
        rows = 1
        if self.server_count > 1:
            columns = 2
        if self.server_count == 4:
            rows = 2
        cell_width = (width - 64 * s - (columns - 1) * 32 * s) // columns
        cell_height = (height - 228 * s - (rows - 1) * 24 * s) // rows
        for index, state in enumerate(self.viewer_states):
            x = 32 * s + (index % columns) * (cell_width + 32 * s)
            y = 108 * s + (index // columns) * (cell_height + 24 * s)
            title = fit_text(self.heading_font, state["label"], cell_width)
            self.screen.blit(self.heading_font.render(title, True, TEXT), (x, y))
            detail = f"{state['ip']} · {state['track_id'] or 'à espera da corrida'}"
            if state["error"]:
                detail = f"{state['ip']} · erro no pedido UDP"
            detail = fit_text(self.small_font, detail, cell_width)
            self.screen.blit(self.small_font.render(detail, True, MUTED), (x, y + 28 * s))
            board_width = min(240 * s, cell_width * 2 // 5)
            map_rect = pygame.Rect(x, y + 60 * s, cell_width - board_width - 24 * s, cell_height - 60 * s)
            board_rect = pygame.Rect(map_rect.right + 24 * s, map_rect.y, board_width, map_rect.height)
            self.screen.set_clip(map_rect)
            self.draw_track(state["track"], map_rect)
            self.draw_players(state["track"], state["players"], map_rect)
            if not state["track"]:
                message = "Mapa indisponível" if state["track_id"] else "Sem dados"
                text = self.small_font.render(message, True, MUTED)
                self.screen.blit(text, text.get_rect(center=map_rect.center))
            self.screen.set_clip(None)
            self.draw_leaderboard(state, board_rect)
        self.back_button.draw(self.screen, self.font, (width - 176 * s, height - 104 * s, 144 * s, 40 * s))

    def draw(self):
        # O menu ocupa só a altura necessária; cabeçalho, formulário e rodapé ficam juntos.
        height = self.window_size[1]
        self.content.height = height
        if self.mode == "menu":
            self.content.height = min(height - 24 * self.scale,
                                      (354 + self.server_count * 68) * self.scale)
        self.content.centery = height // 2
        self.screen.fill(BG)
        if self.mode == "menu":
            self.draw_menu()
        elif self.mode == "groups":
            self.draw_groups()
        elif self.mode == "viewer":
            self.draw_viewer()
        self.draw_header()

    def run(self):
        try:
            self.draw()
            self.window.flip()
            while self.handle_events():
                self.draw()
                if self.previous_screen is not None:
                    elapsed = pygame.time.get_ticks() - self.transition_start
                    if elapsed < 140:
                        self.previous_screen.set_alpha(255 * (140 - elapsed) // 140)
                        self.screen.blit(self.previous_screen, (0, 0))
                    else:
                        self.previous_screen = None
                self.window.flip()
                self.clock.tick(FPS)
        finally:
            self.close_viewer()
            pygame.quit()


if __name__ == "__main__":
    MenuApp().run()
