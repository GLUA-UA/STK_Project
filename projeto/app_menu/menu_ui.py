"""Controlos, imagens e desenho dos três ecrãs do menu."""

import os
import xml.etree.ElementTree as ET
import pygame
from stk_viewer import sorted_players

MENU_IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
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
        view_box = root.attrib["viewBox"].split()
        svg_width = float(view_box[2])
        svg_height = float(view_box[3])
        scale = min(width / svg_width, height / svg_height)
        size = (round(svg_width * scale), round(svg_height * scale))
        # O tamanho recebido já inclui os píxeis Retina. Não amplia um bitmap.
        return pygame.image.load_sized_svg(path, size)
    except (OSError, pygame.error, ET.ParseError, KeyError, IndexError, ValueError) as error:
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
        if self.accent:
            color = ORANGE
            label_color = (20, 20, 20)
        else:
            color = FIELD
            label_color = TEXT
        pygame.draw.rect(screen, color, self.rect)
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
        border_color = BORDER
        if self.active:
            border_color = ORANGE
        pygame.draw.rect(screen, border_color, self.rect, 1)

        value = self.text
        text_color = TEXT
        if not value:
            value = placeholder
            text_color = MUTED
        value = fit_text(font, value, self.rect.width - self.rect.height // 2)
        label = font.render(value, True, text_color)
        position = (self.rect.x + self.rect.height // 4, self.rect.centery)
        screen.blit(label, label.get_rect(midleft=position))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)

        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False

        elif event.type == pygame.TEXTINPUT and self.active and len(self.text) < 32:
            self.text += event.text


def fit_text(font, text, width):
    if font.size(text)[0] <= width:
        return text
    while text and font.size(text + "...")[0] > width:
        text = text[:-1]
    return text + "..."


def world_to_screen(track, x, z, rect, padding):
    track_width = track["width"] or 1
    track_height = track["height"] or 1
    scale = min(
        (rect.width - padding * 2) / track_width,
        (rect.height - padding * 2) / track_height,
    )
    left = rect.centerx - track_width * scale / 2
    bottom = rect.centery + track_height * scale / 2
    screen_x = left + (x - track["min_x"]) * scale
    screen_y = bottom - (z - track["min_z"]) * scale
    return int(screen_x), int(screen_y)


def draw_header(app):
    scale = app.scale
    width, height = app.screen.get_size()
    left, right = app.content.left, app.content.right
    if app.mode == "viewer":
        left, right = 32 * scale, width - 32 * scale
    if app.logo:
        app.screen.blit(app.logo, (left, 12 * scale))
    else:
        app.screen.blit(app.heading_font.render("GLUA", True, TEXT), (left, 28 * scale))
    app.screen.blit(app.heading_font.render("STK", True, TEXT), (left + 166 * scale, 28 * scale))
    pygame.draw.line(app.screen, BORDER, (left, 84 * scale), (right, 84 * scale))
    pygame.draw.line(app.screen, BORDER, (left, height - 42 * scale), (right, height - 42 * scale))
    status = fit_text(app.small_font, app.status, right - left)
    app.screen.blit(app.small_font.render(status, True, app.status_color), (left, height - 30 * scale))


def draw_menu(app):
    scale = app.scale
    left, right = app.content.left, app.content.right
    form_height = (204 + app.server_count * 68) * scale
    top = (app.screen.get_height() - form_height) // 2
    top = max(112 * scale, top)
    field_width = (app.content.width - 24 * scale) // 2
    second = left + field_width + 24 * scale
    app.screen.blit(app.heading_font.render("Mapa da corrida", True, TEXT), (left, top))
    app.screen.blit(app.font.render("Número de servidores", True, MUTED), (left, top + 38 * scale))
    for index, (count, button) in enumerate(app.count_buttons.items()):
        button.accent = count == app.server_count
        button.draw(app.screen, app.font, (left + index * 64 * scale, top + 64 * scale, 52 * scale, 36 * scale))
    for index in range(app.server_count):
        y = top + (120 + index * 68) * scale
        label = app.small_font.render(f"Servidor {index + 1} · Nome", True, MUTED)
        app.screen.blit(label, (left, y))
        app.screen.blit(app.small_font.render("IP / endereço", True, MUTED), (second, y))
        app.server_names[index].draw(app.screen, app.font, (left, y + 24 * scale, field_width, 40 * scale))
        app.ip_boxes[index].draw(app.screen, app.font, (second, y + 24 * scale, field_width, 40 * scale), "127.0.0.1")
    y = top + (132 + app.server_count * 68) * scale
    pygame.draw.line(app.screen, BORDER, (left, y), (right, y))
    app.group_button.draw(app.screen, app.font, (left, y + 24 * scale, 192 * scale, 40 * scale))
    app.start_button.draw(app.screen, app.font, (right - 192 * scale, y + 24 * scale, 192 * scale, 40 * scale))


def draw_groups(app):
    scale = app.scale
    left, right = app.content.left, app.content.right
    height = app.screen.get_height()
    column = (app.content.width - 32 * scale) // 2
    second = left + column + 32 * scale
    app.screen.blit(app.heading_font.render("Participantes e grupos", True, TEXT), (left, 112 * scale))
    app.screen.blit(app.font.render("Participantes", True, MUTED), (left, 166 * scale))
    app.total_box.draw(app.screen, app.font, (left + 120 * scale, 154 * scale, 72 * scale, 40 * scale))
    app.screen.blit(app.font.render("Grupos", True, MUTED), (second, 166 * scale))
    app.group_total_box.draw(app.screen, app.font, (second + 88 * scale, 154 * scale, 72 * scale, 40 * scale))
    app.group_name_area = pygame.Rect(left, 200 * scale, column, height - 320 * scale)
    app.group_result_area = pygame.Rect(second, 200 * scale, column, height - 320 * scale)
    app.group_scroll = max(0, min(app.group_scroll, app.max_group_scroll()))
    box_width = (column - 16 * scale) // 2
    app.screen.set_clip(app.group_name_area)
    for index, box in enumerate(app.name_boxes):
        x = left + (index % 2) * (box_width + 12 * scale)
        y = app.group_name_area.y + (index // 2) * 44 * scale - app.group_scroll
        box.draw(app.screen, app.font, (x, y, box_width, 36 * scale), f"Jogador {index + 1}")
    app.screen.set_clip(None)
    draw_scrollbar(app.screen, app.group_name_area, app.group_scroll, app.max_group_scroll())
    app.group_result_scroll = max(0, min(app.group_result_scroll, app.max_group_result_scroll()))
    app.screen.set_clip(app.group_result_area)
    y = app.group_result_area.y - app.group_result_scroll
    if not app.groups:
        app.screen.blit(app.font.render("Sem grupos criados.", True, MUTED), (second, y))
    for index, names in enumerate(app.groups):
        app.screen.blit(app.font.render(f"Grupo {index + 1}", True, ORANGE), (second, y))
        y += 28 * scale
        for name in names:
            label = fit_text(app.font, name, column - 16 * scale)
            app.screen.blit(app.font.render(label, True, TEXT), (second, y))
            y += 24 * scale
        y += 4 * scale
    app.screen.set_clip(None)
    draw_scrollbar(app.screen, app.group_result_area, app.group_result_scroll, app.max_group_result_scroll())
    y = height - 96 * scale
    pygame.draw.line(app.screen, BORDER, (left, y - 16 * scale), (right, y - 16 * scale))
    app.random_button.draw(app.screen, app.font, (left, y, 144 * scale, 40 * scale))
    app.clear_button.draw(app.screen, app.font, (left + 160 * scale, y, 104 * scale, 40 * scale))
    app.back_button.draw(app.screen, app.font, (right - 144 * scale, y, 144 * scale, 40 * scale))


def draw_map(app, track, players, rect):
    pygame.draw.rect(app.screen, FIELD, rect)
    if not track:
        return

    for quad in track["quads"]:
        points = []
        for x, z in quad:
            points.append(world_to_screen(track, x, z, rect, 22 * app.scale))
        pygame.draw.polygon(app.screen, BORDER, points, 1)

    for name, data in players.items():
        x, y = world_to_screen(track, data["x"], data["z"], rect, 22 * app.scale)
        pygame.draw.circle(app.screen, ORANGE, (x, y), round(5 * app.scale))
        label = app.small_font.render(fit_text(app.small_font, name, 90 * app.scale), True, TEXT)
        label_rect = label.get_rect(topleft=(x + 8 * app.scale, y - 8 * app.scale))
        if label_rect.right > rect.right:
            label_rect.right = x - 8 * app.scale
        label_rect.clamp_ip(rect)
        app.screen.blit(label, label_rect)


def draw_leaderboard(app, state, rect):
    scale = app.scale
    players = sorted_players(state["players"])
    rows = max(1, int((rect.height - 46 * scale) // (38 * scale)))
    state["board_rect"] = rect
    state["scroll"] = min(state["scroll"], max(0, len(players) - rows))
    start = state["scroll"]
    app.screen.blit(app.font.render("Classificação", True, TEXT), rect.topleft)
    y = rect.y + 28 * scale
    for name, player in players[start:start + rows]:
        pos = player["pos"]
        if pos is None:
            pos = "?"
        label = fit_text(app.font, f"{pos}. {name}", rect.width)
        kart = fit_text(app.small_font, player["kart"], rect.width)
        app.screen.blit(app.font.render(label, True, ORANGE), (rect.x, y))
        app.screen.blit(app.small_font.render(kart, True, MUTED), (rect.x, y + 20 * scale))
        y += 38 * scale
    if len(players) > rows:
        label = f"{start + 1}–{min(start + rows, len(players))} / {len(players)} · scroll"
        app.screen.blit(app.small_font.render(label, True, MUTED), (rect.x, rect.bottom - 18 * scale))


def draw_viewer(app):
    scale = app.scale
    width, height = app.screen.get_size()
    columns = 1
    rows = 1
    if app.server_count > 1:
        columns = 2
    if app.server_count == 4:
        rows = 2
    cell_width = (width - 64 * scale - (columns - 1) * 32 * scale) // columns
    cell_height = (height - 228 * scale - (rows - 1) * 24 * scale) // rows
    for index, state in enumerate(app.viewer.states):
        x = 32 * scale + (index % columns) * (cell_width + 32 * scale)
        y = 108 * scale + (index // columns) * (cell_height + 24 * scale)
        title = fit_text(app.heading_font, state["label"], cell_width)
        app.screen.blit(app.heading_font.render(title, True, TEXT), (x, y))
        detail = f"{state['ip']} · {state['track_id'] or 'à espera da corrida'}"
        if state["error"]:
            detail = f"{state['ip']} · {state['error']}"
        detail = fit_text(app.small_font, detail, cell_width)
        app.screen.blit(app.small_font.render(detail, True, MUTED), (x, y + 28 * scale))
        board_width = min(240 * scale, cell_width * 2 // 5)
        map_rect = pygame.Rect(x, y + 60 * scale, cell_width - board_width - 24 * scale, cell_height - 60 * scale)
        board_rect = pygame.Rect(map_rect.right + 24 * scale, map_rect.y, board_width, map_rect.height)
        app.screen.set_clip(map_rect)
        draw_map(app, state["track"], state["players"], map_rect)
        if not state["track"]:
            message = "Mapa indisponível" if state["track_id"] else "Sem dados"
            text = app.small_font.render(message, True, MUTED)
            app.screen.blit(text, text.get_rect(center=map_rect.center))
        app.screen.set_clip(None)
        draw_leaderboard(app, state, board_rect)
    app.back_button.draw(app.screen, app.font, (width - 176 * scale, height - 104 * scale, 144 * scale, 40 * scale))


def draw(app):
    app.screen.fill(BG)
    draw_header(app)
    if app.mode == "menu":
        draw_menu(app)
    elif app.mode == "groups":
        draw_groups(app)
    elif app.mode == "viewer":
        draw_viewer(app)
