#!/usr/bin/env python3

import math
import random
import sys

import pygame

WINDOW_WIDTH = 1500
WINDOW_HEIGHT = 920
FPS = 60
MAX_PARTICIPANTS = 32
INPUT_COLS = 4
GROUP_COUNT = 4

BG_COLOR = (18, 18, 22)
PANEL_COLOR = (30, 31, 38)
PANEL_ALT = (38, 40, 48)
TEXT_COLOR = (240, 240, 240)
MUTED_COLOR = (160, 165, 175)
ACCENT_COLOR = (255, 150, 40)
ACCENT_HOVER = (255, 180, 80)
ERROR_COLOR = (220, 90, 90)
SUCCESS_COLOR = (90, 200, 120)
INPUT_BG = (24, 25, 31)
INPUT_ACTIVE = (50, 54, 66)
INPUT_BORDER = (90, 95, 110)


class TextInput:
    def __init__(self, rect, placeholder="", text=""):
        self.rect = pygame.Rect(rect)
        self.placeholder = placeholder
        self.text = text
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            return None

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return None
            if event.key == pygame.K_TAB:
                return "tab"
            return None

        if event.type == pygame.TEXTINPUT and self.active:
            if len(self.text) < 24:
                self.text += event.text

        return None

    def draw(self, surface, font, small_font, index):
        bg = INPUT_ACTIVE if self.active else INPUT_BG
        pygame.draw.rect(surface, bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, INPUT_BORDER, self.rect, width=2, border_radius=8)

        index_label = small_font.render(f"{index:02d}", True, MUTED_COLOR)
        surface.blit(index_label, (self.rect.x + 8, self.rect.y + 8))

        shown_text = self.text if self.text else self.placeholder
        text_color = TEXT_COLOR if self.text else MUTED_COLOR
        rendered = font.render(shown_text, True, text_color)
        surface.blit(rendered, (self.rect.x + 36, self.rect.y + 11))


class Button:
    def __init__(self, rect, label, accent=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.accent = accent

    def is_hovered(self):
        return self.rect.collidepoint(pygame.mouse.get_pos())

    def draw(self, surface, font):
        if self.accent:
            color = ACCENT_HOVER if self.is_hovered() else ACCENT_COLOR
            text_color = (20, 20, 20)
        else:
            color = (70, 76, 90) if self.is_hovered() else (58, 63, 76)
            text_color = TEXT_COLOR

        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        label = font.render(self.label, True, text_color)
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


def create_name_inputs(panel_rect, total_participants):
    inputs = []
    start_x = panel_rect.x + 24
    start_y = panel_rect.y + 150
    gap_x = 12
    gap_y = 10
    box_width = 168
    box_height = 44
    rows = max(1, math.ceil(total_participants / INPUT_COLS))

    for row in range(rows):
        for col in range(INPUT_COLS):
            idx = row * INPUT_COLS + col
            if idx >= total_participants:
                break
            x = start_x + col * (box_width + gap_x)
            y = start_y + row * (box_height + gap_y)
            inputs.append(
                TextInput((x, y, box_width, box_height), placeholder=f"Participante {idx + 1}")
            )

    return inputs


def distribute_groups(names):
    shuffled = names[:]
    random.shuffle(shuffled)
    group_count = min(GROUP_COUNT, len(shuffled))
    groups = [[] for _ in range(group_count)]

    for index, name in enumerate(shuffled):
        groups[index % group_count].append(name)

    return groups


def move_focus(inputs, current_index, direction):
    if not inputs:
        return 0
    inputs[current_index].active = False
    new_index = (current_index + direction) % len(inputs)
    inputs[new_index].active = True
    return new_index


def validate_total(total_input):
    value = total_input.text.strip()
    if not value:
        return None, "Indica primeiro quantos participantes havera.", ERROR_COLOR
    if not value.isdigit():
        return None, "O numero de participantes tem de ser um inteiro.", ERROR_COLOR

    total = int(value)
    if total < 2 or total > MAX_PARTICIPANTS:
        return None, f"Escolhe um valor entre 2 e {MAX_PARTICIPANTS}.", ERROR_COLOR

    return total, f"{total} participantes definidos.", SUCCESS_COLOR


def validate_names(inputs, total_participants):
    names = [input_box.text.strip() for input_box in inputs]
    filled = [name for name in names if name]

    if len(filled) != total_participants:
        return None, f"Tens de preencher os {total_participants} participantes antes de randomizar.", ERROR_COLOR

    return filled, "Grupos gerados com sucesso.", SUCCESS_COLOR


def draw_groups(screen, groups_panel, title_font, group_title_font, name_font, groups):
    groups_title = title_font.render("Grupos", True, TEXT_COLOR)
    screen.blit(groups_title, (groups_panel.x + 24, groups_panel.y + 22))

    card_width = 296
    card_height = 360
    card_gap_x = 24
    card_gap_y = 24
    card_start_x = groups_panel.x + 24
    card_start_y = groups_panel.y + 86

    for group_index in range(GROUP_COUNT):
        col = group_index % 2
        row = group_index // 2
        card_x = card_start_x + col * (card_width + card_gap_x)
        card_y = card_start_y + row * (card_height + card_gap_y)
        card = pygame.Rect(card_x, card_y, card_width, card_height)
        pygame.draw.rect(screen, (45, 47, 57), card, border_radius=16)
        pygame.draw.rect(screen, (70, 74, 90), card, width=2, border_radius=16)

        group_title = group_title_font.render(f"Grupo {group_index + 1}", True, ACCENT_COLOR)
        screen.blit(group_title, (card.x + 18, card.y + 16))

        if group_index >= len(groups) or not groups[group_index]:
            empty = name_font.render("Sem participantes.", True, MUTED_COLOR)
            screen.blit(empty, (card.x + 18, card.y + 58))
            continue

        for member_index, name in enumerate(groups[group_index], start=1):
            line = name_font.render(f"{member_index}. {name}", True, TEXT_COLOR)
            screen.blit(line, (card.x + 18, card.y + 54 + member_index * 32))


def main():
    pygame.init()
    pygame.display.set_caption("Randomizador de Grupos")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont("Segoe UI", 32, bold=True)
    subtitle_font = pygame.font.SysFont("Segoe UI", 20)
    font = pygame.font.SysFont("Segoe UI", 22)
    small_font = pygame.font.SysFont("Consolas", 16)
    button_font = pygame.font.SysFont("Segoe UI", 22, bold=True)
    group_title_font = pygame.font.SysFont("Segoe UI", 24, bold=True)
    name_font = pygame.font.SysFont("Segoe UI", 20)

    input_panel = pygame.Rect(24, 24, 760, 872)
    groups_panel = pygame.Rect(810, 24, 666, 872)

    total_input = TextInput((input_panel.x + 24, input_panel.y + 104, 200, 44), placeholder="Numero")
    total_input.active = True
    set_total_button = Button((input_panel.x + 236, input_panel.y + 104, 250, 44), "Definir participantes", accent=True)
    random_button = Button((input_panel.x + 24, input_panel.bottom - 88, 260, 48), "Randomizar grupos", accent=True)
    clear_button = Button((input_panel.x + 300, input_panel.bottom - 88, 180, 48), "Limpar")

    total_participants = 0
    inputs = []
    groups = []
    active_index = -1
    status_message = "Define primeiro quantos participantes vais usar."
    status_color = MUTED_COLOR

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            total_input.handle_event(event)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_RETURN:
                    if total_input.active or total_participants == 0:
                        result = validate_total(total_input)
                        if result[0] is not None:
                            total_participants, status_message, status_color = result
                            inputs = create_name_inputs(input_panel, total_participants)
                            groups = []
                            active_index = 0
                            total_input.active = False
                            if inputs:
                                inputs[0].active = True
                        else:
                            _, status_message, status_color = result
                    else:
                        names, status_message, status_color = validate_names(inputs, total_participants)
                        if names:
                            groups = distribute_groups(names)
                elif event.key == pygame.K_UP and inputs:
                    active_index = move_focus(inputs, active_index, -1)
                elif event.key in (pygame.K_DOWN, pygame.K_TAB) and inputs:
                    active_index = move_focus(inputs, active_index, 1)

            for i, input_box in enumerate(inputs):
                result = input_box.handle_event(event)
                if input_box.active:
                    active_index = i
                    total_input.active = False
                if result == "tab":
                    active_index = move_focus(inputs, i, 1)

            if set_total_button.clicked(event):
                result = validate_total(total_input)
                if result[0] is not None:
                    total_participants, status_message, status_color = result
                    inputs = create_name_inputs(input_panel, total_participants)
                    groups = []
                    active_index = 0
                    total_input.active = False
                    if inputs:
                        inputs[0].active = True
                else:
                    _, status_message, status_color = result

            if random_button.clicked(event) and total_participants > 0:
                names, status_message, status_color = validate_names(inputs, total_participants)
                if names:
                    groups = distribute_groups(names)

            if clear_button.clicked(event):
                total_input.text = ""
                total_input.active = True
                total_participants = 0
                inputs = []
                groups = []
                active_index = -1
                status_message = "Campos limpos. Define novamente o numero de participantes."
                status_color = MUTED_COLOR

        screen.fill(BG_COLOR)

        pygame.draw.rect(screen, PANEL_COLOR, input_panel, border_radius=18)
        pygame.draw.rect(screen, PANEL_ALT, groups_panel, border_radius=18)

        title = title_font.render("Participantes", True, TEXT_COLOR)
        screen.blit(title, (input_panel.x + 24, input_panel.y + 22))

        total_label = subtitle_font.render("Numero de participantes (2-32)", True, TEXT_COLOR)
        screen.blit(total_label, (input_panel.x + 24, input_panel.y + 76))
        total_input.draw(screen, font, small_font, 0)
        set_total_button.draw(screen, button_font)

        for i, input_box in enumerate(inputs, start=1):
            input_box.draw(screen, font, small_font, i)

        random_button.draw(screen, button_font)
        clear_button.draw(screen, button_font)

        status = subtitle_font.render(status_message, True, status_color)
        screen.blit(status, (input_panel.x + 24, input_panel.bottom - 30))

        draw_groups(screen, groups_panel, title_font, group_title_font, name_font, groups)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
