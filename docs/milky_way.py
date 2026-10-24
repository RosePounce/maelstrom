import math
import os
import random
import pygame

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 900, 900
CENTER = (WIDTH // 2, HEIGHT // 2)
N_SECTORS = 6                       # nombre de secteurs (5 ou 6, au choix)
IMAGE_PATH = "voie_lactee_gaia.jpg"  # l'image Gaia, à placer à côté du script
BG_COLOR = (8, 8, 20)

SECTOR_NAMES = ["Secteur Alpha", "Secteur Beta", "Secteur Gamma",
                "Secteur Delta", "Secteur Epsilon", "Secteur Zêta"]
SECTOR_COLORS = [(120, 180, 255), (255, 160, 120), (150, 255, 150),
                 (255, 220, 120), (200, 130, 255), (130, 240, 230)]

ANGLE_STEP = 2 * math.pi / N_SECTORS
MAX_RADIUS = min(WIDTH, HEIGHT) // 2 - 40
ELLIPSE_Y = 0.9   # l'image Gaia est légèrement allongée ; ajuste si besoin


def sector_of_angle(angle: float) -> int:
    """Retourne l'index du secteur (0 à N_SECTORS-1) pour un angle en radians."""
    return int((angle % (2 * math.pi)) // ANGLE_STEP)


def sector_at(mx: int, my: int) -> int | None:
    """Retourne le secteur sous la souris, ou None si hors de la galaxie."""
    dx = mx - CENTER[0]
    dy = (my - CENTER[1]) / ELLIPSE_Y
    if math.hypot(dx, dy) > MAX_RADIUS:
        return None
    return sector_of_angle(math.atan2(dy, dx))


def wedge_polygon(a0: float, a1: float) -> list:
    """Polygone en forme de part de tarte entre deux angles."""
    points = [CENTER]
    steps = 48
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        points.append((CENTER[0] + MAX_RADIUS * math.cos(a),
                       CENTER[1] + MAX_RADIUS * math.sin(a) * ELLIPSE_Y))
    return points


def load_background():
    """Charge et met à l'échelle l'image Gaia ; None si absente."""
    if not os.path.exists(IMAGE_PATH):
        return None
    img = pygame.image.load(IMAGE_PATH).convert()
    return pygame.transform.smoothscale(img, (WIDTH, HEIGHT))


def generate_fallback_stars() -> list:
    """Étoiles procédurales, utilisées seulement si l'image est introuvable."""
    stars = []
    for _ in range(2400):
        r = random.uniform(0.05, 1.0) ** 0.7 * MAX_RADIUS
        a = random.uniform(0, 2 * math.pi) + r / MAX_RADIUS * 2.4
        a += random.gauss(0, 0.18)
        x = CENTER[0] + r * math.cos(a)
        y = CENTER[1] + r * math.sin(a) * ELLIPSE_Y
        stars.append((x, y, random.choice((1, 1, 1, 2, 2, 3)),
                      sector_of_angle(a)))
    return stars


def draw(screen, background, fallback_stars, selected, hovered, font, clock):
    screen.fill(BG_COLOR)

    # --- Fond : l'image Gaia (ou étoiles de secours) ---
    if background is not None:
        screen.blit(background, (0, 0))
    else:
        for x, y, size, sector in fallback_stars:
            pygame.draw.circle(screen, SECTOR_COLORS[sector], (int(x), int(y)), size)

    # --- Assombrir les secteurs non sélectionnés ---
    if selected is not None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for s in range(N_SECTORS):
            if s != selected:
                pygame.draw.polygon(overlay, (5, 5, 18, 175),
                                   wedge_polygon(s * ANGLE_STEP,
                                                 (s + 1) * ANGLE_STEP))
        screen.blit(overlay, (0, 0))

    # --- Lignes de séparation ---
    for i in range(N_SECTORS):
        a = i * ANGLE_STEP
        end = (CENTER[0] + MAX_RADIUS * math.cos(a),
               CENTER[1] + MAX_RADIUS * math.sin(a) * ELLIPSE_Y)
        pygame.draw.line(screen, (200, 200, 230), CENTER, end, 2)

    # --- Arc du secteur survolé (fin) ---
    if hovered is not None:
        rect = pygame.Rect(0, 0, 2 * MAX_RADIUS, int(2 * MAX_RADIUS * ELLIPSE_Y))
        rect.center = CENTER
        pygame.draw.arc(screen, SECTOR_COLORS[hovered], rect,
                        math.degrees(hovered * ANGLE_STEP),
                        math.degrees((hovered + 1) * ANGLE_STEP), 2)

    # --- Arc et nom du secteur sélectionné ---
    if selected is not None:
        rect = pygame.Rect(0, 0, 2 * MAX_RADIUS, int(2 * MAX_RADIUS * ELLIPSE_Y))
        rect.center = CENTER
        pygame.draw.arc(screen, SECTOR_COLORS[selected], rect,
                        math.degrees(selected * ANGLE_STEP),
                        math.degrees((selected + 1) * ANGLE_STEP), 4)
        label = font.render(SECTOR_NAMES[selected], True,
                           SECTOR_COLORS[selected])
        screen.blit(label, (CENTER[0] - label.get_width() // 2, 20))

    hint = font.render("Clic : sélectionner un secteur — Échap : quitter", True,
                      (220, 220, 235))
    screen.blit(hint, (10, HEIGHT - 30))

    clock.tick(60)
    pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Voie lactée Gaia — sélection de secteur")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 26)

    background = load_background()
    fallback_stars = None if background is not None else generate_fallback_stars()
    if background is None:
        print(f"Image '{IMAGE_PATH}' introuvable : étoiles procédurales.")

    selected = None
    hovered = None
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                hovered = sector_at(*event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                selected = sector_at(*event.pos)

        draw(screen, background, fallback_stars, selected, hovered, font, clock)

    pygame.quit()


if __name__ == "__main__":
    main()