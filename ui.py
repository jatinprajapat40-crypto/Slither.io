"""
ui.py – AAA-Style UI Manager for SLITHER ROYALE
================================================
Full premium visual overhaul:

  • Glassmorphic panels with multi-layer blur simulation
  • Animated gradient buttons with ripple press effect
  • Neon glow hotbar with arc-progress cooldown rings
  • Cinematic game-over / victory screen
  • Animated leaderboard with rank-change slide
  • Circular radar minimap with sweep + blip trails
  • Animated starfield + nebula background on menus
  • Skin customizer with live snake preview card
"""

from __future__ import annotations

import math
import random
import time as _time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import pygame

if TYPE_CHECKING:
    from skins import SkinManager

# ──────────────────────────────────────────────────────────────────────────────
# Colour helpers
# ──────────────────────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * _clamp(t, 0.0, 1.0)

def _lerp_c(c1, c2, t: float):
    t = _clamp(t, 0.0, 1.0)
    return (int(c1[0]+(c2[0]-c1[0])*t),
            int(c1[1]+(c2[1]-c1[1])*t),
            int(c1[2]+(c2[2]-c1[2])*t))

def _pulse(t: float, speed: float = 1.0) -> float:
    return (math.sin(t * speed * math.tau) + 1.0) * 0.5

def _ease_out_cubic(t: float) -> float:
    return 1 - (1 - _clamp(t, 0, 1)) ** 3

def _ease_out_back(t: float, s: float = 1.70158) -> float:
    t = _clamp(t, 0, 1)
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2

# ──────────────────────────────────────────────────────────────────────────────
# Surface helpers
# ──────────────────────────────────────────────────────────────────────────────

def _aa_circle(surface: pygame.Surface, colour, cx: int, cy: int, r: int):
    """Anti-aliased filled circle via gfxdraw if available, else fallback."""
    try:
        import pygame.gfxdraw as gfx
        gfx.aacircle(surface, cx, cy, r, colour)
        gfx.filled_circle(surface, cx, cy, r, colour)
    except Exception:
        pygame.draw.circle(surface, colour[:3], (cx, cy), r)


def _draw_text_aa(surface, text, x, y, font, colour,
                  center=False, shadow=True, shadow_col=(0, 0, 0),
                  shadow_off=2) -> pygame.Rect:
    surf = font.render(str(text), True, colour[:3])
    rect = surf.get_rect(center=(x, y)) if center else surf.get_rect(topleft=(x, y))
    if shadow:
        ss = font.render(str(text), True, shadow_col)
        sr = ss.get_rect(topleft=(rect.x + shadow_off, rect.y + shadow_off))
        surface.blit(ss, sr)
    surface.blit(surf, rect)
    return rect


def _glass_panel(surface, rect: pygame.Rect,
                 bg=(15, 20, 40), bg_alpha=170,
                 border=(80, 140, 255), border_alpha=200,
                 border_w=1, radius=14, highlight=True,
                 inner_glow=False, inner_glow_col=(80, 140, 255)):
    """Multi-layer glassmorphic panel."""
    w, h = rect.width, rect.height

    # ── drop shadow
    if w > 0 and h > 0:
        shadow_surf = pygame.Surface((w + 20, h + 20), pygame.SRCALPHA)
        for spread in range(10, 0, -2):
            a = int(18 * spread / 10)
            pygame.draw.rect(shadow_surf, (0, 0, 0, a),
                             (10 - spread, 10 - spread, w + spread*2, h + spread*2),
                             border_radius=radius + spread)
        surface.blit(shadow_surf, (rect.x - 10, rect.y - 10))

        # ── background
        bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (*bg, bg_alpha), (0, 0, w, h), border_radius=radius)
        surface.blit(bg_surf, rect.topleft)

        # ── top highlight stripe (glass sheen)
        if highlight and h > 20:
            hl_h = max(2, h // 5)
            hl_surf = pygame.Surface((w - 4, hl_h), pygame.SRCALPHA)
            for row in range(hl_h):
                a = int(45 * (1.0 - row / hl_h) ** 2)
                hl_surf.fill((255, 255, 255, a), rect=(0, row, w - 4, 1))
            surface.blit(hl_surf, (rect.x + 2, rect.y + 2))

        # ── inner glow edge
        if inner_glow:
            ig_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(ig_surf, (*inner_glow_col, 35), (0, 0, w, h),
                             width=12, border_radius=radius)
            surface.blit(ig_surf, rect.topleft)

        # ── border
        border_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*border, border_alpha), (0, 0, w, h),
                         width=border_w, border_radius=radius)
        surface.blit(border_surf, rect.topleft)


def _draw_arc_progress(surface, cx, cy, r, pct, colour,
                       bg_col=(40, 45, 65), width=4, start_angle=-math.pi/2):
    """Draw a circular progress ring (cooldown indicator)."""
    if r < 4:
        return
    # background ring
    rect = pygame.Rect(cx - r, cy - r, r*2, r*2)
    pygame.draw.arc(surface, bg_col, rect, 0, math.tau, width)
    # filled arc
    if pct > 0.01:
        end = start_angle + math.tau * pct
        pygame.draw.arc(surface, colour, rect, start_angle, end, width)


def _radial_gradient_surf(radius: int, colour, alpha_centre=180) -> pygame.Surface:
    d = radius * 2
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        a = int(alpha_centre * (r / radius) ** 1.6)
        pygame.draw.circle(s, (*colour[:3], a), (radius, radius), r)
    return s


# ──────────────────────────────────────────────────────────────────────────────
# Ripple effect (button press feedback)
# ──────────────────────────────────────────────────────────────────────────────

class _Ripple:
    def __init__(self, x: int, y: int, colour=(255, 255, 255)):
        self.x = x; self.y = y
        self.colour = colour
        self.t = 0.0
        self.duration = 0.45
        self.active = True

    def update(self, dt: float):
        self.t += dt
        if self.t >= self.duration:
            self.active = False

    def draw(self, surface: pygame.Surface, clip_rect: pygame.Rect):
        if not self.active:
            return
        prog  = self.t / self.duration
        r     = int(max(clip_rect.width, clip_rect.height) * prog * 0.9)
        alpha = int(120 * (1.0 - prog) ** 1.5)
        s     = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.colour[:3], alpha), (r+1, r+1), r)
        # clip to button bounds
        old = surface.get_clip()
        surface.set_clip(clip_rect)
        surface.blit(s, (self.x - r - 1, self.y - r - 1))
        surface.set_clip(old)


# ──────────────────────────────────────────────────────────────────────────────
# Premium Button
# ──────────────────────────────────────────────────────────────────────────────

class _Button:
    def __init__(self, rect: pygame.Rect, label: str,
                 base_col=(20, 60, 160), hover_col=(60, 120, 255),
                 accent_col=(120, 200, 255), icon: str = "",
                 font: Optional[pygame.font.Font] = None,
                 radius: int = 14):
        self.rect       = rect
        self.label      = label
        self.base_col   = base_col
        self.hover_col  = hover_col
        self.accent_col = accent_col
        self.icon       = icon
        self.font       = font
        self.radius     = radius
        self._hover_t   = 0.0
        self._press_t   = 0.0
        self._ripples: List[_Ripple] = []
        self.hovered    = False
        self.clicked    = False

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._ripples.append(_Ripple(event.pos[0], event.pos[1],
                                             self.accent_col))
                self._press_t = 1.0
                self.clicked  = True

    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        self.clicked  = False
        self.hovered  = self.rect.collidepoint(mouse_pos)
        target        = 1.0 if self.hovered else 0.0
        self._hover_t = _lerp(self._hover_t, target, min(1.0, dt * 12))
        self._press_t = max(0.0, self._press_t - dt * 3.5)
        for r in self._ripples:
            r.update(dt)
        self._ripples = [r for r in self._ripples if r.active]

    def draw(self, surface: pygame.Surface, t: float):
        rect   = self.rect
        h_t    = self._hover_t
        p_t    = self._press_t

        # gradient colours
        col_top = _lerp_c(self.base_col, self.hover_col, h_t)
        col_bot = _lerp_c(
            tuple(max(0, c-30) for c in self.base_col),
            tuple(max(0, c-20) for c in self.hover_col), h_t)

        # hover glow behind
        if h_t > 0.02:
            ge = int(h_t * 18)
            gr = rect.inflate(ge*2, ge*2)
            gs = pygame.Surface((gr.width, gr.height), pygame.SRCALPHA)
            ga = int(50 * h_t)
            pygame.draw.rect(gs, (*self.hover_col, ga), gs.get_rect(),
                             border_radius=self.radius + ge)
            surface.blit(gs, gr.topleft)

        # vertical gradient fill (simulated with two rects)
        _glass_panel(surface, rect, bg=col_top, bg_alpha=int(210 + h_t*40),
                     border=self.accent_col,
                     border_alpha=int(140 + h_t * 115),
                     border_w=max(1, int(1 + h_t * 1.5)),
                     radius=self.radius,
                     inner_glow=h_t > 0.1,
                     inner_glow_col=self.accent_col)

        # bottom darker strip (gradient illusion)
        bot_h = rect.height // 3
        bs    = pygame.Surface((rect.width - 4, bot_h), pygame.SRCALPHA)
        pygame.draw.rect(bs, (*col_bot, 60), (0, 0, rect.width-4, bot_h),
                         border_radius=self.radius)
        surface.blit(bs, (rect.x+2, rect.y + rect.height - bot_h))

        # press squish scale
        scale_y = 1.0 - p_t * 0.04
        draw_r  = rect.inflate(0, int(-rect.height * (1-scale_y)))

        # ripples
        for rp in self._ripples:
            rp.draw(surface, rect)

        # label
        if self.font:
            full_label = f"{self.icon}  {self.label}" if self.icon else self.label
            lc = _lerp_c((200, 210, 230), (255, 255, 255), h_t)
            _draw_text_aa(surface, full_label,
                          draw_r.centerx, draw_r.centery,
                          self.font, lc, center=True,
                          shadow=True, shadow_off=int(1 + h_t*1.5))

        # shine streak across top on hover
        if h_t > 0.05:
            shine_x = rect.x + int(h_t * rect.width * 1.2) - int(rect.width*0.2)
            sw      = max(4, int(rect.width * 0.25))
            ss      = pygame.Surface((sw, rect.height), pygame.SRCALPHA)
            for sx in range(sw):
                a = int(30 * h_t * math.sin(math.pi * sx / sw))
                ss.fill((255, 255, 255, a), rect=(sx, 0, 1, rect.height))
            old = surface.get_clip()
            surface.set_clip(rect)
            surface.blit(ss, (shine_x, rect.y))
            surface.set_clip(old)


# ──────────────────────────────────────────────────────────────────────────────
# Starfield + Nebula background
# ──────────────────────────────────────────────────────────────────────────────

class _Starfield:
    def __init__(self, sw: int, sh: int, count: int = 260):
        self._w = sw; self._h = sh
        self._stars = [self._make() for _ in range(count)]

    def _make(self) -> dict:
        layer = random.randint(0, 2)
        return {
            'x': random.uniform(0, self._w),
            'y': random.uniform(0, self._h),
            'speed': (5, 14, 28)[layer] + random.uniform(-2, 2),
            'size':  (1, 1, 2)[layer],
            'alpha': (70, 140, 220)[layer],
            'phase': random.uniform(0, math.tau),
            'col':   random.choice([(200,220,255),(255,240,200),(180,200,255),(255,200,240)]),
        }

    def update(self, dt: float):
        for s in self._stars:
            s['y'] -= s['speed'] * dt
            if s['y'] < -2:
                s['y'] = self._h + 2
                s['x'] = random.uniform(0, self._w)

    def draw(self, surface: pygame.Surface, t: float):
        for s in self._stars:
            flicker = (math.sin(t * 2.5 + s['phase']) + 1) * 0.5
            a  = int(s['alpha'] * (0.65 + flicker * 0.35))
            sz = s['size']
            ss = pygame.Surface((sz*2+1, sz*2+1), pygame.SRCALPHA)
            pygame.draw.circle(ss, (*s['col'], a), (sz, sz), sz)
            surface.blit(ss, (int(s['x'])-sz, int(s['y'])-sz),
                         special_flags=pygame.BLEND_ALPHA_SDL2)


class _NebulaBg:
    def __init__(self, sw: int, sh: int):
        self._surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for cx, cy, r, col in [
            (sw*0.12, sh*0.22, 280, (60,15,130,22)),
            (sw*0.82, sh*0.15, 220, (15,55,150,18)),
            (sw*0.50, sh*0.72, 320, (80,15,80,16)),
            (sw*0.90, sh*0.78, 200, (10,90,80,14)),
            (sw*0.35, sh*0.45, 160, (40,20,100,12)),
        ]:
            for ring in range(int(r), 0, -5):
                a = int(col[3] * (ring/r)**2.2)
                pygame.draw.circle(self._surf, (*col[:3], a), (int(cx),int(cy)), ring)

    def draw(self, surface: pygame.Surface):
        surface.blit(self._surf, (0,0), special_flags=pygame.BLEND_ALPHA_SDL2)


# ──────────────────────────────────────────────────────────────────────────────
# Circular Minimap
# ──────────────────────────────────────────────────────────────────────────────

class _CircularMinimap:
    RADIUS = 82
    MARGIN = 16

    def __init__(self, sw: int, sh: int):
        self._sw = sw; self._sh = sh
        self._cx = sw - self.RADIUS - self.MARGIN
        self._cy = sh - self.RADIUS - self.MARGIN
        self._sweep = 0.0
        self._blip_trails: Dict[int, List[Tuple[int,int]]] = {}

    def update(self, dt: float):
        self._sweep = (self._sweep + 1.1 * dt) % math.tau

    def draw(self, surface, snakes, player, zone_center, zone_radius, world_size, t):
        cr   = self.RADIUS
        cx   = self._cx; cy = self._cy
        half = world_size / 2
        sc   = cr / half

        mm = pygame.Surface((cr*2, cr*2), pygame.SRCALPHA)

        # Background
        pygame.draw.circle(mm, (6, 10, 20, 230), (cr, cr), cr)

        # Concentric grid rings
        for frac in (0.25, 0.50, 0.75, 1.0):
            pygame.draw.circle(mm, (28, 38, 58, 110), (cr, cr), int(cr*frac), 1)

        # Cross hairs
        pygame.draw.line(mm, (28, 38, 58, 90), (cr, 0), (cr, cr*2), 1)
        pygame.draw.line(mm, (28, 38, 58, 90), (0, cr), (cr*2, cr), 1)

        # Zone ring
        zr_mm = int(zone_radius * sc)
        if zr_mm > 1:
            zx = int((zone_center[0]+half)*sc)
            zy = int((zone_center[1]+half)*sc)
            pa = int(50 + _pulse(t, 2.0)*50)
            pygame.draw.circle(mm, (255, 50, 50, pa), (zx, zy), max(1, zr_mm), 2)

        # Radar sweep fan
        fan = pygame.Surface((cr*2, cr*2), pygame.SRCALPHA)
        fan_span = math.tau / 10
        steps    = 32
        for step in range(steps, 0, -1):
            frac  = step / steps
            angle = self._sweep - fan_span * (1.0 - frac)
            ex    = cr + int(math.cos(angle) * cr)
            ey    = cr + int(math.sin(angle) * cr)
            pygame.draw.line(fan, (0, 230, 110, int(60*frac)), (cr, cr), (ex, ey), 1)
        mm.blit(fan, (0,0), special_flags=pygame.BLEND_ALPHA_SDL2)

        # Bot blips
        for snake in snakes:
            if not snake.alive:
                continue
            bx = int(_clamp((snake.x+half)*sc, 2, cr*2-2))
            by = int(_clamp((snake.y+half)*sc, 2, cr*2-2))
            if player and snake.id == player.id:
                continue
            br = max(1, min(3, snake.length//14+1))
            bs = pygame.Surface((br*2+2, br*2+2), pygame.SRCALPHA)
            pygame.draw.circle(bs, (*snake.color1[:3], 190), (br+1,br+1), br)
            mm.blit(bs, (bx-br-1, by-br-1), special_flags=pygame.BLEND_ALPHA_SDL2)

        # Player blip
        if player and player.alive:
            pmm_x = int(_clamp((player.x+half)*sc, 3, cr*2-3))
            pmm_y = int(_clamp((player.y+half)*sc, 3, cr*2-3))
            pp    = 4 + int(_pulse(t, 2.0)*2)
            gs    = _radial_gradient_surf(pp*2+2, (0,220,255), 90)
            mm.blit(gs, (pmm_x-pp-1, pmm_y-pp-1), special_flags=pygame.BLEND_ALPHA_SDL2)
            pygame.draw.circle(mm, (0, 240, 255), (pmm_x, pmm_y), pp)
            pygame.draw.circle(mm, (255, 255, 255), (pmm_x, pmm_y), max(1,pp//2))

        # Clip to circle
        clip = pygame.Surface((cr*2, cr*2), pygame.SRCALPHA)
        pygame.draw.circle(clip, (255,255,255,255), (cr,cr), cr)
        mm.blit(clip, (0,0), special_flags=pygame.BLEND_RGBA_MIN)

        # Border glow
        og = pygame.Surface((cr*2+16, cr*2+16), pygame.SRCALPHA)
        pygame.draw.circle(og, (40,100,220,55), (cr+8,cr+8), cr+6, 8)
        surface.blit(og, (cx-cr-8, cy-cr-8), special_flags=pygame.BLEND_ALPHA_SDL2)

        # Border ring
        pygame.draw.circle(mm, (70,130,220,255), (cr,cr), cr, 2)

        surface.blit(mm, (cx-cr, cy-cr))


# ──────────────────────────────────────────────────────────────────────────────
# Leaderboard panel
# ──────────────────────────────────────────────────────────────────────────────

class _LeaderboardPanel:
    W = 215; MARGIN = 14

    def __init__(self, sw, sh):
        self._sw = sw; self._sh = sh
        self._alphas = [0.0]*10
        self._offsets= [30.0]*10   # slide-in x offset

    def update(self, dt, top_snakes):
        for i in range(10):
            ta = 1.0 if i < len(top_snakes) else 0.0
            self._alphas[i]  = _lerp(self._alphas[i],  ta,   min(1.0, dt*7))
            self._offsets[i] = _lerp(self._offsets[i], 0.0,  min(1.0, dt*10))

    def draw(self, surface, top_snakes, player, fonts, t):
        tiny  = fonts.get('tiny')
        small = fonts.get('small')
        if not tiny or not small:
            return

        row_h   = 23
        header  = 32
        pad     = 10
        n       = min(10, len(top_snakes))
        panel_h = header + n * row_h + pad * 2

        px = self._sw - self.W - self.MARGIN
        py = self.MARGIN + 52

        rect = pygame.Rect(px, py, self.W, panel_h)
        _glass_panel(surface, rect, bg=(10,16,32), bg_alpha=182,
                     border=(80,140,255), border_alpha=185,
                     radius=13, inner_glow=True, inner_glow_col=(60,120,255))

        # Header
        _draw_text_aa(surface, "⬆  LEADERBOARD",
                      px + self.W//2, py+15, small, (180,200,255), center=True)

        # Separator
        sep_y = py + header - 4
        pygame.draw.line(surface, (60, 100, 200, 120),
                         (px+8, sep_y), (px+self.W-8, sep_y), 1)

        rank_cols = [(255,200,40),(210,210,210),(200,120,40)]

        for i, snake in enumerate(top_snakes[:n]):
            a = self._alphas[i]
            if a < 0.02:
                continue
            off   = self._offsets[i]
            row_y = py + header + pad + i*row_h
            score = snake.score + snake.length * 10
            is_p  = player and snake.id == player.id

            # Player row highlight
            if is_p:
                hl = pygame.Surface((self.W-6, row_h-2), pygame.SRCALPHA)
                hl.fill((0,200,255, int(28*a)))
                surface.blit(hl, (px+3, row_y))

            es = pygame.Surface((self.W-6, row_h), pygame.SRCALPHA)
            es.set_alpha(int(255*a))

            rc  = rank_cols[i] if i < 3 else (155,155,175)
            nc  = (0,220,255) if is_p else (215,220,235)
            if is_p: rc = (0,220,255)

            rs = tiny.render(f"{i+1}.", True, rc)
            es.blit(rs, (4 + int(off), 4))

            ns = tiny.render(snake.name[:14], True, nc)
            es.blit(ns, (28 + int(off), 4))

            scs= tiny.render(str(score), True, rc)
            es.blit(scs, (self.W-6-scs.get_width()-4, 4))

            surface.blit(es, (px+3, row_y))

        # Player footer if outside top-10
        if player:
            rank = next((i+1 for i,s in enumerate(top_snakes) if s.id==player.id), None)
            if rank and rank > 10:
                fy = py + panel_h - 20
                fs = pygame.Surface((self.W-6, 18), pygame.SRCALPHA)
                fs.fill((0,200,255,22))
                surface.blit(fs, (px+3, fy))
                txt = f"You: #{rank}  ({player.score+player.length*10})"
                _draw_text_aa(surface, txt, px+self.W//2, fy+9,
                              tiny, (0,220,255), center=True, shadow=False)


# ──────────────────────────────────────────────────────────────────────────────
# Score / stats panel
# ──────────────────────────────────────────────────────────────────────────────

class _ScorePanel:
    W = 185; PAD = 12

    def draw(self, surface, player, fonts, t):
        if player is None:
            return
        small = fonts.get('small')
        tiny  = fonts.get('tiny')
        if not small or not tiny:
            return

        h = 158
        rect = pygame.Rect(self.PAD, self.PAD, self.W, h)
        _glass_panel(surface, rect, bg=(8,13,28), bg_alpha=175,
                     border=(0,180,255), border_alpha=165,
                     radius=14, inner_glow=True, inner_glow_col=(0,140,255))

        x0 = rect.x + 11
        y  = rect.y + 11

        # Score with gold shimmer
        sc  = _lerp_c((220,200,60),(255,230,80), _pulse(t, 0.7))
        _draw_text_aa(surface, f"SCORE  {player.score}", x0, y, small, sc)
        y += 23

        # Kills / Length
        _draw_text_aa(surface, f"Kills: {player.kills}", x0,    y, tiny, (255,100,100))
        _draw_text_aa(surface, f"Len: {player.length}",  x0+88, y, tiny, (100,255,140))
        y += 19

        # Level
        lvc = _lerp_c((140,80,255),(210,160,255), _pulse(t, 0.8))
        _draw_text_aa(surface, f"Level {player.level}", x0, y, tiny, lvc)
        y += 17

        y = self._bar(surface, x0, y, self.W-20,
                      player.xp, player.xp_to_next, (140,80,255),(60,30,130),"XP", tiny, t)
        y = self._bar(surface, x0, y, self.W-20,
                      player.energy, player.max_energy,
                      (255,200,40),(140,90,10),"EN", tiny, t)
        hp_c = _lerp_c((220,40,40),(40,220,80), player.health/max(1,player.max_health))
        self._bar(surface, x0, y, self.W-20,
                  player.health, player.max_health, hp_c,(60,15,15),"HP", tiny, t)

    def _bar(self, surface, x, y, w, val, mx, col, bg, label, font, t):
        bh  = 9
        pct = _clamp(val/max(1,mx), 0, 1)
        ls  = font.render(label, True, (150,155,175))
        surface.blit(ls, (x, y))
        bx  = x + ls.get_width() + 5
        bw  = w - ls.get_width() - 5
        tr  = pygame.Rect(bx, y+1, bw, bh)

        # trough
        ts = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(ts, (*bg, 190), (0,0,bw,bh), border_radius=5)
        surface.blit(ts, tr.topleft)

        # fill gradient
        fw = max(0, int(bw * pct))
        if fw > 0:
            fs = pygame.Surface((fw, bh), pygame.SRCALPHA)
            for px_i in range(fw):
                shade = _lerp_c(col, _lerp_c(col,(255,255,255),0.35), px_i/max(1,fw))
                pygame.draw.line(fs, (*shade,235),(px_i,0),(px_i,bh-1))
            surface.blit(fs, tr.topleft)

        # border
        pygame.draw.rect(surface, (*col,180), tr, 1, border_radius=5)
        return y + bh + 7


# ──────────────────────────────────────────────────────────────────────────────
# HOTBAR  (the big upgrade — neon arc-ring ability slots)
# ──────────────────────────────────────────────────────────────────────────────

_ABILITY_META = [
    # (AbilityType-name, display, key, base_col, glow_col)
    ("DASH",         "Dash",   "Q", (255,200,30),  (255,240,100)),
    ("SHIELD",       "Shield", "E", (30, 200,255),  (120,230,255)),
    ("GHOST",        "Ghost",  "R", (190,190,210),  (230,230,255)),
    ("MAGNET",       "Magnet", "F", (170, 50,255),  (220,130,255)),
    ("TELEPORT",     "Tele",   "T", (50, 110,255),  (120,170,255)),
    ("FREEZE_PULSE", "Freeze", "G", (80, 200,255),  (160,240,255)),
    ("POISON_TRAIL", "Poison", "V", (30, 210, 80),  (100,255,140)),
]

class _HotBar:
    SLOT_W   = 60
    SLOT_H   = 60
    GAP      = 10
    RING_W   = 4
    PANEL_PH = 10   # extra padding around slots

    def __init__(self, sw: int, sh: int):
        self._sw = sw; self._sh = sh
        n = len(_ABILITY_META)
        total_w = n * self.SLOT_W + (n-1) * self.GAP
        self._start_x = sw//2 - total_w//2
        self._bar_y   = sh - self.SLOT_H - 18
        self._glow_ts = [0.0] * n   # per-slot active glow timer
        self._prev_active = [False] * n

    def update(self, dt: float, player):
        if player is None:
            return
        for i, (aname, *_) in enumerate(_ABILITY_META):
            try:
                from __main__ import AbilityType
                atype = AbilityType[aname]
                ab    = player.abilities.get(atype)
                active = ab.active if ab else False
            except Exception:
                active = False
            if active and not self._prev_active[i]:
                self._glow_ts[i] = 1.0
            self._glow_ts[i]  = max(0.0, self._glow_ts[i] - dt * 1.5)
            self._prev_active[i] = active

    def draw(self, surface: pygame.Surface, player, fonts: dict, t: float):
        if player is None:
            return
        tiny = fonts.get('tiny')
        if not tiny:
            return

        n      = len(_ABILITY_META)
        total_w= n * self.SLOT_W + (n-1) * self.GAP
        px     = self._start_x
        py     = self._bar_y

        # Panel background behind all slots
        panel_rect = pygame.Rect(px - self.PANEL_PH,
                                 py - self.PANEL_PH,
                                 total_w + self.PANEL_PH*2,
                                 self.SLOT_H + self.PANEL_PH*2)
        _glass_panel(surface, panel_rect,
                     bg=(8,12,26), bg_alpha=195,
                     border=(60,100,200), border_alpha=160,
                     radius=18, highlight=False,
                     inner_glow=True, inner_glow_col=(50,90,200))

        try:
            from __main__ import AbilityType as _AT
        except Exception:
            _AT = None

        for i, (aname, disp, key, col, glow_col) in enumerate(_ABILITY_META):
            sx = px + i * (self.SLOT_W + self.GAP)
            sy = py

            # Fetch ability state
            ab      = None
            ready   = True
            active  = False
            cd_pct  = 0.0
            if _AT:
                try:
                    atype  = _AT[aname]
                    ab     = player.abilities.get(atype)
                    if ab:
                        ready   = ab.cooldown <= 0
                        active  = ab.active
                        cd_pct  = _clamp(ab.cooldown / max(0.001, ab.max_cooldown), 0, 1)
                except Exception:
                    pass

            slot_rect = pygame.Rect(sx, sy, self.SLOT_W, self.SLOT_H)

            # ── outer active glow burst
            glow_t = self._glow_ts[i]
            if glow_t > 0:
                ge  = int(glow_t * 22)
                gs2 = pygame.Surface((self.SLOT_W+ge*2, self.SLOT_H+ge*2), pygame.SRCALPHA)
                ga  = int(100 * glow_t)
                pygame.draw.rect(gs2, (*glow_col, ga), gs2.get_rect(),
                                 border_radius=14+ge)
                surface.blit(gs2, (sx-ge, sy-ge))

            # ── slot background
            bg_col = (12,18,35) if ready else (28,10,10)
            border_col = col if ready else (70,70,80)
            _glass_panel(surface, slot_rect,
                         bg=bg_col, bg_alpha=215,
                         border=border_col, border_alpha=230,
                         border_w=2, radius=12, highlight=False)

            # ── cooldown arc ring (drawn on top of background)
            ring_r  = self.SLOT_W // 2 - 3
            ring_cx = sx + self.SLOT_W // 2
            ring_cy = sy + self.SLOT_H // 2

            if not ready and cd_pct > 0:
                # filled dark ring
                _draw_arc_progress(surface, ring_cx, ring_cy, ring_r,
                                   1.0, (30,35,55), width=self.RING_W)
                # remaining cooldown arc (red)
                _draw_arc_progress(surface, ring_cx, ring_cy, ring_r,
                                   cd_pct, (200,60,60), width=self.RING_W)
            else:
                # ready ring — glowing colour ring
                pct_pulse = 1.0 if not active else (0.6 + _pulse(t,4)*0.4)
                ring_col  = _lerp_c(col, glow_col, _pulse(t, 1.5) if active else 0)
                ring_a    = int(180 * pct_pulse)
                pygame.draw.circle(surface, (*ring_col, ring_a),
                                   (ring_cx, ring_cy), ring_r, self.RING_W)

            # ── active shimmer overlay
            if active:
                ac_a = int(40 + _pulse(t,4)*50)
                ac_s = pygame.Surface((self.SLOT_W-4, self.SLOT_H-4), pygame.SRCALPHA)
                pygame.draw.rect(ac_s, (*glow_col, ac_a), ac_s.get_rect(), border_radius=10)
                surface.blit(ac_s, (sx+2, sy+2))

            # ── Key label (top)
            kc  = col if ready else (90,90,100)
            ks  = tiny.render(key, True, kc)
            surface.blit(ks, (sx + self.SLOT_W//2 - ks.get_width()//2, sy+6))

            # ── Ability name (middle)
            nc  = (210,215,225) if ready else (110,110,120)
            ns  = tiny.render(disp, True, nc)
            surface.blit(ns, (sx + self.SLOT_W//2 - ns.get_width()//2, sy+26))

            # ── Cooldown number (bottom) or READY tick
            if not ready and ab:
                cd_s = tiny.render(f"{ab.cooldown:.1f}", True, (255,80,80))
                surface.blit(cd_s, (sx + self.SLOT_W//2 - cd_s.get_width()//2, sy+43))
            elif ready:
                rt   = tiny.render("●", True, (*col, 200))
                surface.blit(rt, (sx + self.SLOT_W//2 - rt.get_width()//2, sy+44))


# ──────────────────────────────────────────────────────────────────────────────
# Active effects pill bar
# ──────────────────────────────────────────────────────────────────────────────

def _draw_active_effects(surface, player, fonts, sw, sh, t):
    small = fonts.get('small')
    if not small or player is None:
        return
    effects = []
    if player.shield_active:       effects.append(("⬡ SHIELD",   (40,200,255), player.shield_timer))
    if player.ghost_active:        effects.append(("◈ GHOST",    (200,200,210), player.ghost_timer))
    if player.magnet_active:       effects.append(("⊛ MAGNET",   (180,60,255), player.magnet_timer))
    if player.speed_boost_timer>0: effects.append(("≫ SPEED",    (255,215,40), player.speed_boost_timer))
    if player.score_multiplier>1:  effects.append(("★ x2 SCORE", (255,200,40), player.score_mult_timer))
    if not effects:
        return
    pill_h   = 28; gap = 6
    start_y  = sh - 88 - (pill_h+gap)*len(effects)
    for idx, (label, col, timer) in enumerate(effects):
        txt = f"{label}  {timer:.1f}s"
        ls  = small.render(txt, True, col[:3])
        pw  = ls.get_width() + 28
        prx = sw//2 - pw//2
        pry = start_y + idx*(pill_h+gap)
        pr  = pygame.Rect(prx, pry, pw, pill_h)
        _glass_panel(surface, pr, bg=(12,18,38), bg_alpha=195,
                     border=col, border_alpha=225,
                     border_w=1, radius=14, highlight=False,
                     inner_glow=timer<3.0, inner_glow_col=col)
        if timer < 3.0:
            pulse_a = int(55 * _pulse(t, 4.0))
            gs = pygame.Surface((pw+12, pill_h+12), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*col[:3], pulse_a), gs.get_rect(), border_radius=15)
            surface.blit(gs, (prx-6, pry-6))
        surface.blit(ls, (prx+14, pry+(pill_h-ls.get_height())//2))


# ──────────────────────────────────────────────────────────────────────────────
# Zone warning vignette
# ──────────────────────────────────────────────────────────────────────────────

def _draw_zone_warning(surface, t, fonts, warning, sw, sh):
    if not warning:
        return
    pv = _pulse(t, 3.0)
    vig= pygame.Surface((sw, sh), pygame.SRCALPHA)
    for ring in range(70, 0, -7):
        a = int(70 * pv * (ring/70))
        pygame.draw.rect(vig, (255,35,35,a),(0,0,sw,sh), width=ring)
    surface.blit(vig, (0,0))
    med = fonts.get('medium')
    if med:
        wc = _lerp_c((255,50,50),(255,200,40), pv)
        _draw_text_aa(surface, "⚠  SAFE ZONE SHRINKING  ⚠",
                      sw//2, 68, med, wc, center=True, shadow_off=3)


# ──────────────────────────────────────────────────────────────────────────────
# UIManager  (public API)
# ──────────────────────────────────────────────────────────────────────────────

class UIManager:
    """
    Central UI controller.

    draw_main_menu(events)                 → action str | None
    draw_skin_customizer(events, skin_id)  → (int, action | None)
    draw_hud(player, snakes, zone_center, zone_radius,
             match_timer, camera, world_size, zone_warning)
    draw_spectate_banner(name)
    draw_game_over(winner, player, events) → action | None
    draw_pause(events)                     → action | None
    update(dt)
    """

    _MENU_BTNS = [
        ("▶  PLAY",        'play',      (18,110,35),  (35,190,70),   (120,255,150), ""),
        ("🎮  GAME MODES", 'modes',     (18,55,155),  (55,115,255),  (130,180,255), ""),
        ("🛒  SHOP",       'shop',      (130,90,15),  (255,195,35),  (255,235,130), ""),
        ("🎨  CUSTOMIZE",  'customize', (75,15,135),  (155,55,255),  (210,130,255), ""),
        ("📊  STATS",      'stats',     (15,95,115),  (35,195,215),  (120,230,255), ""),
        ("✕  QUIT",        'quit',      (115,15,15),  (215,50,50),   (255,130,130), ""),
    ]

    def __init__(self, screen: pygame.Surface, fonts: dict, skin_mgr: 'SkinManager'):
        self._screen   = screen
        self._fonts    = fonts
        self._skin_mgr = skin_mgr
        self._sw       = screen.get_width()
        self._sh       = screen.get_height()
        self._t        = 0.0

        self._starfield= _Starfield(self._sw, self._sh)
        self._nebula   = _NebulaBg(self._sw, self._sh)
        self._lb       = _LeaderboardPanel(self._sw, self._sh)
        self._minimap  = _CircularMinimap(self._sw, self._sh)
        self._scorepnl = _ScorePanel()
        self._hotbar   = _HotBar(self._sw, self._sh)

        self._menu_btns: List[_Button] = self._build_menu_buttons()
        self._sel_skin  = 0

    # ── frame update ──────────────────────────────────────────────────────────
    def update(self, dt: float):
        self._t += dt
        self._starfield.update(dt)
        self._minimap.update(dt)

    # ── main menu ─────────────────────────────────────────────────────────────
    def _build_menu_buttons(self) -> List[_Button]:
        btns  = []
        bw, bh, gap = 268, 50, 12
        n = len(self._MENU_BTNS)
        sy= self._sh//2 - (n*(bh+gap))//2 + 55
        med = self._fonts.get('medium')
        for i,(label,action,base,hover,accent,icon) in enumerate(self._MENU_BTNS):
            r = pygame.Rect(self._sw//2-bw//2, sy+i*(bh+gap), bw, bh)
            btns.append(_Button(r, label, base, hover, accent, icon, med, radius=14))
        return btns

    def draw_main_menu(self, events: list) -> Optional[str]:
        screen = self._screen
        t      = self._t

        screen.fill((4,7,16))
        self._nebula.draw(screen)
        self._starfield.draw(screen, t)

        # Edge vignette
        vg = pygame.Surface((self._sw, self._sh), pygame.SRCALPHA)
        for rv in range(min(self._sw,self._sh)//2, 0, -12):
            a = int(55*(1-rv/(min(self._sw,self._sh)/2))**2)
            pygame.draw.rect(vg,(0,0,0,a),(0,0,self._sw,self._sh),
                             width=min(self._sw,self._sh)//2-rv)
        screen.blit(vg,(0,0))

        # Title
        title_font = self._fonts.get('title')
        large_font = self._fonts.get('large')
        small_font = self._fonts.get('small')
        tiny_font  = self._fonts.get('tiny')
        ty         = int(self._sh*0.13 + math.sin(t*1.3)*7)

        if title_font:
            gp  = _pulse(t, 0.55)
            gw  = 460
            gs  = pygame.Surface((gw, 80), pygame.SRCALPHA)
            ga  = int(40+gp*38)
            pygame.draw.ellipse(gs,(0,170,255,ga),gs.get_rect())
            screen.blit(gs,(self._sw//2-gw//2, ty-20),
                        special_flags=pygame.BLEND_ALPHA_SDL2)
            tc  = _lerp_c((0,140,210),(110,240,255),gp)
            ts  = title_font.render("SLITHER ROYALE", True, (0,0,0))
            screen.blit(ts,(self._sw//2-ts.get_width()//2+3, ty+3))
            ts2 = title_font.render("SLITHER ROYALE", True, tc)
            screen.blit(ts2,(self._sw//2-ts2.get_width()//2, ty))

        if large_font:
            sc  = _lerp_c((195,155,35),(255,225,75), _pulse(t,0.85))
            _draw_text_aa(screen,"AI SNAKE ARENA",
                          self._sw//2, ty+66, large_font, sc, center=True)

        if small_font:
            _draw_text_aa(screen,"60 AI Snakes · Battle Royale · Total Chaos",
                          self._sw//2, ty+104, small_font,(135,145,165),center=True)

        # Live snake strip
        self._skin_mgr.draw_preview_strip(
            screen, int(t*0.28)%5,
            start_x=self._sw//2+170, start_y=ty+128,
            seg_count=11, seg_radius=8, spacing=14, wave_amplitude=11)

        # Buttons
        mouse = pygame.mouse.get_pos()
        action= None
        for event in events:
            for btn in self._menu_btns:
                btn.handle_event(event)
        for i,btn in enumerate(self._menu_btns):
            btn.update(1/60, mouse)
            btn.draw(screen, t)
            if btn.clicked:
                action = self._MENU_BTNS[i][1]

        if tiny_font:
            _draw_text_aa(screen,
                          "Mouse to aim  ·  SPACE boost  ·  Q/E/R/F/T/G/V abilities",
                          self._sw//2, self._sh-20, tiny_font,(65,75,95),center=True)
        return action

    # ── skin customizer ───────────────────────────────────────────────────────
    def draw_skin_customizer(self, events: list, cur_skin: int):
        screen = self._screen
        t      = self._t
        self._sel_skin = cur_skin

        screen.fill((4,7,16))
        self._nebula.draw(screen)
        self._starfield.draw(screen, t)

        large  = self._fonts.get('large')
        medium = self._fonts.get('medium')
        small  = self._fonts.get('small')
        tiny   = self._fonts.get('tiny')

        if large:
            _draw_text_aa(screen,"🎨  CUSTOMIZE YOUR SNAKE",
                          self._sw//2, 46, large,(175,75,255),center=True)

        # Card
        cw, ch = 520, 270
        crect  = pygame.Rect(self._sw//2-cw//2, self._sh//2-ch//2-18, cw, ch)
        _glass_panel(screen, crect, bg=(14,9,34), bg_alpha=205,
                     border=(135,55,255), border_alpha=230,
                     radius=20, inner_glow=True, inner_glow_col=(110,40,255))

        # Skin name with colour
        skin_name= self._skin_mgr.SKIN_NAMES[self._sel_skin]
        name_cols= [(0,230,255),(255,145,18),(255,75,18),(155,75,255),(255,200,38)]
        if medium:
            _draw_text_aa(screen, skin_name, self._sw//2, crect.y+30,
                          medium, name_cols[self._sel_skin], center=True)

        # Live preview
        self._skin_mgr.draw_preview_strip(
            screen, self._sel_skin,
            start_x=crect.x+cw-55, start_y=crect.y+ch//2+12,
            seg_count=20, seg_radius=12, spacing=19,
            wave_amplitude=24, wave_speed=2.0)

        # Indicator dots
        dy  = crect.bottom - 24
        dg  = 24
        n   = self._skin_mgr.SKIN_COUNT
        dsx = self._sw//2 - (n*dg)//2
        for di in range(n):
            dx = dsx + di*dg
            if di == self._sel_skin:
                pygame.draw.circle(screen,(195,95,255),(dx,dy),7)
                pygame.draw.circle(screen,(255,255,255),(dx,dy),7,1)
            else:
                pygame.draw.circle(screen,(55,35,88),(dx,dy),4)
                pygame.draw.circle(screen,(115,75,175),(dx,dy),4,1)

        # Arrow buttons
        aw, ah = 56, 56
        ay     = crect.centery + 8
        lrect  = pygame.Rect(crect.x-aw-18, ay-ah//2, aw, ah)
        rrect  = pygame.Rect(crect.right+18, ay-ah//2, aw, ah)

        mouse  = pygame.mouse.get_pos()
        action = None
        clicked= False; click_pos = None
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True; click_pos = event.pos
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self._sel_skin=(self._sel_skin-1)%n
                elif event.key == pygame.K_RIGHT:
                    self._sel_skin=(self._sel_skin+1)%n

        for br, delta, lbl in [(lrect,-1,"◀"),(rrect,+1,"▶")]:
            hov = br.collidepoint(mouse)
            _glass_panel(screen, br,
                         bg=(75,25,135) if hov else (28,12,58),
                         bg_alpha=215,
                         border=(155,75,255), border_alpha=235,
                         radius=14, highlight=False)
            if medium:
                tc = (255,255,255) if hov else (175,115,255)
                _draw_text_aa(screen, lbl, br.centerx, br.centery,
                              medium, tc, center=True)
            if clicked and click_pos and br.collidepoint(click_pos):
                self._sel_skin=(self._sel_skin+delta)%n

        # Select button
        sr    = pygame.Rect(self._sw//2-105, crect.bottom+24, 210, 48)
        hov_s = sr.collidepoint(mouse)
        _glass_panel(screen, sr,
                     bg=(45,170,55) if hov_s else (18,75,28),
                     bg_alpha=225, border=(75,250,95), border_alpha=225,
                     radius=13, inner_glow=hov_s, inner_glow_col=(75,250,95))
        if medium:
            _draw_text_aa(screen,"✔  SELECT SKIN", sr.centerx, sr.centery,
                          medium,(255,255,255),center=True)
        if clicked and click_pos and sr.collidepoint(click_pos):
            action = 'select'

        # Back button
        backr  = pygame.Rect(20, self._sh-60, 115, 44)
        hov_b  = backr.collidepoint(mouse)
        _glass_panel(screen, backr,
                     bg=(95,18,18) if hov_b else (38,10,10),
                     bg_alpha=215, border=(215,55,55), border_alpha=205,
                     radius=11, highlight=False)
        if small:
            _draw_text_aa(screen,"◀ BACK", backr.centerx, backr.centery,
                          small,(255,195,195),center=True)
        if clicked and click_pos and backr.collidepoint(click_pos):
            action = 'back'

        if tiny:
            _draw_text_aa(screen,"← → arrow keys or click arrows to cycle skins",
                          self._sw//2, self._sh-20, tiny,(75,65,105),center=True)

        return self._sel_skin, action

    # ── in-game HUD ───────────────────────────────────────────────────────────
    def draw_hud(self, player, snakes, zone_center, zone_radius,
                 match_timer, camera, world_size, zone_warning=False):
        screen = self._screen
        t      = self._t

        # Score panel
        self._scorepnl.draw(screen, player, self._fonts, t)

        # Alive + timer top-centre
        alive = sum(1 for s in snakes if s.alive)
        total = len(snakes)
        mins  = int(match_timer//60); secs = int(match_timer%60)
        med   = self._fonts.get('medium')
        small = self._fonts.get('small')
        tiny  = self._fonts.get('tiny')

        if med:
            _draw_text_aa(screen, f"ALIVE  {alive} / {total}",
                          self._sw//2, 12, med,(215,220,240),center=True)
        if small:
            tc = _lerp_c((255,215,40),(255,95,35), _pulse(t,0.22))
            _draw_text_aa(screen, f"{mins:02d}:{secs:02d}",
                          self._sw//2, 38, small, tc, center=True)

        # Zone warning
        _draw_zone_warning(screen, t, self._fonts, zone_warning, self._sw, self._sh)

        # Leaderboard
        top = sorted([s for s in snakes if s.alive],
                     key=lambda s: s.score+s.length*10, reverse=True)
        self._lb.update(1/60, top)
        self._lb.draw(screen, top, player, self._fonts, t)

        # Minimap
        self._minimap.draw(screen, snakes, player,
                           zone_center, zone_radius, world_size, t)
        if tiny:
            _draw_text_aa(screen,"RADAR",
                          self._minimap._cx, self._minimap._cy-self._minimap.RADIUS-11,
                          tiny,(95,135,200),center=True,shadow=False)

        # Hotbar
        self._hotbar.update(1/60, player)
        self._hotbar.draw(screen, player, self._fonts, t)

        # Active effects
        _draw_active_effects(screen, player, self._fonts, self._sw, self._sh, t)

        # Coins chip
        if player and small:
            chip = pygame.Rect(10, 165, 118, 26)
            _glass_panel(screen, chip, bg=(55,42,8), bg_alpha=175,
                         border=(255,195,38), border_alpha=185,
                         border_w=1, radius=13, highlight=False)
            _draw_text_aa(screen, f"💰 {player.coins_collected}",
                          chip.centerx, chip.centery,
                          tiny or small,(255,215,55),center=True,shadow=False)

    # ── spectate banner ───────────────────────────────────────────────────────
    def draw_spectate_banner(self, target_name: str):
        med   = self._fonts.get('medium')
        small = self._fonts.get('small')
        r     = pygame.Rect(self._sw//2-225, 8, 450, 54)
        _glass_panel(self._screen, r, bg=(28,8,48), bg_alpha=205,
                     border=(175,55,255), border_alpha=225, radius=13)
        if med:
            _draw_text_aa(self._screen, f"👁  SPECTATING: {target_name}",
                          self._sw//2, 28, med,(215,175,255),center=True)
        if small:
            _draw_text_aa(self._screen,"← → switch   ·   ESC quit",
                          self._sw//2, 50, small,(135,115,175),center=True)

    # ── game over ─────────────────────────────────────────────────────────────
    def draw_game_over(self, winner, player, events: list) -> Optional[str]:
        screen = self._screen; t = self._t

        ov = pygame.Surface((self._sw, self._sh), pygame.SRCALPHA)
        ov.fill((0,0,0,175))
        screen.blit(ov,(0,0))

        won  = winner is not None and getattr(winner,'is_player',False)
        bord = (255,200,38) if won else (215,55,55)
        pw,ph= 530,400
        pr   = pygame.Rect(self._sw//2-pw//2, self._sh//2-ph//2, pw, ph)
        _glass_panel(screen, pr, bg=(10,14,30), bg_alpha=230,
                     border=bord, border_alpha=235,
                     radius=22, inner_glow=True, inner_glow_col=bord)

        tf   = self._fonts.get('title')
        lf   = self._fonts.get('large')
        mf   = self._fonts.get('medium')
        sf   = self._fonts.get('small')

        ttxt = "🏆  VICTORY!" if won else "💀  ELIMINATED"
        tcol = (255,220,38) if won else (255,75,75)
        if tf:
            scale  = 1.0 + _pulse(t,1.4)*0.045
            ts     = tf.render(ttxt, True, tcol)
            scaled = pygame.transform.smoothscale(
                ts,(int(ts.get_width()*scale),int(ts.get_height()*scale)))
            screen.blit(scaled, scaled.get_rect(center=(self._sw//2, pr.y+62)))

        if winner and lf:
            _draw_text_aa(screen, f"Winner: {winner.name}",
                          self._sw//2, pr.y+115, lf,(215,220,240),center=True)

        if player:
            sy = pr.y+155
            for line, col in [
                (f"Your Score: {player.score}",          (215,220,255)),
                (f"Kills: {player.kills}",               (255,100,100)),
                (f"Length: {player.length}",             (100,255,155)),
                (f"Level: {player.level}",               (155,95,255)),
                (f"+{player.coins_collected} coins  "
                 f"+{5 if won else 1} diamonds",         (255,210,55)),
            ]:
                if mf:
                    _draw_text_aa(screen,line,self._sw//2,sy,mf,col,center=True)
                sy+=32

        mouse  = pygame.mouse.get_pos()
        clicked= False; click_pos = None
        for event in events:
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                clicked=True; click_pos=event.pos

        action = None
        by     = pr.bottom - 88
        for lbl,act,bc,hc in [
            ("▶  PLAY AGAIN",'play',(18,95,28),(38,195,65)),
            ("  MAIN MENU",  'menu',(18,38,135),(38,75,215)),
        ]:
            br   = pygame.Rect(self._sw//2-125, by, 250,48)
            hov  = br.collidepoint(mouse)
            _glass_panel(screen, br, bg=hc if hov else bc, bg_alpha=225,
                         border=hc, border_alpha=235, radius=13)
            if mf:
                _draw_text_aa(screen,lbl,br.centerx,br.centery,mf,(255,255,255),center=True)
            if clicked and click_pos and br.collidepoint(click_pos):
                action = act
            by += 56
        return action

    # ── pause ─────────────────────────────────────────────────────────────────
    def draw_pause(self, events: list) -> Optional[str]:
        screen = self._screen; t = self._t
        ov = pygame.Surface((self._sw,self._sh),pygame.SRCALPHA)
        ov.fill((0,0,0,158))
        screen.blit(ov,(0,0))

        pr = pygame.Rect(self._sw//2-185, self._sh//2-135, 370, 270)
        _glass_panel(screen, pr, bg=(12,16,36), bg_alpha=225,
                     border=(75,125,255), border_alpha=225,
                     radius=18, inner_glow=True, inner_glow_col=(60,110,255))

        tf = self._fonts.get('title')
        mf = self._fonts.get('medium')
        if tf:
            _draw_text_aa(screen,"PAUSED",self._sw//2,self._sh//2-90,
                          tf,(195,205,255),center=True)

        mouse  = pygame.mouse.get_pos()
        clicked= False; click_pos = None
        for event in events:
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                clicked=True; click_pos=event.pos

        action=None
        for lbl,act,bc,hc,off in [
            ("▶  RESUME",    'resume',(18,105,28),(38,205,68), 18),
            ("✕  QUIT MATCH",'quit',  (105,18,18),(215,48,48), 80),
        ]:
            br  = pygame.Rect(self._sw//2-115, self._sh//2-8+off, 230,48)
            hov = br.collidepoint(mouse)
            _glass_panel(screen,br,bg=hc if hov else bc,bg_alpha=225,
                         border=hc,border_alpha=235,radius=12)
            if mf:
                _draw_text_aa(screen,lbl,br.centerx,br.centery,mf,(255,255,255),center=True)
            if clicked and click_pos and br.collidepoint(click_pos):
                action=act
        return action
