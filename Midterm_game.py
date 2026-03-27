"""
Stellar Harvest - A Space Mining Adventure
==========================================
Author: Student
Description:
    Pilot your mining ship through an asteroid field, collecting glowing ore
    crystals for points while avoiding collision with deadly asteroids.
    Your ship has a shield that absorbs impacts — manage it wisely!
    The game gets progressively harder as your score increases.

Controls:
    WASD or Arrow Keys - Move ship
    ESC               - Quit game

Graded on: Core Functionality, Code Structure, Readability,
           Error Handling, Gameplay Design & Creativity
"""

import pygame
import random
import sys
import math

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────
SCREEN_W, SCREEN_H = 900, 700
FPS = 60
TITLE = "Stellar Harvest"

# Colors (R, G, B)
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
YELLOW      = (255, 230, 50)
ORANGE      = (255, 140, 0)
RED         = (220, 50,  50)
CYAN        = (0,   220, 255)
DARK_BLUE   = (5,   10,  40)
PURPLE      = (130, 50,  200)
GREEN       = (50,  220, 100)
LIGHT_GRAY  = (200, 200, 210)
SHIELD_COL  = (80,  180, 255, 120)   # semi-transparent blue

# Player settings
PLAYER_SPEED      = 5
PLAYER_RADIUS     = 22
MAX_SHIELD        = 3        # shield "hits" before game over
INVINCIBILITY_MS  = 1500     # milliseconds of invincibility after a hit

# Ore (collectible) settings
ORE_BASE_COUNT    = 6        # ores present on screen at once
ORE_RADIUS        = 10
ORE_COLORS        = [YELLOW, CYAN, GREEN, (255, 100, 200)]
ORE_VALUES        = {        # points per color
    YELLOW:        10,
    CYAN:          20,
    GREEN:         15,
    (255, 100, 200): 30,
}

# Asteroid settings
ASTEROID_MIN_R    = 18
ASTEROID_MAX_R    = 42
ASTEROID_BASE_SPD = 1.8
ASTEROID_BASE_CNT = 5

# Star background
STAR_COUNT        = 150


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def random_edge_position():
    """Return a random (x, y) position along one of the four screen edges."""
    edge = random.randint(0, 3)
    if edge == 0:   # top
        return random.randint(0, SCREEN_W), -50
    elif edge == 1: # bottom
        return random.randint(0, SCREEN_W), SCREEN_H + 50
    elif edge == 2: # left
        return -50, random.randint(0, SCREEN_H)
    else:           # right
        return SCREEN_W + 50, random.randint(0, SCREEN_H)


def circles_collide(ax, ay, ar, bx, by, br):
    """Return True if two circles overlap (circle-circle collision detection)."""
    dist_sq = (ax - bx) ** 2 + (ay - by) ** 2
    return dist_sq <= (ar + br) ** 2


def draw_glowing_circle(surface, color, cx, cy, radius, glow_radius):
    """Draw a circle with a soft glow halo using additive-style layering."""
    # Draw several transparent rings for the glow effect
    glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
    for r in range(glow_radius, radius, -2):
        alpha = max(0, int(80 * (1 - (r - radius) / (glow_radius - radius + 1))))
        pygame.draw.circle(glow_surf, (*color, alpha), (glow_radius, glow_radius), r)
    surface.blit(glow_surf, (cx - glow_radius, cy - glow_radius))
    # Solid core
    pygame.draw.circle(surface, color, (cx, cy), radius)


def clamp(value, lo, hi):
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


# ─────────────────────────────────────────────
#  CLASSES
# ─────────────────────────────────────────────

class Star:
    """A static background star with a subtle twinkle animation."""

    def __init__(self):
        self.x    = random.randint(0, SCREEN_W)
        self.y    = random.randint(0, SCREEN_H)
        self.size = random.choice([1, 1, 1, 2, 2, 3])
        self.base_brightness = random.randint(100, 255)
        self.phase = random.uniform(0, math.tau)   # random twinkle offset

    def update(self, dt_ms):
        """Animate the twinkle phase."""
        self.phase += 0.002 * dt_ms

    def draw(self, surface):
        """Draw the star with a twinkle effect."""
        brightness = int(self.base_brightness * (0.6 + 0.4 * math.sin(self.phase)))
        color = (brightness, brightness, min(255, brightness + 30))
        pygame.draw.circle(surface, color, (self.x, self.y), self.size)


class Player:
    """
    The player-controlled mining ship.

    Attributes:
        x, y     -- center position (floats for smooth movement)
        radius   -- collision radius
        shield   -- remaining shield points
        score    -- accumulated score
        invincible_until -- timestamp (ms) while player is immune to damage
    """

    def __init__(self):
        self.x      = SCREEN_W // 2
        self.y      = SCREEN_H // 2
        self.radius = PLAYER_RADIUS
        self.shield = MAX_SHIELD
        self.score  = 0
        self.invincible_until = 0   # epoch ms; 0 = not invincible
        self._pulse = 0.0           # engine flame animation counter

    # ── Movement ──────────────────────────────

    def handle_input(self, keys):
        """Move the ship based on WASD / arrow key input, clamped to screen."""
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += 1

        # Normalize diagonal movement so speed is consistent
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.x = clamp(self.x + dx * PLAYER_SPEED, self.radius, SCREEN_W - self.radius)
        self.y = clamp(self.y + dy * PLAYER_SPEED, self.radius, SCREEN_H - self.radius)

    # ── Shield damage ─────────────────────────

    def take_hit(self, now_ms):
        """
        Reduce shield by 1 and grant temporary invincibility.
        Returns True if the player still has shields remaining.
        """
        if now_ms < self.invincible_until:
            return True  # still invincible — ignore hit
        self.shield -= 1
        self.invincible_until = now_ms + INVINCIBILITY_MS
        return self.shield > 0

    def is_invincible(self, now_ms):
        return now_ms < self.invincible_until

    # ── Rendering ─────────────────────────────

    def draw(self, surface, now_ms):
        """Draw the ship as a stylized triangle with engine flame and shield."""
        cx, cy = int(self.x), int(self.y)
        self._pulse += 0.12

        # ── Invincibility flash ──
        if self.is_invincible(now_ms) and (now_ms // 100) % 2 == 0:
            return  # blink: skip drawing every other 100ms tick

        # ── Shield bubble ──
        if self.shield > 0:
            shield_surf = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
            alpha = 60 + int(30 * math.sin(self._pulse))
            pygame.draw.circle(
                shield_surf, (*CYAN, alpha),
                (self.radius * 2, self.radius * 2), self.radius + 6
            )
            surface.blit(shield_surf, (cx - self.radius * 2, cy - self.radius * 2))

        # ── Engine flame (animated) ──
        flame_len = 14 + int(6 * math.sin(self._pulse))
        flame_points = [
            (cx - 8,  cy + 18),
            (cx + 8,  cy + 18),
            (cx,      cy + 18 + flame_len),
        ]
        flame_color = ORANGE if (now_ms // 80) % 2 == 0 else YELLOW
        pygame.draw.polygon(surface, flame_color, flame_points)

        # ── Ship body (upward-pointing triangle) ──
        ship_points = [
            (cx,      cy - 22),   # nose
            (cx - 16, cy + 18),   # bottom-left
            (cx + 16, cy + 18),   # bottom-right
        ]
        pygame.draw.polygon(surface, LIGHT_GRAY, ship_points)

        # ── Cockpit window ──
        pygame.draw.circle(surface, CYAN, (cx, cy - 6), 6)
        pygame.draw.circle(surface, WHITE, (cx, cy - 6), 3)

        # ── Wing accents ──
        pygame.draw.line(surface, CYAN, (cx - 16, cy + 18), (cx - 22, cy + 10), 2)
        pygame.draw.line(surface, CYAN, (cx + 16, cy + 18), (cx + 22, cy + 10), 2)


class Ore:
    """
    A collectible resource crystal that floats gently on screen.

    Attributes:
        x, y   -- center position
        color  -- ore color (maps to point value)
        radius -- collision radius
        value  -- score points awarded on collection
    """

    def __init__(self):
        self._respawn()

    def _respawn(self):
        """Place the ore at a random location and pick a color/value."""
        self.x      = random.randint(ORE_RADIUS + 10, SCREEN_W - ORE_RADIUS - 10)
        self.y      = random.randint(ORE_RADIUS + 10, SCREEN_H - ORE_RADIUS - 10)
        self.color  = random.choice(ORE_COLORS)
        self.radius = ORE_RADIUS
        self.value  = ORE_VALUES[self.color]
        self._phase = random.uniform(0, math.tau)   # float bob phase

    def update(self, dt_ms):
        """Gentle floating animation."""
        self._phase += 0.003 * dt_ms

    def draw(self, surface):
        """Draw the ore as a glowing crystal."""
        bob_y = int(self.y + 3 * math.sin(self._phase))
        draw_glowing_circle(surface, self.color, int(self.x), bob_y,
                            self.radius, self.radius + 10)

    def respawn(self):
        """Called after collection — place ore at a new location."""
        self._respawn()


class Asteroid:
    """
    A tumbling asteroid that crosses the screen.

    Attributes:
        x, y   -- center position (floats)
        radius -- collision radius (and visual size)
        vx, vy -- velocity components
        color  -- surface color
        angle  -- current rotation angle for drawing
        spin   -- rotation speed
    """

    def __init__(self, speed_mult=1.0):
        self._init(speed_mult)

    def _init(self, speed_mult=1.0):
        """Spawn from a random screen edge, heading inward."""
        self.radius = random.randint(ASTEROID_MIN_R, ASTEROID_MAX_R)
        self.x, self.y = random_edge_position()
        self.color = random.choice([
            (160, 100, 60), (130, 130, 130), (110, 80, 60), (90, 90, 110)
        ])

        # Aim roughly toward the center with some randomness
        target_x = SCREEN_W // 2 + random.randint(-200, 200)
        target_y = SCREEN_H // 2 + random.randint(-200, 200)
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy) or 1
        speed = (ASTEROID_BASE_SPD + random.uniform(-0.5, 1.0)) * speed_mult
        self.vx = (dx / dist) * speed
        self.vy = (dy / dist) * speed

        # Visual rotation
        self.angle = random.uniform(0, 360)
        self.spin  = random.uniform(-2.0, 2.0)

        # Irregular shape offsets (polygon vertices)
        pts = 8
        self._verts = []
        for i in range(pts):
            theta = (i / pts) * math.tau
            r = self.radius * random.uniform(0.75, 1.25)
            self._verts.append((math.cos(theta) * r, math.sin(theta) * r))

    def update(self, dt_ms):
        """Move and rotate the asteroid."""
        factor = dt_ms / 16.67  # normalize to 60 fps
        self.x    += self.vx * factor
        self.y    += self.vy * factor
        self.angle = (self.angle + self.spin * factor) % 360

    def is_off_screen(self):
        """Return True if the asteroid has fully left the visible area."""
        margin = self.radius + 80
        return (self.x < -margin or self.x > SCREEN_W + margin or
                self.y < -margin or self.y > SCREEN_H + margin)

    def draw(self, surface):
        """Draw the asteroid as an irregular polygon with a highlight."""
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        # Rotate and translate vertices
        pts = []
        for vx, vy in self._verts:
            rx = vx * cos_a - vy * sin_a + self.x
            ry = vx * sin_a + vy * cos_a + self.y
            pts.append((int(rx), int(ry)))

        pygame.draw.polygon(surface, self.color, pts)
        pygame.draw.polygon(surface, (self.color[0] + 40, self.color[1] + 40, self.color[2] + 40), pts, 2)

        # Small highlight dot
        highlight = (int(self.x - self.radius * 0.3), int(self.y - self.radius * 0.3))
        pygame.draw.circle(surface, (220, 200, 180), highlight, max(2, self.radius // 5))


class ParticleEffect:
    """
    Simple particle burst used for ore collection and shield hit effects.

    Attributes:
        particles -- list of dicts, each with position, velocity, color, life
    """

    def __init__(self, x, y, color, count=12, speed=3.5):
        self.particles = []
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            spd   = random.uniform(1.0, speed)
            self.particles.append({
                "x":     float(x),
                "y":     float(y),
                "vx":    math.cos(angle) * spd,
                "vy":    math.sin(angle) * spd,
                "color": color,
                "life":  random.uniform(0.4, 1.0),   # 0.0–1.0 (1.0 = full)
            })

    def update(self, dt_ms):
        """Move and fade all particles."""
        decay = 0.025 * (dt_ms / 16.67)
        for p in self.particles:
            p["x"]    += p["vx"] * (dt_ms / 16.67)
            p["y"]    += p["vy"] * (dt_ms / 16.67)
            p["life"] -= decay
        self.particles = [p for p in self.particles if p["life"] > 0]

    def is_done(self):
        return len(self.particles) == 0

    def draw(self, surface):
        for p in self.particles:
            alpha = int(255 * p["life"])
            r = max(1, int(4 * p["life"]))
            color = (*p["color"][:3], alpha)
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (r, r), r)
            surface.blit(s, (int(p["x"]) - r, int(p["y"]) - r))


# ─────────────────────────────────────────────
#  HUD / UI DRAWING
# ─────────────────────────────────────────────

def draw_hud(surface, font_lg, font_sm, player, level):
    """
    Render the heads-up display:
        - Score (top-left)
        - Shield pips (top-center)
        - Level (top-right)
        - Instructions hint (bottom)
    """
    # Score
    score_surf = font_lg.render(f"SCORE  {player.score:06d}", True, WHITE)
    surface.blit(score_surf, (20, 15))

    # Shield pips
    shield_label = font_sm.render("SHIELD", True, CYAN)
    surface.blit(shield_label, (SCREEN_W // 2 - shield_label.get_width() // 2, 12))
    for i in range(MAX_SHIELD):
        color = CYAN if i < player.shield else (50, 60, 80)
        px = SCREEN_W // 2 - (MAX_SHIELD * 22) // 2 + i * 22
        pygame.draw.rect(surface, color, (px, 30, 16, 10), border_radius=3)

    # Level
    lvl_surf = font_sm.render(f"LEVEL {level}", True, ORANGE)
    surface.blit(lvl_surf, (SCREEN_W - lvl_surf.get_width() - 20, 15))

    # Bottom hint
    hint = font_sm.render("WASD / Arrows to move  |  ESC to quit", True, (80, 80, 110))
    surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 24))


def draw_screen_overlay(surface, font_title, font_body, title_text, subtitle_text):
    """Render a centered full-screen overlay (game over / title screen)."""
    # Dark semi-transparent backdrop
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 15, 180))
    surface.blit(overlay, (0, 0))

    title_surf = font_title.render(title_text, True, YELLOW)
    sub_surf   = font_body.render(subtitle_text, True, WHITE)

    surface.blit(title_surf, (SCREEN_W // 2 - title_surf.get_width() // 2, SCREEN_H // 2 - 60))
    surface.blit(sub_surf,   (SCREEN_W // 2 - sub_surf.get_width()  // 2, SCREEN_H // 2 + 10))


# ─────────────────────────────────────────────
#  GAME STATE MANAGEMENT
# ─────────────────────────────────────────────

class GameState:
    """
    Tracks all mutable game data in one place for clarity.

    States:
        "title"    -- title screen shown at launch
        "playing"  -- active gameplay
        "dead"     -- game-over screen
    """

    TITLE   = "title"
    PLAYING = "playing"
    DEAD    = "dead"

    def __init__(self):
        self.state = self.TITLE

    def set(self, state):
        if state not in (self.TITLE, self.PLAYING, self.DEAD):
            raise ValueError(f"Unknown game state: {state!r}")
        self.state = state

    def is_(self, state):
        return self.state == state


# ─────────────────────────────────────────────
#  MAIN GAME LOOP
# ─────────────────────────────────────────────

def new_game():
    """
    Initialise (or reset) all game objects and return them as a dict.
    Separating this allows easy game restart without re-running pygame.init().
    """
    player    = Player()
    stars     = [Star() for _ in range(STAR_COUNT)]
    ores      = [Ore()  for _ in range(ORE_BASE_COUNT)]
    asteroids = [Asteroid() for _ in range(ASTEROID_BASE_CNT)]
    effects   = []   # active ParticleEffects
    level     = 1
    level_threshold = 100  # score needed to advance a level
    return {
        "player":          player,
        "stars":           stars,
        "ores":            ores,
        "asteroids":       asteroids,
        "effects":         effects,
        "level":           level,
        "level_threshold": level_threshold,
        "speed_mult":      1.0,
    }


def compute_speed_mult(level):
    """Increase asteroid speed with level — caps at 3× for playability."""
    return min(1.0 + (level - 1) * 0.25, 3.0)


def run():
    """Entry point: initialise pygame, run the main loop, clean up on exit."""
    # ── Pygame init ───────────────────────────
    try:
        pygame.init()
    except pygame.error as e:
        print(f"[ERROR] pygame.init() failed: {e}")
        sys.exit(1)

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)
    clock  = pygame.time.Clock()

    # ── Fonts ─────────────────────────────────
    try:
        font_title = pygame.font.SysFont("consolas", 54, bold=True)
        font_large = pygame.font.SysFont("consolas", 28, bold=True)
        font_small = pygame.font.SysFont("consolas", 18)
        font_body  = pygame.font.SysFont("consolas", 22)
    except Exception:
        # Fallback to pygame's built-in default font
        font_title = pygame.font.Font(None, 60)
        font_large = pygame.font.Font(None, 32)
        font_small = pygame.font.Font(None, 22)
        font_body  = pygame.font.Font(None, 26)

    # ── Game state ────────────────────────────
    gs   = GameState()
    game = new_game()

    # ── Main loop ─────────────────────────────
    running = True
    while running:
        dt_ms  = clock.tick(FPS)     # milliseconds since last frame
        now_ms = pygame.time.get_ticks()

        # ── Event handling ────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # Start game from title or restart after death
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if gs.is_(GameState.TITLE) or gs.is_(GameState.DEAD):
                        game = new_game()
                        gs.set(GameState.PLAYING)

        # ── Title screen ──────────────────────
        if gs.is_(GameState.TITLE):
            screen.fill(DARK_BLUE)
            for star in game["stars"]:
                star.update(dt_ms)
                star.draw(screen)
            draw_screen_overlay(
                screen, font_title, font_body,
                "STELLAR HARVEST",
                "Collect ore  |  Dodge asteroids  |  ENTER to launch"
            )
            pygame.display.flip()
            continue

        # ── Game-over screen ──────────────────
        if gs.is_(GameState.DEAD):
            screen.fill(DARK_BLUE)
            for star in game["stars"]:
                star.update(dt_ms)
                star.draw(screen)
            draw_screen_overlay(
                screen, font_title, font_body,
                "SHIP DESTROYED",
                f"Final Score: {game['player'].score:06d}   |   ENTER to retry"
            )
            pygame.display.flip()
            continue

        # ── PLAYING ───────────────────────────
        player     = game["player"]
        stars      = game["stars"]
        ores       = game["ores"]
        asteroids  = game["asteroids"]
        effects    = game["effects"]

        # Input
        keys = pygame.key.get_pressed()
        player.handle_input(keys)

        # Update stars
        for star in stars:
            star.update(dt_ms)

        # Update ore float animation
        for ore in ores:
            ore.update(dt_ms)

        # Update asteroids; remove off-screen ones and respawn
        for asteroid in asteroids:
            asteroid.update(dt_ms)
        asteroids[:] = [a for a in asteroids if not a.is_off_screen()]
        while len(asteroids) < ASTEROID_BASE_CNT + (game["level"] - 1):
            asteroids.append(Asteroid(game["speed_mult"]))

        # Update particle effects
        for fx in effects:
            fx.update(dt_ms)
        effects[:] = [fx for fx in effects if not fx.is_done()]

        # ── Collision: player ↔ ore ────────────
        for ore in ores:
            if circles_collide(player.x, player.y, player.radius,
                               ore.x,    ore.y,    ore.radius):
                player.score += ore.value
                effects.append(ParticleEffect(ore.x, ore.y, ore.color, count=14))
                ore.respawn()

        # ── Collision: player ↔ asteroid ───────
        for asteroid in asteroids:
            if circles_collide(player.x, player.y, player.radius,
                               asteroid.x, asteroid.y, asteroid.radius):
                still_alive = player.take_hit(now_ms)
                effects.append(ParticleEffect(
                    player.x, player.y, RED, count=20, speed=5.0))
                if not still_alive:
                    gs.set(GameState.DEAD)
                    break

        # ── Level progression ──────────────────
        if player.score >= game["level"] * game["level_threshold"]:
            game["level"]      += 1
            game["speed_mult"]  = compute_speed_mult(game["level"])
            game["level_threshold"] = 100 + game["level"] * 50

        # ─────────────────────────────────────
        #  RENDERING
        # ─────────────────────────────────────
        screen.fill(DARK_BLUE)

        # Background stars
        for star in stars:
            star.draw(screen)

        # Ores
        for ore in ores:
            ore.draw(screen)

        # Asteroids
        for asteroid in asteroids:
            asteroid.draw(screen)

        # Particles (drawn below ship)
        for fx in effects:
            fx.draw(screen)

        # Player ship
        if gs.is_(GameState.PLAYING):
            player.draw(screen, now_ms)

        # HUD
        draw_hud(screen, font_large, font_small, player, game["level"])

        pygame.display.flip()

    # ── Cleanup ───────────────────────────────
    pygame.quit()
    sys.exit(0)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    run()
