#!/usr/bin/env python3
"""Menu STK: navegação, eventos e organização dos participantes.
Na raiz do repositório: .venv/bin/python projeto/app_menu/app_menu.py
"""

import random
import pygame
import menu_ui as ui
from stk_viewer import Viewer

WINDOW_SIZE = (1280, 820)
MIN_SIZE = (980, 640)
MAX_PARTICIPANTS = 32
DEFAULT_GROUP_COUNT = 4
MAX_GROUPS = 16


class MenuApp:
    def __init__(self):
        pygame.init()
        self.window = pygame.Window("GLUA — STK", size=WINDOW_SIZE,
                                    resizable=True, allow_high_dpi=True)
        self.window.minimum_size = MIN_SIZE
        self.scale = 0
        self.resize()
        self.clock = pygame.time.Clock()

        self.mode = "menu"
        self.server_count = 1
        self.ip_boxes = []
        self.server_names = []
        for index in range(4):
            self.ip_boxes.append(ui.TextBox("127.0.0.1"))
            self.server_names.append(ui.TextBox(f"Server {index + 1}"))
        self.status = "Escolhe os servidores e indica os IPs."
        self.status_color = ui.MUTED

        self.start_button = ui.Button("Iniciar mapa", True)
        self.group_button = ui.Button("Configurar grupos")
        self.back_button = ui.Button("Voltar")
        self.clear_button = ui.Button("Limpar")
        self.random_button = ui.Button("Randomizar", True)
        self.count_buttons = {
            1: ui.Button("1", True),
            2: ui.Button("2"),
            4: ui.Button("4"),
        }

        self.viewer = Viewer()

        self.total_box = ui.TextBox("8")
        self.group_total_box = ui.TextBox(str(DEFAULT_GROUP_COUNT))
        self.name_boxes = []
        for index in range(8):
            self.name_boxes.append(ui.TextBox())
        self.group_scroll = 0
        self.group_name_area = pygame.Rect(0, 0, 1, 1)
        self.group_result_scroll = 0
        self.group_result_area = pygame.Rect(0, 0, 1, 1)
        self.groups = []
        icon = ui.load_image("Logo_Penguin_Orange.svg", 64, 64)
        if icon:
            self.window.set_icon(icon)

    def resize(self):
        # SDL distingue o tamanho da janela dos píxeis físicos (2x em Retina).
        self.screen = self.window.get_surface()
        self.window_size = self.screen.get_size()
        scale = self.screen.get_width() / self.window.size[0]
        if scale != self.scale:
            self.scale = scale
            self.heading_font = pygame.font.SysFont("Arial", round(20 * scale), bold=True)
            self.font = pygame.font.SysFont("Arial", round(16 * scale))
            self.small_font = pygame.font.SysFont("Arial", round(14 * scale))
            self.logo = ui.load_image("Logo_White.svg", 144 * scale, 60 * scale)
        width, height = self.window_size
        content_width = min(760 * scale, width - 64 * scale)
        self.content = pygame.Rect((width - content_width) // 2, 0, content_width, height)

    def change_mode(self, mode):
        if self.mode == "viewer" and mode != "viewer":
            self.close_viewer()
        self.mode = mode
        for box in self.ip_boxes + self.server_names + self.name_boxes + [self.total_box, self.group_total_box]:
            box.active = False

    def close_viewer(self):
        if not self.viewer.states:
            return
        try:
            self.viewer.close()
            self.status = "Pontuações guardadas em projeto/pontuacoes/."
            self.status_color = ui.ORANGE
        except OSError as error:
            self.status = f"Erro ao guardar pontuações: {error}"
            self.status_color = ui.ERROR
            print(f"[ERRO] {self.status}")

    def open_viewer(self):
        self.close_viewer()
        servers = []
        for index in range(self.server_count):
            name = self.server_names[index].text.strip()
            address = self.ip_boxes[index].text.strip()
            if not name:
                name = f"Server {index + 1}"
            if not address:
                address = "127.0.0.1"
            servers.append({"label": name, "ip": address})
        try:
            self.viewer.open(servers)
            self.status = "Voltar guarda as pontuações. O STK deve estar a correr no servidor."
            self.status_color = ui.ORANGE
        except OSError as error:
            self.status = f"Viewer aberto sem UDP: {error}"
            self.status_color = ui.ERROR
            print(f"[WARN] {self.status}")
        self.change_mode("viewer")

    def update_participant_count(self):
        value = self.total_box.text.strip()
        if not value.isdigit():
            self.status = "Numero de participantes invalido."
            self.status_color = ui.ERROR
            return False

        total = max(2, min(MAX_PARTICIPANTS, int(value)))
        if total != len(self.name_boxes):
            self.name_boxes = self.name_boxes[:total]
            while len(self.name_boxes) < total:
                self.name_boxes.append(ui.TextBox())
            self.groups = []

        self.total_box.text = str(total)
        self.group_scroll = min(self.group_scroll, self.max_group_scroll())
        self.status = f"{total} participantes preparados."
        self.status_color = ui.ORANGE
        return True

    def randomize_groups(self):
        names = []
        for box in self.name_boxes:
            name = box.text.strip()
            if name:
                names.append(name)
        if len(names) < 2:
            self.status = "Escreve pelo menos dois nomes."
            self.status_color = ui.ERROR
            return

        random.shuffle(names)
        group_count = DEFAULT_GROUP_COUNT
        value = self.group_total_box.text.strip()
        if value.isdigit():
            group_count = int(value)
        group_count = max(1, min(MAX_GROUPS, group_count))
        self.group_total_box.text = str(group_count)
        self.groups = []
        for index in range(group_count):
            self.groups.append([])

        for index, name in enumerate(names):
            self.groups[index % group_count].append(name)

        self.group_result_scroll = 0
        self.status = "Grupos criados."
        self.status_color = ui.ORANGE

    def handle_menu_event(self, event):
        for count, button in self.count_buttons.items():
            if button.clicked(event):
                self.server_count = count

        for box in self.ip_boxes[:self.server_count] + self.server_names[:self.server_count]:
            box.handle_event(event)

        if self.start_button.clicked(event):
            self.open_viewer()

        if self.group_button.clicked(event):
            self.change_mode("groups")
            self.status = ""
            self.status_color = ui.MUTED

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
            x, y = pygame.mouse.get_pos()
            mouse_pos = (round(x * self.scale), round(y * self.scale))
            if self.group_name_area.collidepoint(mouse_pos):
                self.group_scroll -= event.y * 36 * self.scale
                self.group_scroll = max(0, min(self.group_scroll, self.max_group_scroll()))
            if self.group_result_area.collidepoint(mouse_pos):
                self.group_result_scroll -= event.y * 36 * self.scale
                self.group_result_scroll = max(0, min(self.group_result_scroll, self.max_group_result_scroll()))

        for box in self.name_boxes:
            if event.type == pygame.MOUSEBUTTONDOWN and not self.group_name_area.collidepoint(event.pos):
                box.active = False
            else:
                box.handle_event(event)

        if self.clear_button.clicked(event):
            for box in self.name_boxes:
                box.text = ""
                box.active = False
            self.groups = []
            self.group_scroll = 0
            self.group_result_scroll = 0
            self.status = ""
            self.status_color = ui.MUTED

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

    def handle_event(self, event):
        if event.type in (pygame.QUIT, pygame.WINDOWCLOSE):
            return False
        if event.type in (pygame.WINDOWSIZECHANGED, pygame.WINDOWDISPLAYCHANGED):
            self.resize()
            ui.draw(self)
            return True

        # SDL envia cliques em coordenadas da janela; o desenho usa píxeis Retina.
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            x, y = event.pos
            event.pos = (round(x * self.scale), round(y * self.scale))

        escape = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        back = self.mode != "menu" and self.back_button.clicked(event)
        if escape or back:
            if self.mode == "menu":
                return False
            self.change_mode("menu")
            ui.draw(self)
            return True

        if self.mode == "menu":
            self.handle_menu_event(event)
        elif self.mode == "groups":
            self.handle_group_event(event)
        elif self.mode == "viewer" and event.type == pygame.MOUSEWHEEL:
            x, y = pygame.mouse.get_pos()
            mouse_pos = (round(x * self.scale), round(y * self.scale))
            for state in self.viewer.states:
                if state["board_rect"] and state["board_rect"].collidepoint(mouse_pos):
                    state["scroll"] = max(0, state["scroll"] - event.y)

        if event.type == pygame.MOUSEBUTTONDOWN:
            ui.draw(self)  # Atualiza as áreas dos botões antes do próximo clique.
        return True

    def run(self):
        try:
            ui.draw(self)
            self.window.flip()
            while True:
                for event in pygame.event.get():
                    if not self.handle_event(event):
                        return
                if self.mode == "viewer":
                    self.viewer.read_packets()
                ui.draw(self)
                self.window.flip()
                self.clock.tick(60)
        finally:
            self.close_viewer()
            pygame.quit()


if __name__ == "__main__":
    MenuApp().run()
