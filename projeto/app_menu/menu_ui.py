"""Controlos, imagens e desenho dos três ecrãs do menu."""

import os
import xml.etree.ElementTree as ET
import pygame
from stk_viewer import sorted_players

MENU_IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
BG = (16, 10, 4)
FIELD = (0, 0, 0)
BORDER = (49, 25, 6)
ORANGE = (247, 127, 28)
TEXT = (230, 230, 230)
MUTED = (170, 165, 160)
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


def load_design_images(scale):
    # SVGs lidos apenas quando a escala do ecrã muda, nunca a cada frame.
    images = {}
    images["hero"] = None
    try:
        images["hero"] = pygame.image.load(os.path.join(MENU_IMAGES_DIR, "stk_hero.png"))
    except (OSError, pygame.error) as error:
        print("[AVISO] Hero STK indisponível:", error)
    images["penguin"] = load_image("design_vectors/logo_penguin.svg", 32 * scale, 40 * scale)
    images["glua"] = load_image("design_vectors/logo_glua.svg", 62 * scale, 25 * scale)
    images["aetua"] = load_image("design_vectors/logo_aetua.svg", 90 * scale, 36 * scale)
    for name in ("map", "race", "groups"):
        images[name] = load_image(f"design_vectors/icon_{name}.svg", 32 * scale, 32 * scale)
    for name in ("settings", "play", "text"):
        images[name] = load_image(f"design_vectors/icon_{name}.svg", 18 * scale, 18 * scale)
    for count, filename in ((1, "icon_person.svg"), (2, "icon_people.svg"), (4, "icon_groups.svg")):
        image = load_image("design_vectors/" + filename, 20 * scale, 20 * scale)
        active_image = None
        if image:
            # Mantém o alpha do SVG: branco em fundo preto, preto em fundo laranja.
            image.fill((230, 230, 230, 0), special_flags=pygame.BLEND_RGBA_MAX)
            active_image = image.copy()
            active_image.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        images[f"people_{count}"] = image
        images[f"people_{count}_active"] = active_image
    return images


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

    def draw(self, screen, font, rect, image=None):
        self.rect = pygame.Rect(rect)
        if self.accent:
            color = ORANGE
            label_color = (20, 20, 20)
        else:
            color = FIELD
            label_color = TEXT
        radius = self.rect.height // 2
        pygame.draw.rect(screen, color, self.rect, border_radius=radius)
        if not self.accent:
            pygame.draw.rect(screen, BORDER, self.rect, 1, border_radius=radius)
        label = font.render(self.text, True, label_color)
        width = label.get_width()
        if image:
            width += image.get_width() + self.rect.height // 5
        left = self.rect.centerx - width // 2
        if image:
            screen.blit(image, image.get_rect(midleft=(left, self.rect.centery)))
            left += image.get_width() + self.rect.height // 5
        screen.blit(label, label.get_rect(midleft=(left, self.rect.centery)))

    def clicked(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        return self.rect.collidepoint(event.pos)


class TextBox:
    def __init__(self, text=""):
        self.text = text
        self.active = False
        self.rect = pygame.Rect(0, 0, 1, 1)

    def draw(self, screen, font, rect, placeholder="", image=None):
        self.rect = pygame.Rect(rect)
        pygame.draw.rect(screen, FIELD, self.rect, border_radius=round(self.rect.height / 10))
        border_color = BORDER
        if self.active:
            border_color = ORANGE
        pygame.draw.rect(screen, border_color, self.rect, 1, border_radius=round(self.rect.height / 10))

        value = self.text
        text_color = TEXT
        if not value:
            value = placeholder
            text_color = MUTED
        left = self.rect.x + self.rect.height // 4
        if image:
            screen.blit(image, image.get_rect(midleft=(left, self.rect.centery)))
            left += image.get_width() + self.rect.height // 5
        value = fit_text(font, value, self.rect.right - left - self.rect.height // 4)
        label = font.render(value, True, text_color)
        position = (left, self.rect.centery)
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
    left, right = 32 * scale, width - 32 * scale
    penguin = app.images["penguin"]
    wordmark = app.images["glua"]
    if penguin and wordmark:
        app.screen.blit(penguin, (left, 20 * scale))
        app.screen.blit(wordmark, (left + 42 * scale, 28 * scale))
    else:
        app.screen.blit(app.heading_font.render("GLUA", True, TEXT), (left, 28 * scale))
    partner = app.images["aetua"]
    if partner:
        app.screen.blit(partner, (right - partner.get_width(), 22 * scale))
    pygame.draw.line(app.screen, BORDER, (left, height - 42 * scale), (right, height - 42 * scale))
    status = fit_text(app.small_font, app.status, right - left)
    app.screen.blit(app.small_font.render(status, True, app.status_color), (left, height - 30 * scale))


def draw_server_selector(app, top):
    scale = app.scale
    label = app.font.render("Número de Servidores", True, TEXT)
    app.screen.blit(label, label.get_rect(center=(app.content.centerx, top + 48 * scale)))
    selector = pygame.Rect(app.content.centerx - 94.5 * scale, top + 64 * scale, 189 * scale, 44 * scale)
    radius = round(4 * scale)
    pygame.draw.rect(app.screen, FIELD, selector, border_radius=radius)
    for index, count in enumerate((1, 2, 4)):
        button = app.count_buttons[count]
        button.rect = pygame.Rect(selector.x + index * 63 * scale, selector.y, 63 * scale, selector.height)
        button.accent = count == app.server_count
        color = TEXT
        image = app.images[f"people_{count}"]
        if button.accent:
            color = FIELD
            image = app.images[f"people_{count}_active"]
            left_radius = 0
            right_radius = 0
            if index == 0:
                left_radius = radius
            elif index == 2:
                right_radius = radius
            pygame.draw.rect(app.screen, ORANGE, button.rect,
                             border_top_left_radius=left_radius, border_bottom_left_radius=left_radius,
                             border_top_right_radius=right_radius, border_bottom_right_radius=right_radius)
        number = app.font.render(str(count), True, color)
        width = number.get_width()
        if image:
            width += image.get_width() + 8 * scale
        x = button.rect.centerx - width // 2
        if image:
            app.screen.blit(image, image.get_rect(midleft=(x, button.rect.centery)))
            x += image.get_width() + 8 * scale
        app.screen.blit(number, number.get_rect(midleft=(x, button.rect.centery)))
        if index > 0:
            pygame.draw.line(app.screen, (26, 26, 26), button.rect.topleft, button.rect.bottomleft, max(1, round(scale)))
    pygame.draw.rect(app.screen, (26, 26, 26), selector, max(1, round(scale)), border_radius=radius)


def draw_home(app):
    scale = app.scale
    left, right = app.content.left, app.content.right
    if app.hero:
        app.screen.blit(app.hero, app.hero.get_rect(center=app.hero_rect.center))
    credit = app.small_font.render("Obrigado à DuoSky pelo design da interface · https://duosky.pt/", True, MUTED)
    app.screen.blit(credit, credit.get_rect(midtop=(app.content.centerx, app.hero_rect.bottom + 12 * scale)))
    # O Figma deixa 100 px entre hero e secção; aqui o hero usa metade da altura.
    top = app.hero_rect.bottom + 50 * scale
    app.screen.blit(app.heading_font.render("Configurar servidores", True, TEXT), (left, top))
    if app.images["map"]:
        app.screen.blit(app.images["map"], (right - 32 * scale, top))
    draw_server_selector(app, top)

    # Quatro servidores usam duas colunas; os restantes mantêm nome e IP lado a lado.
    column_width = app.content.width
    if app.server_count == 4:
        column_width = (app.content.width - 24 * scale) // 2
    field_width = (column_width - 12 * scale) // 2
    for index in range(app.server_count):
        x = left
        row = index
        if app.server_count == 4:
            x += (index % 2) * (column_width + 24 * scale)
            row = index // 2
        second = x + field_width + 12 * scale
        y = top + (120 + row * 68) * scale
        label = app.small_font.render(f"Servidor {index + 1} · Nome", True, MUTED)
        app.screen.blit(label, (x, y))
        app.screen.blit(app.small_font.render("IP / endereço", True, MUTED), (second, y))
        app.server_names[index].draw(app.screen, app.font, (x, y + 24 * scale, field_width, 40 * scale), image=app.images["text"])
        app.ip_boxes[index].draw(app.screen, app.font, (second, y + 24 * scale, field_width, 40 * scale), "127.0.0.1", app.images["text"])
    rows = app.server_count
    if rows == 4:
        rows = 2
    y = top + (132 + rows * 68) * scale
    pygame.draw.line(app.screen, BORDER, (left, y), (right, y))
    app.group_button.draw(app.screen, app.font, (left, y + 16 * scale, 208 * scale, 40 * scale), app.images["settings"])
    app.start_button.draw(app.screen, app.font, (right - 176 * scale, y + 16 * scale, 176 * scale, 40 * scale), app.images["play"])


def draw_groups(app):
    scale = app.scale
    left, right = app.content.left, app.content.right
    height = app.screen.get_height()
    column = (app.content.width - 32 * scale) // 2
    second = left + column + 32 * scale
    app.screen.blit(app.heading_font.render("Participantes e grupos", True, TEXT), (left, 112 * scale))
    if app.images["groups"]:
        app.screen.blit(app.images["groups"], (right - 32 * scale, 112 * scale))
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
        box.draw(app.screen, app.font, (x, y, box_width, 36 * scale), f"Jogador {index + 1}", app.images["text"])
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


def draw_map(app, track, players, rect, title):
    pygame.draw.rect(app.screen, FIELD, rect, border_radius=round(8 * app.scale))
    pygame.draw.rect(app.screen, ORANGE, rect, max(1, round(app.scale)), border_radius=round(8 * app.scale))
    label = fit_text(app.font, title, rect.width - 24 * app.scale)
    app.screen.blit(app.font.render(label, True, TEXT), (rect.x + 12 * app.scale, rect.y + 8 * app.scale))
    if not track:
        return

    content = pygame.Rect(rect.x, rect.y + 32 * app.scale, rect.width, rect.height - 32 * app.scale)
    for quad in track["quads"]:
        points = []
        for x, z in quad:
            points.append(world_to_screen(track, x, z, content, 12 * app.scale))
        pygame.draw.polygon(app.screen, MUTED, points, 1)

    for name, data in players.items():
        x, y = world_to_screen(track, data["x"], data["z"], content, 12 * app.scale)
        pygame.draw.circle(app.screen, ORANGE, (x, y), round(5 * app.scale))
        label = app.small_font.render(fit_text(app.small_font, name, 90 * app.scale), True, TEXT)
        label_rect = label.get_rect(topleft=(x + 8 * app.scale, y - 8 * app.scale))
        if label_rect.right > content.right:
            label_rect.right = x - 8 * app.scale
        label_rect.clamp_ip(content)
        app.screen.blit(label, label_rect)


def draw_leaderboard(app, state, rect):
    scale = app.scale
    players = sorted_players(state["players"])
    rows = max(1, int((rect.height - 48 * scale) // (24 * scale)))
    state["board_rect"] = rect
    state["scroll"] = min(state["scroll"], max(0, len(players) - rows))
    start = state["scroll"]
    app.screen.blit(app.font.render("Classificação", True, TEXT), rect.topleft)
    pygame.draw.line(app.screen, BORDER, (rect.x, rect.y + 24 * scale), (rect.right, rect.y + 24 * scale))
    y = rect.y + 28 * scale
    for name, player in players[start:start + rows]:
        pos = player["pos"]
        if pos is None:
            pos = "?"
        label = fit_text(app.font, f"{pos}. {name}", rect.width * 2 // 3 - 16 * scale)
        kart = fit_text(app.small_font, player["kart"], rect.width // 3)
        app.screen.blit(app.font.render(label, True, TEXT), (rect.x, y))
        app.screen.blit(app.small_font.render(kart, True, MUTED), (rect.x + rect.width * 2 // 3, y + 2 * scale))
        y += 24 * scale
    if len(players) > rows:
        label = f"{start + 1}–{min(start + rows, len(players))} / {len(players)} · scroll"
        app.screen.blit(app.small_font.render(label, True, MUTED), (rect.x, rect.bottom - 18 * scale))


def draw_server_view(app, state, area, compact):
    scale = app.scale
    name = fit_text(app.font, state["label"], area.width)
    app.screen.blit(app.font.render(name, True, TEXT), area.topleft)
    status = "À espera de dados do STK"
    color = ORANGE
    if state["error"]:
        status = "Erro: " + state["error"]
        color = ERROR
    elif state["receiving"]:
        status = "Dados recebidos"
    detail = fit_text(app.small_font, f"{state['ip']} | {status}", area.width - 20 * scale)
    app.screen.blit(app.small_font.render(detail, True, MUTED), (area.x, area.y + 24 * scale))
    dot_x = area.x + app.small_font.size(detail)[0] + 10 * scale
    pygame.draw.circle(app.screen, color, (round(dot_x), round(area.y + 32 * scale)), round(3 * scale))

    map_top = area.y + 48 * scale
    if compact:
        # Na grelha 2x2, a classificação ao lado deixa a pista maior e legível.
        board_width = area.width * 2 // 5
        map_rect = pygame.Rect(area.x, map_top, area.width - board_width - 16 * scale, area.bottom - map_top)
        board_rect = pygame.Rect(map_rect.right + 16 * scale, map_top, board_width, map_rect.height)
    else:
        board_height = 144 * scale
        if area.height < 500 * scale:
            board_height = 96 * scale
        board_rect = pygame.Rect(area.x + 12 * scale, area.bottom - board_height,
                                 area.width - 24 * scale, board_height)
        map_rect = pygame.Rect(area.x, map_top, area.width, board_rect.top - 20 * scale - map_top)

    app.screen.set_clip(map_rect)
    draw_map(app, state["track"], state["players"], map_rect, state["track_id"] or "Pista")
    if not state["track"]:
        message = "Mapa indisponível" if state["track_id"] else "Sem dados"
        text = app.small_font.render(message, True, MUTED)
        app.screen.blit(text, text.get_rect(center=map_rect.center))
    app.screen.set_clip(None)
    draw_leaderboard(app, state, board_rect)


def draw_viewer(app):
    scale = app.scale
    width, height = app.screen.get_size()
    content_width = min(1036 * scale, width - 96 * scale)
    left = (width - content_width) // 2
    right = left + content_width
    app.screen.blit(app.heading_font.render("Assistir jogo", True, TEXT), (left, 80 * scale))
    if app.images["race"]:
        app.screen.blit(app.images["race"], (right - 32 * scale, 80 * scale))

    count = len(app.viewer.states)
    columns = 1
    rows = 1
    if count == 2:
        columns = 2
    elif count == 4:
        columns = 2
        rows = 2
    gap = 24 * scale
    cell_width = (content_width - (columns - 1) * gap) // columns
    cell_height = (height - 216 * scale - (rows - 1) * gap) // rows
    for index, state in enumerate(app.viewer.states):
        x = left + (index % columns) * (cell_width + gap)
        y = 128 * scale + (index // columns) * (cell_height + gap)
        area = pygame.Rect(x, y, cell_width, cell_height)
        draw_server_view(app, state, area, count == 4)
    app.back_button.draw(app.screen, app.font, (right - 144 * scale, height - 78 * scale, 144 * scale, 32 * scale))


def draw(app):
    app.screen.fill(BG)
    draw_header(app)
    if app.mode == "home":
        draw_home(app)
    elif app.mode == "groups":
        draw_groups(app)
    elif app.mode == "viewer":
        draw_viewer(app)
