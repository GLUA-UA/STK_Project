#!/usr/bin/env python3
"""Menu STK: navegação, eventos e organização dos participantes.
Na raiz do repositório: .venv/bin/python projeto/app_menu/app_menu.py
"""

import random
import webbrowser
import pygame
import menu_ui as ui
from stk_viewer import Viewer
from server_process import Servers

WINDOW_SIZE = (1280, 820)
MIN_SIZE = (980, 640)
MAX_PARTICIPANTS = 32
DEFAULT_GROUP_COUNT = 4
MAX_GROUPS = 16


class MenuApp:
    def __init__(self):
        pygame.init()
        self.window = pygame.Window("GLUA - STK", size=WINDOW_SIZE,
                                    resizable=True, allow_high_dpi=True)
        self.window.minimum_size = MIN_SIZE
        self.scale = 0
        self.resize()
        self.clock = pygame.time.Clock()

        self.mode = "home"
        self.designer_link_rect = None
        self.server_count = 1
        self.ip_boxes = []
        self.server_names = []
        for index in range(4):
            self.ip_boxes.append(ui.TextBox("127.0.0.1"))
            self.server_names.append(ui.TextBox(f"Server {index + 1}"))
        print("[MENU] Iniciar menu STK.")
        self.set_status("Escolhe os servidores e indica os IPs.")

        self.start_button = ui.Button("Assistir", True)
        self.group_button = ui.Button("Configurar grupos", True)
        self.back_button = ui.Button("Voltar")
        self.clear_button = ui.Button("Limpar")
        self.random_button = ui.Button("Randomizar", True)
        self.count_buttons = {
            1: ui.Button("1", True),
            2: ui.Button("2"),
            4: ui.Button("4"),
        }

        self.viewer = Viewer()
        self.servers = Servers()

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
        icon = self.images["penguin"]
        if icon:
            self.window.set_icon(icon)

    def resize(self):
        # SDL distingue o tamanho da janela dos píxeis físicos (2x em Retina).
        self.screen = self.window.get_surface()
        scale = self.screen.get_width() / self.window.size[0]
        if scale != self.scale:
            self.scale = scale
            self.heading_font = pygame.font.SysFont("Arial", round(28 * scale), bold=True)
            self.font = pygame.font.SysFont("Arial", round(16 * scale))
            self.small_font = pygame.font.SysFont("Arial", round(14 * scale))
            self.images = ui.load_design_images(scale)
        width, height = self.screen.get_size()
        content_width = min(960 * scale, width - 96 * scale)
        self.content = pygame.Rect((width - content_width) // 2, 0, content_width, height)
        # O hero do Figma tem 999 x 600; o espaço fica igual para 1, 2 e 4 servidores.
        hero_height = min(300 * scale, height - 498 * scale)
        self.hero_rect = pygame.Rect(0, 80 * scale, hero_height * 999 / 600, hero_height)
        self.hero_rect.centerx = self.content.centerx
        self.hero = None
        image = self.images["hero"]
        if image:
            factor = min(self.hero_rect.width / image.get_width(), self.hero_rect.height / image.get_height())
            size = (round(image.get_width() * factor), round(image.get_height() * factor))
            self.hero = pygame.transform.smoothscale(image, size)

    def set_status(self, message, color=ui.MUTED):
        self.status = message
        self.status_color = color
        if message:
            print("[MENU]", message)

    def change_mode(self, mode):
        if self.mode == "viewer" and mode != "viewer":
            self.close_viewer()
        self.mode = mode
        print("[ECRÃ]", mode)
        for box in self.ip_boxes + self.server_names + self.name_boxes + [self.total_box, self.group_total_box]:
            box.active = False

    def close_viewer(self):
        self.servers.stop()
        if not self.viewer.states:
            return
        try:
            self.viewer.close()
            self.set_status("Pontuações guardadas em projeto/pontuacoes/.", ui.ORANGE)
        except OSError as error:
            self.set_status(f"Erro ao guardar pontuações: {error}", ui.ERROR)

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
            self.servers.start(servers)
            self.viewer.open(servers)
            self.set_status("A acompanhar servidores. Voltar para guardar e parar o servidor local.", ui.ORANGE)
        except (OSError, ValueError) as error:
            self.servers.stop()
            self.set_status(f"Erro ao abrir sessão: {error}", ui.ERROR)
            return
        self.change_mode("viewer")

    def update_participant_count(self):
        value = self.total_box.text.strip()
        if not value.isdigit():
            self.set_status("Numero de participantes invalido.", ui.ERROR)
            return False

        total = max(2, min(MAX_PARTICIPANTS, int(value)))
        if total != len(self.name_boxes):
            self.name_boxes = self.name_boxes[:total]
            while len(self.name_boxes) < total:
                self.name_boxes.append(ui.TextBox())
            self.groups = []

        self.total_box.text = str(total)
        self.group_scroll = min(self.group_scroll, self.max_group_scroll())
        self.set_status(f"{total} participantes preparados.", ui.ORANGE)
        return True

    def randomize_groups(self):
        names = []
        for box in self.name_boxes:
            name = box.text.strip()
            if name:
                names.append(name)
        if len(names) < 2:
            self.set_status("Escreve pelo menos dois nomes.", ui.ERROR)
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
        self.set_status("Grupos criados.", ui.ORANGE)
        for index, group in enumerate(self.groups, start=1):
            print(f"[GRUPO {index}] {', '.join(group)}")

    def handle_home_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.designer_link_rect and self.designer_link_rect.collidepoint(event.pos):
                webbrowser.open("https://duosky.pt/")
                return

        for count, button in self.count_buttons.items():
            if button.clicked(event):
                self.server_count = count
                self.set_status(f"{count} servidor(es) selecionado(s).")

        for index in range(self.server_count):
            self.ip_boxes[index].handle_event(event)
            self.server_names[index].handle_event(event)

        if self.start_button.clicked(event):
            self.open_viewer()

        if self.group_button.clicked(event):
            self.change_mode("groups")
            self.set_status("")

    def handle_group_event(self, event):
        total_was_active = self.total_box.active
        self.total_box.handle_event(event)
        self.group_total_box.handle_event(event)

        if total_was_active and not self.total_box.active:
            self.update_participant_count()

        if event.type == pygame.MOUSEWHEEL:
            if self.group_name_area.collidepoint(event.pos):
                self.group_scroll -= event.y * 36 * self.scale
                self.group_scroll = max(0, min(self.group_scroll, self.max_group_scroll()))
            if self.group_result_area.collidepoint(event.pos):
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
            self.set_status("")
            print("[GRUPOS] Campos e grupos limpos.")

        if self.random_button.clicked(event) and self.update_participant_count():
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
        if event.type == pygame.MOUSEWHEEL:
            event.pos = pygame.mouse.get_pos()
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
            x, y = event.pos
            event.pos = (round(x * self.scale), round(y * self.scale))

        escape = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        back = self.mode != "home" and self.back_button.clicked(event)
        if escape or back:
            if self.mode == "home":
                return False
            self.change_mode("home")
            ui.draw(self)
            return True

        if self.mode == "home":
            self.handle_home_event(event)
        elif self.mode == "groups":
            self.handle_group_event(event)
        elif self.mode == "viewer" and event.type == pygame.MOUSEWHEEL:
            for state in self.viewer.states:
                if state["board_rect"] and state["board_rect"].collidepoint(event.pos):
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
                    message = self.servers.check(self.viewer.states)
                    if message:
                        self.set_status(message, ui.ERROR)
                ui.draw(self)
                self.window.flip()
                self.clock.tick(60)
        finally:
            self.close_viewer()
            pygame.quit()
            print("[MENU] Menu STK terminado.")


if __name__ == "__main__":
    MenuApp().run()
