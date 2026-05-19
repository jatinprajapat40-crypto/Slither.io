"""
skins.py – Premium Snake Skin Rendering System for SLITHER ROYALE
=================================================================
SkinManager provides 5 distinct, production-quality visual skin styles.
Each skin is drawn via draw_segment() which is the single master entry point.

Skin IDs:
  0 – Neon Cyan Glow     (radial alpha-surface glow)
  1 – Tiger Stripe        (alternating dynamic contrast bands)
  2 – Magma Pulse         (math.sin time-driven lava color shift)
  3 – Cosmic Sparkle      (floating stardust particles around each segment)
  4 – Golden Royal        (metallic 3D orbital gold rings)

Usage from main.py / renderer:
    from skins import SkinManager
    skin_mgr = SkinManager()
    skin_mgr.draw_segment(surface, position=(sx, sy), radius=r,
                          segment_index=i, skin_id=player_skin_id)
"""

import pygame
import math
import random
from typing import Tuple

# ---------------------------------------------------------------------------
# Internal colour helpers
# ---------------------------------------------------------------------------

def _clamp_color(r: float, g: float, b: float) -> Tuple[int, int, int]:
    """Clamp float RGB components into valid 0-255 integer range."""
    return (int(max(0, min(255, r))),
            int(max(0, min(255, g))),
            int(max(0, min(255, b))))


def _lerp_c(c1: Tuple[int, int, int],
            c2: Tuple[int, int, int],
            t: float) -> Tuple[int, int, int]:
    """Linear interpolation between two RGB tuples.  t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return _clamp_color(
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
    )


def _hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """Convert HSV (0-1 each) to integer RGB tuple."""
    if s == 0.0:
        val = int(v * 255)
        return (val, val, val)
    h6 = h * 6.0
    i = int(h6)
    f = h6 - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    sector = i % 6
    if sector == 0:
        r, g, b = v, t, p
    elif sector == 1:
        r, g, b = q, v, p
    elif sector == 2:
        r, g, b = p, v, t
    elif sector == 3:
        r, g, b = p, q, v
    elif sector == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return _clamp_color(r * 255, g * 255, b * 255)


# ---------------------------------------------------------------------------
# Glow surface cache – avoids rebuilding expensive alpha surfaces every frame
# ---------------------------------------------------------------------------

class _GlowCache:
    """LRU-style cache for pre-rendered radial glow surfaces."""

    def __init__(self, max_entries: int = 128):
        self._cache: dict = {}
        self._max = max_entries

    def get(self, radius: int, color: Tuple[int, int, int],
            alpha: int) -> pygame.Surface:
        key = (radius, color, alpha)
        if key in self._cache:
            return self._cache[key]

        diameter = radius * 2
        surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)

        # Build radial gradient: brightest at centre → transparent at edge
        for ring_r in range(radius, 0, -1):
            # Alpha falls off quadratically from centre
            ring_alpha = int(alpha * (ring_r / radius) ** 2)
            ring_alpha = max(0, min(255, ring_alpha))
            ring_color = (*color[:3], ring_alpha)
            pygame.draw.circle(surf, ring_color, (radius, radius), ring_r)

        # Bright core
        core_r = max(1, radius // 4)
        bright = _lerp_c(color, (255, 255, 255), 0.55)
        pygame.draw.circle(surf, (*bright, min(255, alpha + 60)),
                           (radius, radius), core_r)

        if len(self._cache) >= self._max:
            # Evict oldest entry
            oldest = next(iter(self._cache))
            del self._cache[oldest]

        self._cache[key] = surf
        return surf


# ---------------------------------------------------------------------------
# Cosmic Sparkle particle store
# ---------------------------------------------------------------------------

class _SparkleParticle:
    """One tiny stardust fleck orbiting a snake segment."""

    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life',
                 'size', 'color', 'angle', 'orbit_r', 'orbit_speed')

    def __init__(self, cx: float, cy: float, base_color: Tuple[int, int, int]):
        self.angle = random.uniform(0, math.tau)
        self.orbit_r = random.uniform(4, 18)
        self.orbit_speed = random.uniform(1.5, 4.0) * random.choice((-1, 1))
        self.x = cx + math.cos(self.angle) * self.orbit_r
        self.y = cy + math.sin(self.angle) * self.orbit_r
        self.vx = random.uniform(-0.8, 0.8)
        self.vy = random.uniform(-0.8, 0.8)
        self.life = random.uniform(0.3, 0.9)
        self.max_life = self.life
        self.size = random.uniform(1.0, 3.0)
        # Slight hue variation from the base colour
        hue_shift = random.uniform(-0.08, 0.08)
        r, g, b = base_color
        self.color = _clamp_color(r + hue_shift * 60,
                                  g + hue_shift * 40,
                                  b + hue_shift * 80)


class _SparkleSystem:
    """Manages a pool of cosmic sparkle particles for Skin 3."""

    POOL_SIZE = 600

    def __init__(self):
        self._particles: list[_SparkleParticle] = []
        # Spawn budget: we only spawn a few new ones per draw call
        self._spawn_budget = 0.0

    def update(self, dt: float):
        alive = []
        for p in self._particles:
            p.life -= dt
            if p.life > 0:
                p.x += p.vx
                p.y += p.vy
                p.angle += p.orbit_speed * dt
                alive.append(p)
        self._particles = alive

    def emit(self, cx: float, cy: float,
             color: Tuple[int, int, int], count: int = 2):
        """Spawn `count` new sparkles around (cx, cy)."""
        remaining = self.POOL_SIZE - len(self._particles)
        for _ in range(min(count, remaining)):
            self._particles.append(_SparkleParticle(cx, cy, color))

    def draw(self, surface: pygame.Surface):
        for p in self._particles:
            t = p.life / p.max_life          # 1 → 0
            alpha = int(220 * t)
            sz = max(1, int(p.size * t))
            col = (*p.color[:3], alpha)
            # Draw on an SRCALPHA surface for per-particle alpha
            diam = sz * 2 + 2
            s = pygame.Surface((diam, diam), pygame.SRCALPHA)
            pygame.draw.circle(s, col, (sz + 1, sz + 1), sz)
            surface.blit(s, (int(p.x) - sz - 1, int(p.y) - sz - 1),
                         special_flags=pygame.BLEND_ALPHA_SDL2)


# ---------------------------------------------------------------------------
# Main SkinManager class
# ---------------------------------------------------------------------------

class SkinManager:
    """
    Manages rendering of 5 premium snake skin styles.

    Public API
    ----------
    draw_segment(surface, position, radius, segment_index, skin_id)
        Render a single snake body segment according to the active skin.

    draw_head(surface, position, radius, angle, skin_id)
        Render the head with eyes, matching the skin theme.

    update(dt)
        Must be called once per frame to advance time-based animations.

    SKIN_NAMES : list[str]
        Human-readable display names for all 5 skins.
    """

    SKIN_COUNT = 5
    SKIN_NAMES = [
        "Neon Cyan Glow",
        "Tiger Stripe",
        "Magma Pulse",
        "Cosmic Sparkle",
        "Golden Royal",
    ]

    # Skin colour palettes (primary, secondary, accent)
    _PALETTE = {
        0: ((0, 240, 255),   (0, 180, 220),   (180, 255, 255)),   # Neon Cyan
        1: ((220, 120, 10),  (20,  20,  20),   (255, 180,  60)),   # Tiger
        2: ((180, 20,   5),  (255, 120,  20),  (255,  60,   5)),   # Magma
        3: ((60,  20, 180),  (120,  60, 255),  (200, 160, 255)),   # Cosmic
        4: ((180, 140,  20), (255, 215,  60),  (255, 255, 200)),   # Gold
    }

    def __init__(self):
        self._glow_cache = _GlowCache(max_entries=256)
        self._sparkle = _SparkleSystem()
        self._time: float = 0.0          # Accumulated game time in seconds
        self._ticks: int = 0             # pygame.time.get_ticks() snapshot

    # ------------------------------------------------------------------
    # Frame update
    # ------------------------------------------------------------------

    def update(self, dt: float):
        """Advance animation timers.  Call once per game frame."""
        self._time += dt
        self._ticks = pygame.time.get_ticks()
        self._sparkle.update(dt)

    # ------------------------------------------------------------------
    # Master draw entry point
    # ------------------------------------------------------------------

    def draw_segment(
        self,
        surface: pygame.Surface,
        position: Tuple[float, float],
        radius: int,
        segment_index: int,
        skin_id: int,
    ):
        """
        Render one snake body segment.

        Parameters
        ----------
        surface       : pygame.Surface – the game canvas to draw on.
        position      : (screen_x, screen_y) – centre of the segment in pixels.
        radius        : pixel radius of this segment.
        segment_index : 0 = head end, increasing toward tail.
        skin_id       : 0-4 selecting one of the 5 premium skins.
        """
        if radius < 1:
            return

        sid = int(skin_id) % self.SKIN_COUNT
        ix, iy = int(position[0]), int(position[1])

        dispatch = [
            self._draw_neon_glow,
            self._draw_tiger_stripe,
            self._draw_magma_pulse,
            self._draw_cosmic_sparkle,
            self._draw_golden_royal,
        ]
        dispatch[sid](surface, ix, iy, radius, segment_index)

    # ------------------------------------------------------------------
    # Head drawing (skin-aware)
    # ------------------------------------------------------------------

    def draw_head(
        self,
        surface: pygame.Surface,
        position: Tuple[float, float],
        radius: int,
        angle: float,
        skin_id: int,
    ):
        """
        Render the snake head with eyes, styled to the active skin.

        Parameters
        ----------
        angle : snake's current heading in radians (0 = right).
        """
        if radius < 2:
            return

        sid = int(skin_id) % self.SKIN_COUNT
        ix, iy = int(position[0]), int(position[1])
        pal = self._PALETTE[sid]

        # Draw body segment first (handles the head shape too)
        self.draw_segment(surface, position, int(radius * 1.2), 0, skin_id)

        # ---- Eyes ----
        eye_dist = radius * 0.48
        eye_r    = max(2, int(radius * 0.30))
        pupil_r  = max(1, int(eye_r * 0.52))

        for side in (-1.0, 1.0):
            perp = angle + math.pi / 2 * side
            ex = ix + int(math.cos(perp) * eye_dist + math.cos(angle) * eye_dist * 0.45)
            ey = iy + int(math.sin(perp) * eye_dist + math.sin(angle) * eye_dist * 0.45)

            # White sclera
            pygame.draw.circle(surface, (240, 240, 240), (ex, ey), eye_r)

            # Skin-specific iris colour
            iris_colors = [
                (0, 220, 255),     # Neon – cyan iris
                (255, 140, 0),     # Tiger – amber iris
                (255, 80,  20),    # Magma – ember iris
                (160, 80, 255),    # Cosmic – violet iris
                (200, 160, 20),    # Gold – golden iris
            ]
            pygame.draw.circle(surface, iris_colors[sid], (ex, ey), eye_r - 1)

            # Pupil
            px = ex + int(math.cos(angle) * pupil_r * 0.5)
            py = ey + int(math.sin(angle) * pupil_r * 0.5)
            pygame.draw.circle(surface, (5, 5, 10), (px, py), pupil_r)

            # Specular highlight
            hx = ex - max(1, eye_r // 3)
            hy = ey - max(1, eye_r // 3)
            pygame.draw.circle(surface, (255, 255, 255), (hx, hy),
                               max(1, eye_r // 4))

        # Tongue (visible on head)
        self._draw_tongue(surface, ix, iy, radius, angle, pal[0])

    # ------------------------------------------------------------------
    # Skin 0 – Neon Cyan Glow
    # ------------------------------------------------------------------

    def _draw_neon_glow(
        self,
        surface: pygame.Surface,
        ix: int, iy: int,
        radius: int,
        seg_idx: int,
    ):
        """
        Two-layer neon glow:
          Layer 1 – a large semi-transparent radial gradient (the 'halo').
          Layer 2 – the bright, solid core circle.
        The halo is built once and cached; it uses SRCALPHA blending.
        """
        pal = self._PALETTE[0]
        core_color   = pal[0]   # (0, 240, 255)
        inner_color  = pal[1]   # (0, 180, 220)
        accent_color = pal[2]   # (180, 255, 255)

        # Subtle depth pulsing along the body length
        depth_t = seg_idx * 0.08
        pulse_shift = math.sin(self._time * 3.0 - depth_t) * 0.12
        glow_alpha  = int(max(30, min(110, 80 + pulse_shift * 80)))

        # Outer halo – 3× the segment radius
        halo_r  = max(4, int(radius * 3.0))
        halo_sf = self._glow_cache.get(halo_r, core_color, glow_alpha)
        blit_x  = ix - halo_r
        blit_y  = iy - halo_r
        surface.blit(halo_sf, (blit_x, blit_y),
                     special_flags=pygame.BLEND_ALPHA_SDL2)

        # Medium glow ring
        mid_r  = max(3, int(radius * 1.8))
        mid_sf = self._glow_cache.get(mid_r, inner_color, min(160, glow_alpha + 60))
        surface.blit(mid_sf, (ix - mid_r, iy - mid_r),
                     special_flags=pygame.BLEND_ALPHA_SDL2)

        # Solid core
        t_body = max(0.0, min(1.0, seg_idx / 60))
        core_c = _lerp_c(core_color, inner_color, t_body * 0.6)
        pygame.draw.circle(surface, core_c, (ix, iy), radius)

        # Bright centre specular
        spec_r = max(1, radius // 3)
        spec_c = _lerp_c(core_c, accent_color, 0.70)
        pygame.draw.circle(surface, spec_c, (ix - spec_r // 2, iy - spec_r // 2),
                           spec_r)

        # Thin crisp outline
        pygame.draw.circle(surface, (0, 200, 240), (ix, iy), radius, 1)

    # ------------------------------------------------------------------
    # Skin 1 – Tiger Stripe
    # ------------------------------------------------------------------

    def _draw_tiger_stripe(
        self,
        surface: pygame.Surface,
        ix: int, iy: int,
        radius: int,
        seg_idx: int,
    ):
        """
        Alternating high-contrast stripes.
        Every N segments the colour flips between rich orange and deep black,
        with a subtle brown outline.  Stripe width varies with body depth.
        """
        pal = self._PALETTE[1]
        orange   = pal[0]    # (220, 120, 10)
        black    = pal[1]    # (20,  20,  20)
        highlight= pal[2]    # (255, 180, 60)

        # Stripe width grows slightly towards the tail
        stripe_period = max(2, 3 + seg_idx // 20)
        band = (seg_idx // stripe_period) % 2

        # Animate stripe position gently along the body
        anim_band = (seg_idx + int(self._time * 4)) // stripe_period
        band = anim_band % 2

        if band == 0:
            base_color = orange
            spec_color = highlight
        else:
            base_color = black
            spec_color = (60, 40, 10)

        # Depth fade: body gets slightly darker toward the tail
        fade_t = min(1.0, seg_idx / 80)
        draw_color = _lerp_c(base_color, (10, 10, 10), fade_t * 0.35)

        pygame.draw.circle(surface, draw_color, (ix, iy), radius)

        # Specular highlight (top-left)
        spec_r = max(1, radius // 3)
        pygame.draw.circle(surface, spec_color,
                           (ix - spec_r // 2, iy - spec_r // 2), spec_r)

        # Outline gives a thick, leathery look
        out_r = max(1, int(radius * 0.12))
        pygame.draw.circle(surface, (90, 50, 5), (ix, iy), radius, out_r)

        # Central band line: a thin arc-like mark
        if band == 0 and radius > 5:
            line_color = _lerp_c(orange, (80, 30, 0), 0.5)
            lw = max(1, radius // 5)
            pygame.draw.line(surface, line_color,
                             (ix - radius + lw, iy),
                             (ix + radius - lw, iy), lw)

    # ------------------------------------------------------------------
    # Skin 2 – Magma Pulse
    # ------------------------------------------------------------------

    def _draw_magma_pulse(
        self,
        surface: pygame.Surface,
        ix: int, iy: int,
        radius: int,
        seg_idx: int,
    ):
        """
        Uses pygame.time.get_ticks() and math.sin to wave RGB values
        smoothly between deep crimson and bright lava orange.
        Each segment is phase-shifted so the colour ripples travel the body.
        """
        pal = self._PALETTE[2]
        deep_red  = pal[0]   # (180, 20, 5)
        lava_org  = pal[1]   # (255, 120, 20)
        ember     = pal[2]   # (255, 60, 5)

        # Phase travels from head to tail at ~2 Hz
        phase_speed = 0.002   # units: 1/ms → radians per ms
        seg_phase   = seg_idx * 0.18
        t_raw       = self._ticks * phase_speed - seg_phase
        t           = (math.sin(t_raw) + 1.0) * 0.5    # 0 → 1

        # Colour swings between deep_red and lava_org
        base_c = _lerp_c(deep_red, lava_org, t)

        # Extra brightness burst at peak
        burst = max(0.0, t - 0.75) * 4.0
        draw_c = _lerp_c(base_c, ember, burst)

        pygame.draw.circle(surface, draw_c, (ix, iy), radius)

        # Hot-core highlight – white-orange at the centre
        core_t  = (math.sin(t_raw * 1.7 + 1.2) + 1.0) * 0.5
        core_c  = _lerp_c(lava_org, (255, 240, 200), core_t * 0.6)
        core_r  = max(1, int(radius * 0.38))
        pygame.draw.circle(surface, core_c,
                           (ix - core_r // 3, iy - core_r // 3), core_r)

        # Dark outer ring for depth
        pygame.draw.circle(surface, (80, 10, 5), (ix, iy), radius, max(1, radius // 6))

        # Occasional heat shimmer: extra bright speck
        if t > 0.85 and radius > 4:
            speck_r = max(1, radius // 5)
            speck_x = ix + random.randint(-radius // 3, radius // 3)
            speck_y = iy + random.randint(-radius // 3, radius // 3)
            pygame.draw.circle(surface, (255, 240, 180), (speck_x, speck_y), speck_r)

    # ------------------------------------------------------------------
    # Skin 3 – Cosmic Sparkle
    # ------------------------------------------------------------------

    def _draw_cosmic_sparkle(
        self,
        surface: pygame.Surface,
        ix: int, iy: int,
        radius: int,
        seg_idx: int,
    ):
        """
        Deep space purple-blue body with tiny stardust particles.
        Particles orbit / drift around each segment and fade out.
        """
        pal = self._PALETTE[3]
        deep   = pal[0]   # (60, 20, 180)
        violet = pal[1]   # (120, 60, 255)
        pale   = pal[2]   # (200, 160, 255)

        # Depth colour fade
        depth_t = min(1.0, seg_idx / 70)
        base_c  = _lerp_c(violet, deep, depth_t * 0.6)

        # Slow shimmer across the whole body
        shimmer = (math.sin(self._time * 1.8 + seg_idx * 0.12) + 1.0) * 0.5
        draw_c  = _lerp_c(base_c, pale, shimmer * 0.25)

        pygame.draw.circle(surface, draw_c, (ix, iy), radius)

        # Inner highlight – galaxy core feel
        inner_r = max(1, int(radius * 0.45))
        inner_c = _lerp_c(pale, (240, 220, 255), shimmer * 0.55)
        pygame.draw.circle(surface, inner_c,
                           (ix - inner_r // 3, iy - inner_r // 3), inner_r)

        # Dark outer ring
        pygame.draw.circle(surface, (20, 5, 60), (ix, iy), radius, max(1, radius // 7))

        # Emit new sparkles sparingly (only every few segments to budget CPU)
        if seg_idx % 3 == 0:
            emit_count = 1 if radius < 8 else 2
            self._sparkle.emit(ix, iy, pale, emit_count)

        # The sparkle system draws all alive particles each frame (called separately)
        # via draw_sparkles() so they layer on top of all segments correctly.

    def draw_sparkles(self, surface: pygame.Surface):
        """
        Call once per frame AFTER drawing all segments for skin 3,
        so sparkles render on top of the entire snake body.
        """
        self._sparkle.draw(surface)

    # ------------------------------------------------------------------
    # Skin 4 – Golden Royal
    # ------------------------------------------------------------------

    def _draw_golden_royal(
        self,
        surface: pygame.Surface,
        ix: int, iy: int,
        radius: int,
        seg_idx: int,
    ):
        """
        Metallic gold 3D look achieved by:
          • Base dark-gold circle.
          • A set of concentric orbital highlight rings.
          • A bright specular cap rotated by time for a 'spinning' sheen.
          • A dark bottom shadow for depth.
        """
        pal   = self._PALETTE[4]
        dark  = pal[0]   # (180, 140, 20)
        mid   = pal[1]   # (255, 215, 60)
        light = pal[2]   # (255, 255, 200)

        # Base gold body
        depth_t = min(1.0, seg_idx / 80)
        base_c  = _lerp_c(mid, dark, depth_t * 0.50)
        pygame.draw.circle(surface, base_c, (ix, iy), radius)

        # ---- Concentric orbital highlight rings ----
        # Ring spacing and alpha calculated for a 3D sphere illusion.
        ring_data = [
            (0.85, (180, 130, 10), max(1, radius // 6)),  # outer shadow ring
            (0.68, mid,            max(1, radius // 5)),  # bright equator ring
            (0.50, light,          max(1, radius // 6)),  # inner highlight ring
        ]
        for ring_frac, ring_color, ring_width in ring_data:
            ring_r = max(1, int(radius * ring_frac))
            pygame.draw.circle(surface, ring_color, (ix, iy), ring_r, ring_width)

        # ---- Rotating specular cap ----
        # The sheen angle orbits at different speeds per segment → 3D rotation feel
        sheen_angle = self._time * 1.6 + seg_idx * 0.22
        sheen_dist  = radius * 0.38
        sheen_x = ix + int(math.cos(sheen_angle) * sheen_dist)
        sheen_y = iy + int(math.sin(sheen_angle) * sheen_dist * 0.5)  # flatten vertically
        sheen_r = max(1, int(radius * 0.30))

        sheen_surf = pygame.Surface((sheen_r * 2 + 2, sheen_r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(sheen_surf, (*light, 180),
                           (sheen_r + 1, sheen_r + 1), sheen_r)
        surface.blit(sheen_surf, (sheen_x - sheen_r - 1, sheen_y - sheen_r - 1),
                     special_flags=pygame.BLEND_ALPHA_SDL2)

        # ---- Bottom shadow ----
        shadow_r  = max(1, int(radius * 0.60))
        shadow_y  = iy + int(radius * 0.40)
        shadow_sf = pygame.Surface((shadow_r * 2, shadow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(shadow_sf, (40, 30, 0, 120),
                           (shadow_r, shadow_r), shadow_r)
        surface.blit(shadow_sf, (ix - shadow_r, shadow_y - shadow_r),
                     special_flags=pygame.BLEND_ALPHA_SDL2)

        # Thin dark gold outline
        pygame.draw.circle(surface, (120, 90, 5), (ix, iy), radius, max(1, radius // 8))

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _draw_tongue(
        self,
        surface: pygame.Surface,
        hx: int, hy: int,
        radius: int,
        angle: float,
        color: Tuple[int, int, int],
    ):
        """Draw an animated forked tongue from the snake's head."""
        flick = math.sin(self._time * 12.0)   # fast flick
        tongue_len = radius * 1.6
        fork_len   = radius * 0.55
        fork_angle = 0.42

        # Tongue root to tip
        tx = hx + int(math.cos(angle) * tongue_len)
        ty = hy + int(math.sin(angle) * tongue_len)

        tongue_color = (220, 20, 20)
        pygame.draw.line(surface, tongue_color, (hx, hy), (tx, ty),
                         max(1, radius // 5))

        # Fork tips (only when flicked outward)
        if flick > 0:
            for fork_side in (-1, 1):
                fa = angle + fork_side * fork_angle
                fx = tx + int(math.cos(fa) * fork_len * flick)
                fy = ty + int(math.sin(fa) * fork_len * flick)
                pygame.draw.line(surface, tongue_color,
                                 (tx, ty), (fx, fy),
                                 max(1, radius // 6))

    # ------------------------------------------------------------------
    # Preview strip (used by UIManager skin selector)
    # ------------------------------------------------------------------

    def draw_preview_strip(
        self,
        surface: pygame.Surface,
        skin_id: int,
        start_x: int,
        start_y: int,
        seg_count: int = 22,
        seg_radius: int = 10,
        spacing: int = 16,
        wave_amplitude: int = 18,
        wave_speed: float = 2.0,
    ):
        """
        Draw a live, animated horizontal snake preview strip.
        Used by the UI skin-selector card.

        The strip wiggles sinusoidally to show the skin in motion.
        """
        for i in range(seg_count - 1, -1, -1):
            # Wave motion
            wave = math.sin(self._time * wave_speed + i * 0.35) * wave_amplitude
            sx = start_x + i * spacing
            sy = int(start_y + wave)
            r  = max(3, seg_radius - i // 5)   # taper towards tail
            self.draw_segment(surface, (sx, sy), r, i, skin_id)

        # Draw sparkles on top for cosmic skin
        if skin_id == 3:
            self.draw_sparkles(surface)

        # Draw head (index 0)
        head_angle = math.atan2(
            math.sin(self._time * wave_speed) * wave_amplitude * 0.35 * wave_speed,
            spacing
        )
        self.draw_head(surface, (start_x, start_y), seg_radius + 2,
                       head_angle, skin_id)
