#!/usr/bin/env python3
"""
TETRIS FUTURISTA
Un Tetris con interfaz neón/futurista hecho con Pygame,
con música de fondo en bucle infinito.

Requisitos:
    pip install pygame

Ejecutar:
    python tetris_futurista.py

Controles:
    Flecha Izquierda / Derecha : mover pieza
    Flecha Abajo               : caída suave (soft drop)
    Espacio                    : caída instantánea (hard drop)
    Flecha Arriba / X          : rotar en sentido horario
    Z                          : rotar en sentido antihorario
    C                          : guardar pieza (hold)
    P                          : pausa
    M                          : mute / unmute música
    R                          : reiniciar (tras game over)
    ESC                        : salir
"""

import os
import sys
import random
import math

import pygame

# ------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_PATH = os.path.join(BASE_DIR, "assets", "tetris_theme.mp3")

COLS, ROWS = 10, 20
CELL = 34
BOARD_X, BOARD_Y = 60, 60

SIDE_PANEL_W = 260
WIN_W = BOARD_X * 2 + COLS * CELL + SIDE_PANEL_W
WIN_H = BOARD_Y * 2 + ROWS * CELL

FPS = 60

# Paleta futurista (fondo oscuro + acentos neón)
BG_TOP = (8, 10, 24)
BG_BOTTOM = (18, 8, 36)
PANEL_BG = (14, 16, 32)
GRID_LINE = (40, 46, 74)
NEON_CYAN = (0, 255, 240)
NEON_MAGENTA = (255, 0, 200)
NEON_PURPLE = (150, 80, 255)
NEON_BLUE = (60, 130, 255)
TEXT_MAIN = (220, 240, 255)
TEXT_DIM = (120, 140, 170)

# Colores neón por tipo de pieza
PIECE_COLORS = {
    "I": (0, 240, 255),
    "O": (255, 230, 0),
    "T": (200, 0, 255),
    "S": (0, 255, 120),
    "Z": (255, 40, 90),
    "J": (60, 110, 255),
    "L": (255, 150, 0),
}

# Formas de las 7 piezas (matrices 4x4, rotación 0)
SHAPES = {
    "I": [
        ["....", "IIII", "....", "...."],
        ["..I.", "..I.", "..I.", "..I."],
        ["....", "....", "IIII", "...."],
        [".I..", ".I..", ".I..", ".I.."],
    ],
    "O": [
        [".OO.", ".OO.", "....", "...."],
        [".OO.", ".OO.", "....", "...."],
        [".OO.", ".OO.", "....", "...."],
        [".OO.", ".OO.", "....", "...."],
    ],
    "T": [
        [".T..", "TTT.", "....", "...."],
        [".T..", ".TT.", ".T..", "...."],
        ["....", "TTT.", ".T..", "...."],
        [".T..", "TT..", ".T..", "...."],
    ],
    "S": [
        [".SS.", "SS..", "....", "...."],
        [".S..", ".SS.", "..S.", "...."],
        ["....", ".SS.", "SS..", "...."],
        ["S...", "SS..", ".S..", "...."],
    ],
    "Z": [
        ["ZZ..", ".ZZ.", "....", "...."],
        ["..Z.", ".ZZ.", ".Z..", "...."],
        ["....", "ZZ..", ".ZZ.", "...."],
        [".Z..", "ZZ..", "Z...", "...."],
    ],
    "J": [
        ["J...", "JJJ.", "....", "...."],
        [".JJ.", ".J..", ".J..", "...."],
        ["....", "JJJ.", "..J.", "...."],
        [".J..", ".J..", "JJ..", "...."],
    ],
    "L": [
        ["..L.", "LLL.", "....", "...."],
        [".L..", ".L..", ".LL.", "...."],
        ["....", "LLL.", "L...", "...."],
        ["LL..", ".L..", ".L..", "...."],
    ],
}

BAG = list(SHAPES.keys())


# ------------------------------------------------------------------
# UTILIDADES VISUALES
# ------------------------------------------------------------------

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def make_vertical_gradient(w, h, top_color, bottom_color):
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(1, h - 1)
        surf.set_at((0, y), lerp_color(top_color, bottom_color, t))
    surf = pygame.transform.scale(surf.subsurface((0, 0, 1, h)), (w, h))
    return surf


def draw_glow_rect(surface, rect, color, glow_radius=14, base_alpha=90):
    """Dibuja un halo de resplandor alrededor de un rectángulo."""
    glow = pygame.Surface(
        (rect.width + glow_radius * 2, rect.height + glow_radius * 2),
        pygame.SRCALPHA,
    )
    steps = 6
    for i in range(steps, 0, -1):
        alpha = int(base_alpha * (i / steps) ** 2)
        pad = int(glow_radius * (i / steps))
        r = pygame.Rect(
            glow_radius - pad,
            glow_radius - pad,
            rect.width + pad * 2,
            rect.height + pad * 2,
        )
        pygame.draw.rect(glow, (*color, alpha), r, border_radius=8)
    surface.blit(glow, (rect.x - glow_radius, rect.y - glow_radius))


def draw_neon_cell(surface, x, y, size, color, filled=True, alpha=255):
    rect = pygame.Rect(x, y, size, size)
    if filled:
        inner = pygame.Surface((size, size), pygame.SRCALPHA)
        # relleno con degradado sutil
        top = lerp_color(color, (255, 255, 255), 0.25)
        bottom = lerp_color(color, (0, 0, 0), 0.25)
        for yy in range(size):
            t = yy / max(1, size - 1)
            row_color = lerp_color(top, bottom, t)
            pygame.draw.line(inner, (*row_color, alpha), (0, yy), (size, yy))
        pygame.draw.rect(inner, (*color, alpha), inner.get_rect(), width=2, border_radius=4)
        surface.blit(inner, (x, y))
        # brillo interior
        highlight = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(
            highlight, (255, 255, 255, 40), (2, 2, size - 4, size // 3), border_radius=3
        )
        surface.blit(highlight, (x, y))
    else:
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), s.get_rect(), width=2, border_radius=4)
        surface.blit(s, (x, y))


def draw_text_glow(surface, font, text, color, pos, glow_color=None, center=False):
    glow_color = glow_color or color
    x, y = pos
    glow_surf = font.render(text, True, glow_color)
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
        s = glow_surf.copy()
        s.set_alpha(40)
        r = s.get_rect()
        if center:
            r.center = (x + dx, y + dy)
        else:
            r.topleft = (x + dx, y + dy)
        surface.blit(s, r)
    main_surf = font.render(text, True, color)
    r = main_surf.get_rect()
    if center:
        r.center = (x, y)
    else:
        r.topleft = (x, y)
    surface.blit(main_surf, r)
    return r


# ------------------------------------------------------------------
# LÓGICA DEL JUEGO
# ------------------------------------------------------------------

class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.rot = 0
        self.x = 3
        self.y = -2

    def cells(self, rot=None):
        rot = self.rot if rot is None else rot % 4
        shape = SHAPES[self.kind][rot]
        result = []
        for r, row in enumerate(shape):
            for c, ch in enumerate(row):
                if ch != ".":
                    result.append((self.x + c, self.y + r))
        return result


def new_bag():
    bag = BAG.copy()
    random.shuffle(bag)
    return bag


class Tetris:
    def __init__(self):
        self.reset()

    def reset(self):
        self.grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.bag = new_bag()
        self.next_bag = new_bag()
        self.current = Piece(self.bag.pop(0))
        self.hold_kind = None
        self.can_hold = True
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.fall_time = 0.0
        self.fall_speed = 0.8
        self.lock_delay = 0.5
        self.lock_timer = 0.0
        self.is_grounded = False
        self.combo = 0
        self.clear_flash = []  # filas que están destellando
        self.flash_timer = 0.0
        self.shake = 0.0

    def next_pieces(self, count=3):
        preview = self.bag + self.next_bag
        return preview[:count]

    def _advance_bag(self):
        if not self.bag:
            self.bag = self.next_bag
            self.next_bag = new_bag()

    def spawn_new(self):
        self._advance_bag()
        kind = self.bag.pop(0)
        self.current = Piece(kind)
        self.can_hold = True
        if self.collides(self.current, self.current.x, self.current.y, self.current.rot):
            self.game_over = True

    def collides(self, piece, x, y, rot):
        for cx, cy in piece.cells(rot):
            nx, ny = x + (cx - piece.x), y + (cy - piece.y)
            if nx < 0 or nx >= COLS or ny >= ROWS:
                return True
            if ny >= 0 and self.grid[ny][nx] is not None:
                return True
        return False

    def move(self, dx):
        if self.game_over or self.paused:
            return
        p = self.current
        if not self.collides(p, p.x + dx, p.y, p.rot):
            p.x += dx
            self.lock_timer = 0.0

    def rotate(self, direction=1):
        if self.game_over or self.paused:
            return
        p = self.current
        new_rot = (p.rot + direction) % 4
        # Wall kicks sencillos
        kicks = [0, -1, 1, -2, 2]
        for k in kicks:
            if not self.collides(p, p.x + k, p.y, new_rot):
                p.x += k
                p.rot = new_rot
                self.lock_timer = 0.0
                return

    def soft_drop(self):
        if self.game_over or self.paused:
            return
        p = self.current
        if not self.collides(p, p.x, p.y + 1, p.rot):
            p.y += 1
            self.score += 1
        else:
            self.lock_piece()

    def hard_drop(self):
        if self.game_over or self.paused:
            return
        p = self.current
        dist = 0
        while not self.collides(p, p.x, p.y + 1, p.rot):
            p.y += 1
            dist += 1
        self.score += dist * 2
        self.lock_piece()
        self.shake = 6.0

    def ghost_y(self):
        p = self.current
        gy = p.y
        while not self.collides(p, p.x, gy + 1, p.rot):
            gy += 1
        return gy

    def hold(self):
        if self.game_over or self.paused or not self.can_hold:
            return
        cur_kind = self.current.kind
        if self.hold_kind is None:
            self.hold_kind = cur_kind
            self.spawn_new()
        else:
            self.hold_kind, cur_kind = cur_kind, self.hold_kind
            self.current = Piece(cur_kind)
        self.can_hold = False
        self.lock_timer = 0.0

    def lock_piece(self):
        p = self.current
        for cx, cy in p.cells():
            if cy < 0:
                self.game_over = True
                return
            self.grid[cy][cx] = PIECE_COLORS[p.kind]
        self.clear_lines()
        self.spawn_new()
        self.lock_timer = 0.0

    def clear_lines(self):
        full_rows = [r for r in range(ROWS) if all(self.grid[r][c] is not None for c in range(COLS))]
        if not full_rows:
            self.combo = 0
            return
        self.clear_flash = full_rows
        self.flash_timer = 0.15

        n = len(full_rows)
        points = {1: 100, 2: 300, 3: 500, 4: 800}
        self.score += points.get(n, 0) * self.level
        self.combo += 1
        self.score += 50 * (self.combo - 1) * self.level
        self.lines += n
        new_level = 1 + self.lines // 10
        if new_level != self.level:
            self.level = new_level
            self.fall_speed = max(0.08, 0.8 - (self.level - 1) * 0.07)

        for r in full_rows:
            del self.grid[r]
            self.grid.insert(0, [None for _ in range(COLS)])
        self.shake = 4.0 + n * 2

    def update(self, dt):
        if self.game_over or self.paused:
            return

        if self.flash_timer > 0:
            self.flash_timer -= dt
        else:
            self.clear_flash = []

        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt * 20)

        p = self.current
        grounded = self.collides(p, p.x, p.y + 1, p.rot)

        if grounded:
            self.lock_timer += dt
            if self.lock_timer >= self.lock_delay:
                self.lock_piece()
        else:
            self.fall_time += dt
            if self.fall_time >= self.fall_speed:
                self.fall_time = 0.0
                p.y += 1
                self.lock_timer = 0.0


# ------------------------------------------------------------------
# AUDIO
# ------------------------------------------------------------------

def init_audio():
    try:
        pygame.mixer.init()
        if os.path.exists(MUSIC_PATH):
            pygame.mixer.music.load(MUSIC_PATH)
            pygame.mixer.music.set_volume(0.55)
            pygame.mixer.music.play(loops=-1)  # -1 = bucle infinito
            return True
        else:
            print(f"[AVISO] No se encontró el archivo de música en: {MUSIC_PATH}")
            return False
    except pygame.error as e:
        print(f"[AVISO] No se pudo inicializar el audio: {e}")
        return False


# ------------------------------------------------------------------
# RENDER
# ------------------------------------------------------------------

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.bg = make_vertical_gradient(WIN_W, WIN_H, BG_TOP, BG_BOTTOM)
        self.font_title = pygame.font.SysFont("arial", 40, bold=True)
        self.font_big = pygame.font.SysFont("consolas", 26, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 20, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 15)
        self.time = 0.0

    def board_rect(self):
        return pygame.Rect(BOARD_X, BOARD_Y, COLS * CELL, ROWS * CELL)

    def draw_background(self):
        self.screen.blit(self.bg, (0, 0))
        # líneas de "circuito" decorativas sutiles
        t = self.time
        for i in range(6):
            alpha = 18 + 10 * math.sin(t * 0.6 + i)
            color = (*NEON_PURPLE, max(0, int(alpha)))
            y = int((i / 6) * WIN_H + (t * 12) % WIN_H) % WIN_H
            s = pygame.Surface((WIN_W, 2), pygame.SRCALPHA)
            s.fill(color)
            self.screen.blit(s, (0, y))

    def draw_board_frame(self, shake_offset):
        rect = self.board_rect().move(*shake_offset)
        panel = rect.inflate(20, 20)
        pygame.draw.rect(self.screen, PANEL_BG, panel, border_radius=14)
        draw_glow_rect(self.screen, panel, NEON_CYAN, glow_radius=18, base_alpha=55)
        pygame.draw.rect(self.screen, NEON_CYAN, panel, width=2, border_radius=14)

        # fondo del tablero
        pygame.draw.rect(self.screen, (10, 12, 26), rect, border_radius=6)
        # rejilla
        for c in range(COLS + 1):
            x = rect.x + c * CELL
            pygame.draw.line(self.screen, GRID_LINE, (x, rect.y), (x, rect.y + ROWS * CELL))
        for r in range(ROWS + 1):
            y = rect.y + r * CELL
            pygame.draw.line(self.screen, GRID_LINE, (rect.x, y), (rect.x + COLS * CELL, y))
        return rect

    def draw_grid_cells(self, game, rect, shake_offset):
        flashing = set(game.clear_flash)
        flash_on = int(self.time * 20) % 2 == 0
        for r in range(ROWS):
            for c in range(COLS):
                color = game.grid[r][c]
                if color is None:
                    continue
                if r in flashing and flash_on:
                    color = (255, 255, 255)
                x = rect.x + c * CELL
                y = rect.y + r * CELL
                draw_neon_cell(self.screen, x, y, CELL - 2, color)

    def draw_ghost(self, game, rect):
        gy = game.ghost_y()
        p = game.current
        for cx, cy in p.cells():
            gy_cell = gy + (cy - p.y)
            if gy_cell < 0:
                continue
            x = rect.x + cx * CELL
            y = rect.y + gy_cell * CELL
            draw_neon_cell(self.screen, x, y, CELL - 2, PIECE_COLORS[p.kind], filled=False, alpha=140)

    def draw_current_piece(self, game, rect):
        p = game.current
        color = PIECE_COLORS[p.kind]
        for cx, cy in p.cells():
            if cy < 0:
                continue
            x = rect.x + cx * CELL
            y = rect.y + cy * CELL
            draw_neon_cell(self.screen, x, y, CELL - 2, color)

    def draw_mini_piece(self, kind, center_x, center_y, scale=22):
        shape = SHAPES[kind][0]
        cells = [(c, r) for r, row in enumerate(shape) for c, ch in enumerate(row) if ch != "."]
        if not cells:
            return
        min_x = min(c for c, r in cells)
        max_x = max(c for c, r in cells)
        min_y = min(r for c, r in cells)
        max_y = max(r for c, r in cells)
        w = (max_x - min_x + 1) * scale
        h = (max_y - min_y + 1) * scale
        ox = center_x - w / 2
        oy = center_y - h / 2
        for c, r in cells:
            x = ox + (c - min_x) * scale
            y = oy + (r - min_y) * scale
            draw_neon_cell(self.screen, int(x), int(y), scale - 3, PIECE_COLORS[kind])

    def draw_panel(self, game, panel_rect, muted):
        pygame.draw.rect(self.screen, PANEL_BG, panel_rect, border_radius=14)
        draw_glow_rect(self.screen, panel_rect, NEON_MAGENTA, glow_radius=16, base_alpha=45)
        pygame.draw.rect(self.screen, NEON_MAGENTA, panel_rect, width=2, border_radius=14)

        pad = 20
        x = panel_rect.x + pad
        y = panel_rect.y + pad

        draw_text_glow(self.screen, self.font_title, "TETRIS", NEON_CYAN, (x, y), glow_color=NEON_CYAN)
        y += 50

        pulse = (math.sin(self.time * 3) + 1) / 2
        sub_color = lerp_color(NEON_PURPLE, NEON_MAGENTA, pulse)
        draw_text_glow(self.screen, self.font_small, "· F U T U R I S T A ·", sub_color, (x, y))
        y += 40

        # SCORE
        self._section_label(x, y, "PUNTAJE")
        draw_text_glow(self.screen, self.font_big, f"{game.score:,}", TEXT_MAIN, (x, y + 22))
        y += 70

        # LEVEL / LINES
        self._section_label(x, y, "NIVEL")
        draw_text_glow(self.screen, self.font_big, str(game.level), NEON_CYAN, (x, y + 22))
        self._section_label(x + 120, y, "LÍNEAS")
        draw_text_glow(self.screen, self.font_big, str(game.lines), NEON_CYAN, (x + 120, y + 22))
        y += 70

        # HOLD
        self._section_label(x, y, "GUARDAR (C)")
        hold_box = pygame.Rect(x, y + 20, 100, 70)
        pygame.draw.rect(self.screen, (10, 12, 26), hold_box, border_radius=8)
        pygame.draw.rect(self.screen, NEON_BLUE, hold_box, width=2, border_radius=8)
        if game.hold_kind:
            self.draw_mini_piece(game.hold_kind, hold_box.centerx, hold_box.centery)
        y += 100

        # NEXT
        self._section_label(x, y, "SIGUIENTES")
        y += 20
        next_list = game.next_pieces(3)
        for i, kind in enumerate(next_list):
            box = pygame.Rect(x, y + i * 62, 100, 55)
            pygame.draw.rect(self.screen, (10, 12, 26), box, border_radius=8)
            pygame.draw.rect(self.screen, NEON_PURPLE, box, width=2, border_radius=8)
            self.draw_mini_piece(kind, box.centerx, box.centery, scale=18)
        y += len(next_list) * 62 + 20

        # controles / estado audio
        controls = [
            "\u2190 \u2192  Mover",
            "\u2191 / X  Rotar",
            "\u2193  Caída suave",
            "ESPACIO  Caída total",
            "C  Guardar pieza",
            "P  Pausa   M  Música",
        ]
        self._section_label(x, y, "CONTROLES")
        y += 22
        for line in controls:
            s = self.font_small.render(line, True, TEXT_DIM)
            self.screen.blit(s, (x, y))
            y += 20

        # icono de música
        y += 6
        music_color = NEON_CYAN if not muted else (90, 90, 100)
        state = "REPRODUCIENDO ♪ (loop)" if not muted else "SILENCIADO"
        draw_text_glow(self.screen, self.font_small, state, music_color, (x, y))

    def _section_label(self, x, y, text):
        s = self.font_small.render(text, True, TEXT_DIM)
        self.screen.blit(s, (x, y))

    def draw_overlay_message(self, title, subtitle, title_color=NEON_MAGENTA):
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((5, 5, 15, 190))
        self.screen.blit(overlay, (0, 0))
        draw_text_glow(
            self.screen, self.font_title, title, title_color,
            (WIN_W // 2, WIN_H // 2 - 20), center=True,
        )
        draw_text_glow(
            self.screen, self.font_med, subtitle, TEXT_MAIN,
            (WIN_W // 2, WIN_H // 2 + 30), center=True,
        )


# ------------------------------------------------------------------
# BUCLE PRINCIPAL
# ------------------------------------------------------------------

def main():
    pygame.init()
    audio_ok = init_audio()
    muted = not audio_ok

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("TETRIS FUTURISTA")
    clock = pygame.time.Clock()

    game = Tetris()
    renderer = Renderer(screen)

    das_dir = 0
    das_timer = 0.0
    DAS_DELAY = 0.15
    DAS_SPEED = 0.03

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        renderer.time += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFT:
                    game.move(-1)
                    das_dir = -1
                    das_timer = -DAS_DELAY
                elif event.key == pygame.K_RIGHT:
                    game.move(1)
                    das_dir = 1
                    das_timer = -DAS_DELAY
                elif event.key in (pygame.K_UP, pygame.K_x):
                    game.rotate(1)
                elif event.key == pygame.K_z:
                    game.rotate(-1)
                elif event.key == pygame.K_DOWN:
                    game.soft_drop()
                elif event.key == pygame.K_SPACE:
                    game.hard_drop()
                elif event.key == pygame.K_c:
                    game.hold()
                elif event.key == pygame.K_p:
                    game.paused = not game.paused
                elif event.key == pygame.K_m:
                    muted = not muted
                    if audio_ok:
                        if muted:
                            pygame.mixer.music.set_volume(0.0)
                        else:
                            pygame.mixer.music.set_volume(0.55)
                elif event.key == pygame.K_r and game.game_over:
                    game.reset()
            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    if (event.key == pygame.K_LEFT and das_dir == -1) or (
                        event.key == pygame.K_RIGHT and das_dir == 1
                    ):
                        das_dir = 0

        # Auto-repeat de movimiento horizontal (DAS)
        if das_dir != 0 and not game.paused and not game.game_over:
            das_timer += dt
            while das_timer >= DAS_SPEED:
                game.move(das_dir)
                das_timer -= DAS_SPEED

        # Asegurar que la música siga sonando en bucle (red de seguridad)
        if audio_ok and not pygame.mixer.music.get_busy() and not muted:
            pygame.mixer.music.play(loops=-1)

        game.update(dt)

        # ---------------- RENDER ----------------
        renderer.draw_background()

        shake_offset = (0, 0)
        if game.shake > 0:
            shake_offset = (
                random.randint(-int(game.shake), int(game.shake)),
                random.randint(-int(game.shake), int(game.shake)),
            )

        board_rect = renderer.draw_board_frame(shake_offset)
        renderer.draw_grid_cells(game, board_rect, shake_offset)
        if not game.game_over and not game.paused:
            renderer.draw_ghost(game, board_rect)
            renderer.draw_current_piece(game, board_rect)

        panel_rect = pygame.Rect(
            BOARD_X * 2 + COLS * CELL, BOARD_Y - 10, SIDE_PANEL_W - 30, ROWS * CELL + 20
        )
        renderer.draw_panel(game, panel_rect, muted)

        if game.paused:
            renderer.draw_overlay_message("PAUSA", "Presiona P para continuar", NEON_BLUE)
        if game.game_over:
            renderer.draw_overlay_message(
                "GAME OVER", f"Puntaje: {game.score}   —   Presiona R para reiniciar", NEON_MAGENTA
            )

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()