#!/usr/bin/env python3

import os
import random
import socket
import xml.etree.ElementTree as ET
from datetime import datetime

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

BG = (12, 12, 14)
PANEL = (28, 29, 35)
PANEL_ALT = (36, 38, 46)
FIELD = (20, 21, 26)
FIELD_ACTIVE = (42, 45, 55)
TRACK_BG = (18, 18, 20)
TRACK_LINE = (82, 82, 90)
ROW_A = (38, 40, 48)
ROW_B = (31, 32, 39)
ORANGE = (255, 145, 40)
ORANGE_DARK = (210, 110, 25)
TEXT = (240, 240, 240)
MUTED = (160, 160, 168)
SUCCESS = (90, 200, 120)
ERROR = (220, 90, 90)
MENU_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def draw_panel(screen, rect, color=PANEL):
    shadow = rect.move(0, 3)
    pygame.draw.rect(screen, (4, 4, 6), shadow, border_radius=14)
    pygame.draw.rect(screen, color, rect, border_radius=14)
    pygame.draw.rect(screen, (64, 66, 78), rect, 1, border_radius=14)


def draw_gloss(screen, rect, base, hover=False):
    shadow = rect.move(0, 2)
    pygame.draw.rect(screen, (4, 4, 6), shadow, border_radius=10)

    color = tuple(min(255, value + 12) for value in base) if hover else base
    pygame.draw.rect(screen, color, rect, border_radius=10)

    shine = pygame.Surface((rect.width, max(1, rect.height // 3)), pygame.SRCALPHA)
    pygame.draw.rect(shine, (255, 255, 255, 22), shine.get_rect(), border_radius=10)
    screen.blit(shine, rect.topleft)

    border = (255, 175, 70) if base == ORANGE else (72, 74, 86)
    pygame.draw.rect(screen, border, rect, 1, border_radius=10)


def load_menu_image():
    if not os.path.isdir(MENU_IMAGES_DIR):
        return None

    for name in sorted(os.listdir(MENU_IMAGES_DIR)):
        if name.lower().endswith(MENU_IMAGE_EXTENSIONS):
            path = os.path.join(MENU_IMAGES_DIR, name)
            return pygame.image.load(path).convert_alpha()
    return None


def draw_image_cover(screen, image, rect):
    image_ratio = image.get_width() / image.get_height()
    rect_ratio = rect.width / rect.height

    if image_ratio > rect_ratio:
        height = rect.height
        width = int(height * image_ratio)
    else:
        width = rect.width
        height = int(width / image_ratio)

    scaled = pygame.transform.smoothscale(image, (width, height))
    x = rect.x + (rect.width - width) // 2
    y = rect.y + (rect.height - height) // 2
    old_clip = screen.get_clip()
    screen.set_clip(rect)
    screen.blit(scaled, (x, y))
    screen.set_clip(old_clip)


class Button:
    def __init__(self, text, accent=False):
        self.text = text
        self.accent = accent
        self.rect = pygame.Rect(0, 0, 1, 1)

    def draw(self, screen, font, rect):
        self.rect = pygame.Rect(rect)
        hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        color = ORANGE if self.accent else PANEL_ALT
        draw_gloss(screen, self.rect, color, hovered)

        label_color = (20, 20, 20) if self.accent else TEXT
        label = font.render(self.text, True, label_color)
        screen.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


class TextBox:
    def __init__(self, text=""):
        self.text = text
        self.active = False
        self.rect = pygame.Rect(0, 0, 1, 1)

    def draw(self, screen, font, rect, placeholder=""):
        self.rect = pygame.Rect(rect)
        color = FIELD_ACTIVE if self.active else FIELD
        pygame.draw.rect(screen, color, self.rect, border_radius=7)
        pygame.draw.rect(screen, (80, 84, 98), self.rect, 1, border_radius=7)

        value = self.text if self.text else placeholder
        text_color = TEXT if self.text else MUTED
        label = font.render(fit_text(font, value, self.rect.width - 20), True, text_color)
        screen.blit(label, (self.rect.x + 10, self.rect.y + 10))

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
    padding = 22
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


def sorted_players(players):
    return sorted(
        players.items(),
        key=lambda item: (
            item[1]["pos"] is None,
            item[1]["pos"] if item[1]["pos"] is not None else 999999,
            item[0].lower(),
        ),
    )


class MenuApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
        pygame.display.set_caption("STK Toolkit")
        self.window_size = WINDOW_SIZE
        self.clock = pygame.time.Clock()

        self.title_font = pygame.font.SysFont("Arial", 32, bold=True)
        self.heading_font = pygame.font.SysFont("Arial", 22, bold=True)
        self.font = pygame.font.SysFont("Arial", 16)
        self.small_font = pygame.font.SysFont("Arial", 12)

        self.mode = "menu"
        self.server_count = 1
        self.ip_boxes = [TextBox("127.0.0.1") for _ in range(4)]
        self.status = "Escolhe quantos servidores queres ver."
        self.status_color = MUTED

        self.start_button = Button("Abrir live viewer", True)
        self.group_button = Button("Randomizador de grupos")
        self.back_button = Button("Voltar")
        self.clear_button = Button("Limpar")
        self.random_button = Button("Randomizar", True)
        self.count_buttons = {
            1: Button("1 servidor", True),
            2: Button("2 servidores"),
            4: Button("4 servidores"),
        }

        self.viewer_sock = None
        self.viewer_states = []

        self.total_box = TextBox("8")
        self.group_total_box = TextBox(str(DEFAULT_GROUP_COUNT))
        self.name_boxes = [TextBox() for _ in range(8)]
        self.group_scroll = 0
        self.group_name_area = pygame.Rect(0, 0, 1, 1)
        self.group_result_scroll = 0
        self.group_result_area = pygame.Rect(0, 0, 1, 1)
        self.groups = []
        self.menu_image = load_menu_image()

    def close_viewer(self):
        if not self.viewer_states:
            return

        self.save_scores()

        if self.viewer_sock:
            self.viewer_sock.close()
            self.viewer_sock = None

        self.viewer_states = []

    def make_states(self):
        return [
            {
                "label": f"Server {index + 1}",
                "ip": self.ip_boxes[index].text.strip() or "127.0.0.1",
                "track_id": "",
                "track": None,
                "players": {},
            }
            for index in range(self.server_count)
        ]

    def open_viewer(self):
        self.close_viewer()
        self.viewer_states = self.make_states()

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", CLIENT_PORT))
            sock.setblocking(False)

            for state in self.viewer_states:
                sock.sendto(b"MAP_CONNECT", (state["ip"], SERVER_PORT))

            self.viewer_sock = sock
            self.status = "Viewer activo. ESC ou Voltar para sair."
            self.status_color = SUCCESS
            print("[INFO] Viewer aberto.")
        except OSError as error:
            self.viewer_sock = None
            self.status = f"Viewer aberto sem UDP: {error}"
            self.status_color = ERROR
            print(f"[WARN] {self.status}")

        self.mode = "viewer"

    def find_state(self, ip):
        for state in self.viewer_states:
            if state["ip"] == ip:
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

        return track_id, name, {
            "kart": kart,
            "x": float(x),
            "z": float(z),
            "pos": pos,
        }

    def read_packets(self):
        if not self.viewer_sock:
            return

        try:
            while True:
                data, address = self.viewer_sock.recvfrom(1024)
                state = self.find_state(address[0])
                packet = self.parse_packet(data)

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

    def save_scores(self):
        os.makedirs(SCORES_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = os.path.join(SCORES_DIR, f"app_viewer_{timestamp}.txt")

        with open(path, "w", encoding="utf-8") as file:
            for state in self.viewer_states:
                file.write(f"[{state['label']}] ip={state['ip']} track={state['track_id'] or 'unknown'}\n")
                for index, (name, data) in enumerate(sorted_players(state["players"]), start=1):
                    pos = data["pos"] if data["pos"] is not None else "?"
                    file.write(f"{index}. nome={name} kart={data['kart']} pos={pos}\n")
                file.write("\n")

    def update_participant_count(self):
        value = self.total_box.text.strip()
        if not value.isdigit():
            self.status = "Numero de participantes invalido."
            self.status_color = ERROR
            return False

        total = max(2, min(MAX_PARTICIPANTS, int(value)))
        current = [box.text for box in self.name_boxes]
        self.name_boxes = []

        for index in range(total):
            text = current[index] if index < len(current) else ""
            self.name_boxes.append(TextBox(text))

        self.total_box.text = str(total)
        self.group_scroll = min(self.group_scroll, self.max_group_scroll())
        self.groups = []
        self.status = f"{total} participantes preparados."
        self.status_color = SUCCESS
        return True

    def group_count(self):
        value = self.group_total_box.text.strip()
        if not value.isdigit():
            return DEFAULT_GROUP_COUNT
        return max(1, min(MAX_GROUPS, int(value)))

    def randomize_groups(self):
        names = [box.text.strip() for box in self.name_boxes if box.text.strip()]
        if len(names) < 2:
            self.status = "Escreve pelo menos dois nomes."
            self.status_color = ERROR
            return

        random.shuffle(names)
        group_count = self.group_count()
        self.group_total_box.text = str(group_count)
        self.groups = [[] for _ in range(group_count)]

        for index, name in enumerate(names):
            self.groups[index % group_count].append(name)

        self.status = "Grupos criados."
        self.status_color = SUCCESS

    def handle_menu_event(self, event):
        for count, button in self.count_buttons.items():
            if button.clicked(event):
                self.server_count = count
                for selected_count, selected_button in self.count_buttons.items():
                    selected_button.accent = selected_count == count

        for box in self.ip_boxes[:self.server_count]:
            box.handle_event(event)

        if self.start_button.clicked(event):
            self.open_viewer()

        if self.group_button.clicked(event):
            self.mode = "groups"
            self.status = ""
            self.status_color = MUTED

    def handle_group_event(self, event):
        total_was_active = self.total_box.active
        total_before = self.total_box.text
        self.total_box.handle_event(event)
        self.group_total_box.handle_event(event)

        left_total_box = total_was_active and event.type == pygame.MOUSEBUTTONDOWN and not self.total_box.rect.collidepoint(event.pos)
        pressed_enter = total_was_active and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN
        if total_before != self.total_box.text or left_total_box or pressed_enter:
            if self.total_box.text.strip().isdigit():
                self.update_participant_count()

        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self.group_name_area.collidepoint(mouse_pos):
                self.group_scroll -= event.y * 36
                self.group_scroll = max(0, min(self.group_scroll, self.max_group_scroll()))
            if self.group_result_area.collidepoint(mouse_pos):
                self.group_result_scroll -= event.y * 36
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

        if self.back_button.clicked(event):
            self.mode = "menu"

        if self.clear_button.clicked(event):
            for box in self.name_boxes:
                box.text = ""
                box.active = False
            self.groups = []
            self.status = ""
            self.status_color = MUTED

        if self.random_button.clicked(event):
            self.update_participant_count()
            self.randomize_groups()

    def group_columns(self, area_width):
        return max(1, min(2, area_width // 190))

    def max_group_scroll(self):
        columns = self.group_columns(self.group_name_area.width)
        rows = (len(self.name_boxes) + columns - 1) // columns
        content_height = rows * 44
        return max(0, content_height - self.group_name_area.height)

    def group_result_columns(self, area_width):
        if area_width < 420:
            return 1
        return min(2, self.group_result_total())

    def group_result_total(self):
        return len(self.groups) if self.groups else self.group_count()

    def group_result_card_height(self):
        return max(150, (self.group_result_area.height - 20) // 2)

    def max_group_result_scroll(self):
        columns = self.group_result_columns(self.group_result_area.width)
        rows = (max(1, self.group_result_total()) + columns - 1) // columns
        card_height = self.group_result_card_height()
        content_height = rows * card_height + max(0, rows - 1) * 20
        return max(0, content_height - self.group_result_area.height)

    def handle_viewer_event(self, event):
        if self.back_button.clicked(event):
            self.close_viewer()
            self.mode = "menu"

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close_viewer()
                return False

            if event.type == pygame.VIDEORESIZE:
                self.window_size = (max(event.w, MIN_SIZE[0]), max(event.h, MIN_SIZE[1]))
                self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.mode == "menu":
                    self.close_viewer()
                    return False
                if self.mode == "viewer":
                    self.close_viewer()
                self.mode = "menu"

            if self.mode == "menu":
                self.handle_menu_event(event)
            elif self.mode == "groups":
                self.handle_group_event(event)
            elif self.mode == "viewer":
                self.handle_viewer_event(event)

        return True

    def draw_menu(self):
        width, height = self.window_size
        left_width = min(600, max(500, int(width * 0.44)))
        panel = pygame.Rect(60, 60, left_width, height - 120)
        image_rect = pygame.Rect(panel.right + 34, 60, width - panel.right - 94, height - 120)

        draw_panel(self.screen, panel)
        title = self.title_font.render("STK Toolkit", True, ORANGE)
        self.screen.blit(title, (panel.x + 28, panel.y + 26))

        y = panel.y + 90
        label = self.font.render("Quantos servidores?", True, TEXT)
        self.screen.blit(label, (panel.x + 28, y))
        y += 34

        button_width = (panel.width - 76) // 3
        for index, count in enumerate((1, 2, 4)):
            rect = pygame.Rect(panel.x + 28 + index * (button_width + 10), y, button_width, 44)
            self.count_buttons[count].draw(self.screen, self.font, rect)
        y += 72

        for index, box in enumerate(self.ip_boxes[:self.server_count]):
            label = self.font.render(f"IP do Server {index + 1}", True, TEXT)
            self.screen.blit(label, (panel.x + 28, y))
            box.draw(self.screen, self.font, pygame.Rect(panel.x + 180, y - 10, 260, 42), "127.0.0.1")
            y += 58

        action_y = panel.bottom - 78
        action_gap = 14
        action_width = (panel.width - 56 - action_gap) // 2
        start_rect = pygame.Rect(panel.x + 28, action_y, action_width, 48)
        group_rect = pygame.Rect(start_rect.right + action_gap, action_y, action_width, 48)

        self.start_button.draw(self.screen, self.font, start_rect)
        self.group_button.draw(self.screen, self.font, group_rect)

        if image_rect.width > 120 and image_rect.height > 120:
            draw_panel(self.screen, image_rect, (18, 18, 22))
            inner = image_rect.inflate(-28, -28)
            if self.menu_image:
                draw_image_cover(self.screen, self.menu_image, inner)
            else:
                self.draw_menu_art(inner)

    def draw_menu_art(self, rect):
        pygame.draw.rect(self.screen, (10, 10, 12), rect, border_radius=12)
        pygame.draw.circle(self.screen, (52, 34, 20), rect.center, min(rect.width, rect.height) // 3)
        pygame.draw.circle(self.screen, ORANGE_DARK, rect.center, min(rect.width, rect.height) // 3, 2)

        for offset in range(-160, 200, 40):
            start = (rect.x + max(0, offset), rect.bottom - 30)
            end = (rect.centerx + offset // 3, rect.y + 40)
            pygame.draw.line(self.screen, (70, 70, 76), start, end, 2)

        kart = pygame.Rect(rect.centerx - 42, rect.centery - 18, 84, 36)
        pygame.draw.rect(self.screen, ORANGE, kart, border_radius=12)
        pygame.draw.circle(self.screen, (8, 8, 10), (kart.x + 18, kart.bottom), 12)
        pygame.draw.circle(self.screen, (8, 8, 10), (kart.right - 18, kart.bottom), 12)
        pygame.draw.circle(self.screen, TEXT, (kart.centerx, kart.y + 8), 8, 2)

    def draw_groups(self):
        width, height = self.window_size
        left = pygame.Rect(40, 40, 430, height - 80)
        right = pygame.Rect(500, 40, width - 540, height - 80)

        pygame.draw.rect(self.screen, PANEL, left, border_radius=10)
        pygame.draw.rect(self.screen, PANEL, right, border_radius=10)

        title = self.heading_font.render("Randomizador de grupos", True, ORANGE)
        self.screen.blit(title, (left.x + 24, left.y + 22))

        self.screen.blit(self.font.render("Participantes", True, TEXT), (left.x + 24, left.y + 78))
        self.total_box.draw(self.screen, self.font, pygame.Rect(left.x + 160, left.y + 66, 90, 42), "8")

        self.screen.blit(self.font.render("Grupos", True, TEXT), (left.x + 24, left.y + 126))
        self.group_total_box.draw(self.screen, self.font, pygame.Rect(left.x + 160, left.y + 114, 90, 42), str(DEFAULT_GROUP_COUNT))

        self.group_name_area = pygame.Rect(left.x + 24, left.y + 178, left.width - 48, left.height - 268)
        self.group_scroll = max(0, min(self.group_scroll, self.max_group_scroll()))

        columns = self.group_columns(self.group_name_area.width)
        box_width = (self.group_name_area.width - (columns - 1) * 14) // columns

        old_clip = self.screen.get_clip()
        self.screen.set_clip(self.group_name_area)
        for index, box in enumerate(self.name_boxes):
            row = index // columns
            col = index % columns
            x = self.group_name_area.x + col * (box_width + 14)
            y = self.group_name_area.y + row * 44 - self.group_scroll
            box.draw(self.screen, self.small_font, pygame.Rect(x, y, box_width, 34), f"Jogador {index + 1}")
        self.screen.set_clip(old_clip)

        if self.max_group_scroll() > 0:
            bar_height = max(30, int(self.group_name_area.height * self.group_name_area.height / (self.group_name_area.height + self.max_group_scroll())))
            bar_y = self.group_name_area.y + int((self.group_name_area.height - bar_height) * self.group_scroll / self.max_group_scroll())
            pygame.draw.rect(self.screen, (70, 72, 82), (self.group_name_area.right - 5, self.group_name_area.y, 5, self.group_name_area.height), border_radius=3)
            pygame.draw.rect(self.screen, ORANGE, (self.group_name_area.right - 5, bar_y, 5, bar_height), border_radius=3)

        self.random_button.draw(self.screen, self.font, pygame.Rect(left.x + 24, left.bottom - 64, 150, 44))
        self.clear_button.draw(self.screen, self.font, pygame.Rect(left.x + 188, left.bottom - 64, 100, 44))
        self.back_button.draw(self.screen, self.font, pygame.Rect(left.x + 302, left.bottom - 64, 96, 44))

        self.screen.blit(self.heading_font.render("Grupos", True, ORANGE), (right.x + 24, right.y + 22))

        self.group_result_area = pygame.Rect(right.x + 24, right.y + 70, right.width - 48, right.height - 94)
        self.group_result_scroll = max(0, min(self.group_result_scroll, self.max_group_result_scroll()))

        group_total = self.group_result_total()
        columns = self.group_result_columns(self.group_result_area.width)
        card_width = (self.group_result_area.width - (columns - 1) * 18) // columns
        card_height = self.group_result_card_height()

        old_clip = self.screen.get_clip()
        self.screen.set_clip(self.group_result_area)
        for index in range(group_total):
            col = index % columns
            row = index // columns
            rect = pygame.Rect(
                self.group_result_area.x + col * (card_width + 18),
                self.group_result_area.y + row * (card_height + 20) - self.group_result_scroll,
                card_width,
                card_height,
            )
            pygame.draw.rect(self.screen, PANEL_ALT, rect, border_radius=8)
            self.screen.blit(self.font.render(f"Grupo {index + 1}", True, ORANGE), (rect.x + 14, rect.y + 12))

            names = self.groups[index] if index < len(self.groups) else []
            max_names = max(0, (rect.height - 52) // 22)
            for name_index, name in enumerate(names[:max_names]):
                name_text = fit_text(self.small_font, name, rect.width - 28)
                text = self.small_font.render(f"{name_index + 1}. {name_text}", True, TEXT)
                self.screen.blit(text, (rect.x + 14, rect.y + 44 + name_index * 22))

            hidden = len(names) - max_names
            if hidden > 0:
                text = self.small_font.render(f"+{hidden}", True, MUTED)
                self.screen.blit(text, (rect.x + 14, rect.bottom - 24))
        self.screen.set_clip(old_clip)

        if self.max_group_result_scroll() > 0:
            bar_height = max(30, int(self.group_result_area.height * self.group_result_area.height / (self.group_result_area.height + self.max_group_result_scroll())))
            bar_y = self.group_result_area.y + int((self.group_result_area.height - bar_height) * self.group_result_scroll / self.max_group_result_scroll())
            pygame.draw.rect(self.screen, (70, 72, 82), (self.group_result_area.right - 5, self.group_result_area.y, 5, self.group_result_area.height), border_radius=3)
            pygame.draw.rect(self.screen, ORANGE, (self.group_result_area.right - 5, bar_y, 5, bar_height), border_radius=3)

    def draw_track(self, track, rect):
        pygame.draw.rect(self.screen, TRACK_BG, rect, border_radius=6)
        if not track:
            return

        for quad in track["quads"]:
            points = [world_to_screen(track, x, z, rect) for x, z in quad]
            pygame.draw.polygon(self.screen, TRACK_LINE, points, 1)

    def draw_players(self, track, players, rect):
        if not track:
            return

        for name, data in players.items():
            x, y = world_to_screen(track, data["x"], data["z"], rect)
            pygame.draw.circle(self.screen, ORANGE, (x, y), 5)
            label = self.small_font.render(fit_text(self.small_font, name, 70), True, TEXT)
            self.screen.blit(label, (x + 8, y - 8))

    def draw_leaderboard(self, players, rect):
        player_list = sorted_players(players)
        row_height = 40
        y = rect.y
        max_rows = max(0, rect.height // row_height)

        for index, (name, data) in enumerate(player_list[:max_rows]):
            row = pygame.Rect(rect.x, y, rect.width, row_height - 4)
            color = ROW_A if index % 2 == 0 else ROW_B
            pygame.draw.rect(self.screen, color, row, border_radius=5)

            pos = data["pos"] if data["pos"] is not None else "?"
            name_text = fit_text(self.font, f"{pos}. {name}", row.width - 12)
            kart_text = fit_text(self.small_font, data["kart"], row.width - 12)

            self.screen.blit(self.font.render(name_text, True, ORANGE), (row.x + 6, row.y + 3))
            self.screen.blit(self.small_font.render(kart_text, True, TEXT), (row.x + 6, row.y + 22))
            y += row_height + 6

        hidden = len(player_list) - max_rows
        if hidden > 0:
            footer = self.small_font.render(f"+{hidden} jogadores", True, MUTED)
            self.screen.blit(footer, (rect.x, rect.bottom - 18))

    def viewer_rects(self):
        width, height = self.window_size
        margin = 20
        gap = 20

        if self.server_count == 1:
            return [pygame.Rect(margin, 92, width - margin * 2, height - 112)]

        if self.server_count == 2:
            card_width = (width - margin * 2 - gap) // 2
            return [
                pygame.Rect(margin, 92, card_width, height - 112),
                pygame.Rect(margin + card_width + gap, 92, card_width, height - 112),
            ]

        card_width = (width - margin * 2 - gap) // 2
        card_height = (height - 112 - margin - gap) // 2
        return [
            pygame.Rect(margin + col * (card_width + gap), 92 + row * (card_height + gap), card_width, card_height)
            for row in range(2)
            for col in range(2)
        ]

    def draw_viewer_card(self, rect, state):
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=8)
        title = self.font.render(state["label"], True, ORANGE)
        subtitle = self.small_font.render(f"{state['track_id'] or 'sem dados'} | {state['ip']}", True, MUTED)
        self.screen.blit(title, (rect.x + 15, rect.y + 12))
        self.screen.blit(subtitle, (rect.x + 15, rect.y + 36))

        map_rect = pygame.Rect(rect.x + 15, rect.y + 60, int(rect.width * 0.58), rect.height - 76)
        board_rect = pygame.Rect(map_rect.right + 15, map_rect.y, rect.right - map_rect.right - 30, map_rect.height)

        self.draw_track(state["track"], map_rect)
        self.draw_players(state["track"], state["players"], map_rect)
        self.draw_leaderboard(state["players"], board_rect)

    def draw_viewer(self):
        self.read_packets()

        title = self.heading_font.render("Live Viewer", True, ORANGE)
        self.screen.blit(title, (24, 24))
        self.back_button.draw(self.screen, self.font, pygame.Rect(self.window_size[0] - 130, 22, 100, 42))

        if not self.viewer_sock:
            warning = self.small_font.render("UDP indisponivel. Viewer aberto so para teste visual.", True, ERROR)
            self.screen.blit(warning, (150, 30))

        for rect, state in zip(self.viewer_rects(), self.viewer_states):
            self.draw_viewer_card(rect, state)

    def run(self):
        running = True

        while running:
            running = self.handle_events()
            self.screen.fill(BG)

            if self.mode == "menu":
                self.draw_menu()
            elif self.mode == "groups":
                self.draw_groups()
            elif self.mode == "viewer":
                self.draw_viewer()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


def main():
    MenuApp().run()


if __name__ == "__main__":
    main()
