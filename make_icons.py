"""Generate web/icon-192.png and web/icon-512.png for the PWA."""
import os
import pygame
import math

os.environ['SDL_RENDER_DRIVER'] = 'software'
os.environ['SDL_VIDEODRIVER']   = 'offscreen'
pygame.init()

def make_icon(size: int) -> pygame.Surface:
    s = size
    surf = pygame.Surface((s, s), pygame.SRCALPHA)

    # ── Background ──────────────────────────────────────────────────────────
    bg_color = (12, 9, 26)
    pygame.draw.rect(surf, bg_color, (0, 0, s, s), border_radius=s // 8)

    # Radial glow centre
    glow = pygame.Surface((s, s), pygame.SRCALPHA)
    for r in range(s // 2, 0, -4):
        a = max(0, int(60 * (1 - r / (s / 2))))
        pygame.draw.circle(glow, (120, 60, 200, a), (s // 2, s // 2), r)
    surf.blit(glow, (0, 0))

    cx = s // 2
    scale = s / 192  # normalise to 192-px design

    # ── Shield body ─────────────────────────────────────────────────────────
    sh_w = int(90 * scale)
    sh_h = int(110 * scale)
    sh_x = cx - sh_w // 2
    sh_y = int(38 * scale)

    # Shadow
    pygame.draw.polygon(surf, (20, 10, 50), [
        (sh_x + 4,          sh_y + 4),
        (sh_x + sh_w + 4,   sh_y + 4),
        (sh_x + sh_w + 4,   sh_y + int(70 * scale)),
        (cx + 4,            sh_y + sh_h + 4),
        (sh_x + 4,          sh_y + int(70 * scale)),
    ])
    # Main shield
    gold = (200, 160, 20)
    pygame.draw.polygon(surf, gold, [
        (sh_x,        sh_y),
        (sh_x + sh_w, sh_y),
        (sh_x + sh_w, sh_y + int(70 * scale)),
        (cx,          sh_y + sh_h),
        (sh_x,        sh_y + int(70 * scale)),
    ])
    # Inner fill
    pad = int(6 * scale)
    pygame.draw.polygon(surf, (18, 14, 36), [
        (sh_x + pad,        sh_y + pad),
        (sh_x + sh_w - pad, sh_y + pad),
        (sh_x + sh_w - pad, sh_y + int(68 * scale)),
        (cx,                sh_y + sh_h - pad),
        (sh_x + pad,        sh_y + int(68 * scale)),
    ])

    # ── Crossed swords ───────────────────────────────────────────────────────
    sword_col  = (220, 200, 100)
    guard_col  = (160, 130, 60)
    lw = max(2, int(3 * scale))

    def sword(x0, y0, x1, y1):
        pygame.draw.line(surf, sword_col, (int(x0), int(y0)), (int(x1), int(y1)), lw)
        # guard perpendicular
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length == 0:
            return
        nx, ny = -dy / length, dx / length
        gx = x0 + dx * 0.25
        gy = y0 + dy * 0.25
        gl = int(10 * scale)
        pygame.draw.line(surf, guard_col,
                         (int(gx - nx * gl), int(gy - ny * gl)),
                         (int(gx + nx * gl), int(gy + ny * gl)), lw)

    # Sword 1: top-left to bottom-right
    sword(cx - int(28 * scale), sh_y + int(12 * scale),
          cx + int(28 * scale), sh_y + int(88 * scale))
    # Sword 2: top-right to bottom-left
    sword(cx + int(28 * scale), sh_y + int(12 * scale),
          cx - int(28 * scale), sh_y + int(88 * scale))

    # ── Crown above shield ───────────────────────────────────────────────────
    crown_y  = int(22 * scale)
    crown_h  = int(18 * scale)
    crown_w  = int(44 * scale)
    crown_x  = cx - crown_w // 2
    crown_color = (255, 200, 40)

    # base bar
    pygame.draw.rect(surf, crown_color,
                     (crown_x, crown_y + crown_h // 2,
                      crown_w, crown_h // 2 + 2), border_radius=2)
    # three spikes
    spike_xs = [crown_x, cx - int(10 * scale), cx + int(10 * scale), crown_x + crown_w]
    spike_ys = [crown_y + crown_h // 2,
                crown_y,
                crown_y,
                crown_y + crown_h // 2]
    for i in range(3):
        bx = crown_x + int((i + 0.5) * crown_w / 3)
        pygame.draw.polygon(surf, crown_color, [
            (bx - int(5 * scale), crown_y + crown_h // 2),
            (bx,                  crown_y if i == 1 else crown_y + int(6 * scale)),
            (bx + int(5 * scale), crown_y + crown_h // 2),
        ])
    # jewels
    for i, jc in enumerate([(255, 60, 60), (60, 200, 255), (200, 255, 60)]):
        jx = crown_x + int((i + 0.5) * crown_w / 3)
        pygame.draw.circle(surf, jc, (int(jx), crown_y + crown_h - 3), max(2, int(3 * scale)))

    # ── Border ring ──────────────────────────────────────────────────────────
    pygame.draw.rect(surf, (90, 60, 160, 200), (0, 0, s, s),
                     width=max(2, int(3 * scale)), border_radius=s // 8)

    return surf


os.makedirs("web", exist_ok=True)
for sz in (192, 512):
    icon = make_icon(sz)
    path = f"web/icon-{sz}.png"
    pygame.image.save(icon, path)
    print(f"Saved {path}  ({sz}×{sz})")

pygame.quit()
