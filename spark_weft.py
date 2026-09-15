#!/usr/bin/env python3
"""Spark Weft — neon loom-shuttle arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/SPARK_WEFT_ElbowOS.mp4")
TITLE, HANDLE = "SPARK WEFT", "x.com/ElbowOS"

BG = (12, 6, 22)
INK = (36, 14, 52)
MAG = (255, 64, 168)
PINK = (255, 140, 210)
CYAN = (80, 240, 255)
LIME = (180, 255, 70)
GOLD = (255, 210, 70)
VIO = (170, 110, 255)
WHITE = (250, 246, 255)
HOT = (255, 70, 90)
COLS = (MAG, CYAN, LIME, GOLD, VIO)


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.display.quit()
            pygame.display.init()
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        self.font_lg = pygame.font.SysFont("DejaVu Sans", 56, bold=True)
        self.font = pygame.font.SysFont("DejaVu Sans", 36, bold=True)
        self.font_sm = pygame.font.SysFont("DejaVu Sans", 26)
        self.clock = pygame.time.Clock()
        self.lanes = 5
        self.lane_x = [180 + i * 180 for i in range(self.lanes)]
        self.lane = 2
        self.x = self.lane_x[self.lane]
        self.y = 1540
        self.score = self.combo = self.t = self.flash = self.bind = 0
        self.threads, self.snags, self.sparks, self.stitches = [], [], [], []
        self.stars = [[random.randint(0, W), random.randint(0, H),
                       random.uniform(0.4, 1.8), random.choice(COLS)]
                      for _ in range(70)]
        self.reset()

    def reset(self):
        self.lives = 3
        self.combo = 0
        self.lane = 2
        self.x = self.lane_x[self.lane]
        self.thr_cd = 8
        self.snag_cd = 28
        self.target = [random.choice(COLS) for _ in range(self.lanes)]

    def burst(self, x, y, col, n=14):
        for _ in range(n):
            a = random.uniform(0, 6.2832)
            sp = random.uniform(2.0, 11)
            self.sparks.append([x, y, math.cos(a) * sp, math.sin(a) * sp, 16, col])

    def spawn_thread(self):
        i = random.randrange(self.lanes)
        self.threads.append([i, -40, self.target[i] if random.random() < 0.62 else random.choice(COLS)])

    def spawn_snag(self):
        i = random.randrange(self.lanes)
        self.snags.append([i, -50, random.uniform(0.9, 1.3)])

    def do_bind(self):
        if self.bind > 6:
            return
        self.bind = 16
        hits = 0
        for th in list(self.threads):
            if th[0] == self.lane and 1320 < th[1] < 1680:
                if th[2] == self.target[self.lane]:
                    self.combo += 1
                    self.score += 12 + self.combo * 3
                    hits += 1
                    self.burst(self.lane_x[th[0]], th[1], th[2], 18)
                    self.stitches.append([th[0], th[1], 20, th[2]])
                    self.threads.remove(th)
                    if random.random() < 0.45:
                        self.target[self.lane] = random.choice(COLS)
                else:
                    self.combo = 0
                    self.flash = 8
                    self.burst(self.lane_x[th[0]], th[1], HOT, 10)
                    self.threads.remove(th)
        if hits == 0:
            self.score += 1

    def hit_check(self):
        for th in list(self.threads):
            if th[1] > 1760:
                self.threads.remove(th)
                self.combo = 0
        for s in list(self.snags):
            if s[0] == self.lane and abs(s[1] - self.y) < 48:
                self.lives -= 1
                self.combo = 0
                self.flash = 10
                self.burst(self.x, self.y, HOT, 22)
                self.snags.remove(s)
                if self.lives <= 0:
                    self.score = max(0, self.score - 18)
                    self.reset()

    def autoplay(self):
        best, best_d = self.lane, 9e9
        for th in self.threads:
            if th[2] == self.target[th[0]] and -20 < th[1] < 1600:
                d = (1600 - th[1]) + abs(th[0] - self.lane) * 90
                if d < best_d:
                    best, best_d = th[0], d
        threats = [s for s in self.snags if abs(s[1] - self.y) < 280]
        if threats and any(s[0] == best for s in threats):
            for cand in (best - 1, best + 1, best - 2, best + 2):
                if 0 <= cand < self.lanes and not any(s[0] == cand for s in threats):
                    best = cand
                    break
        if best > self.lane:
            self.lane += 1
        elif best < self.lane:
            self.lane -= 1
        ready = any(th[0] == self.lane and 1340 < th[1] < 1660 and th[2] == self.target[self.lane]
                    for th in self.threads)
        near_snag = any(s[0] == self.lane and abs(s[1] - self.y) < 110 for s in self.snags)
        if ready and not near_snag:
            self.do_bind()
        elif self.t % 26 == 0 and any(th[0] == self.lane and 1380 < th[1] < 1620 for th in self.threads):
            self.do_bind()

    def tick(self):
        self.t += 1
        self.flash = max(0, self.flash - 1)
        self.bind = max(0, self.bind - 1)
        want = self.lane_x[self.lane]
        self.x += (want - self.x) * 0.28
        flow = 13 + min(8, self.t / 90)
        self.thr_cd -= 1
        self.snag_cd -= 1
        if self.thr_cd <= 0:
            self.spawn_thread()
            self.thr_cd = max(6, 14 - self.t // 90)
        if self.snag_cd <= 0:
            self.spawn_snag()
            self.snag_cd = max(16, 30 - self.t // 80)
        for th in self.threads:
            th[1] += flow + math.sin(self.t * 0.09 + th[0]) * 0.6
        for s in self.snags:
            s[1] += flow * s[2]
        self.threads = [th for th in self.threads if th[1] < H + 40]
        self.snags = [s for s in self.snags if s[1] < H + 40]
        self.hit_check()
        for sp in self.sparks:
            sp[0] += sp[2]
            sp[1] += sp[3]
            sp[4] -= 1
        self.sparks = [sp for sp in self.sparks if sp[4] > 0]
        for st in self.stitches:
            st[2] -= 1
        self.stitches = [st for st in self.stitches if st[2] > 0]
        for star in self.stars:
            star[1] += star[2]
            if star[1] > H:
                star[1] = -4
                star[0] = random.randint(0, W)

    def draw(self, surf):
        surf.fill(BG)
        for i in range(24):
            y0 = (i * 90 + int(self.t * 3)) % (H + 90) - 40
            pygame.draw.rect(surf, INK, (0, y0, W, 10))
        for star in self.stars:
            pygame.draw.circle(surf, star[3], (int(star[0]), int(star[1])), 2)
        top, bot = 220, 1720
        for i, lx in enumerate(self.lane_x):
            col = self.target[i]
            pygame.draw.line(surf, (40, 20, 60), (lx, top), (lx, bot), 10)
            pygame.draw.line(surf, col, (lx, top), (lx, bot), 3)
            pygame.draw.circle(surf, col, (lx, top - 10), 16)
            pygame.draw.circle(surf, WHITE, (lx, top - 10), 6)
        for th in self.threads:
            lx, yy = self.lane_x[th[0]], int(th[1])
            pygame.draw.circle(surf, th[2], (lx, yy), 18)
            pygame.draw.circle(surf, WHITE, (lx - 4, yy - 5), 5)
            pygame.draw.line(surf, th[2], (lx - 22, yy), (lx + 22, yy), 3)
        for s in self.snags:
            lx, yy = self.lane_x[s[0]], int(s[1])
            pygame.draw.polygon(surf, HOT, [(lx, yy - 18), (lx + 16, yy + 10), (lx - 16, yy + 10)])
            pygame.draw.circle(surf, (40, 8, 16), (lx, yy + 2), 6)
        for st in self.stitches:
            lx = self.lane_x[st[0]]
            pygame.draw.line(surf, st[3], (lx - 40, int(st[1])), (lx + 40, int(st[1])), 6)
        for sp in self.sparks:
            pygame.draw.circle(surf, sp[5], (int(sp[0]), int(sp[1])), max(2, sp[4] // 4))
        bx, by = int(self.x), int(self.y)
        body = [(bx - 46, by + 10), (bx + 46, by + 10), (bx + 28, by + 36), (bx - 28, by + 36)]
        pygame.draw.polygon(surf, (70, 20, 90), body)
        pygame.draw.polygon(surf, MAG, body, 3)
        pygame.draw.ellipse(surf, CYAN, (bx - 28, by - 22, 56, 34))
        pygame.draw.ellipse(surf, WHITE, (bx - 10, by - 14, 14, 10))
        if self.bind:
            pygame.draw.circle(surf, PINK, (bx, by), 18 + (16 - self.bind) * 3, 2)
        if self.flash:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((255, 40, 80, 60))
            surf.blit(ov, (0, 0))
        title = self.font_lg.render(TITLE, True, PINK)
        surf.blit(title, title.get_rect(center=(W // 2, 84)))
        sub = self.font_sm.render(HANDLE, True, CYAN)
        surf.blit(sub, sub.get_rect(center=(W // 2, 146)))
        sc = self.font.render(f"SCORE  {self.score}", True, WHITE)
        lv = self.font.render(f"LIVES  {'\u25c6' * max(0, self.lives)}", True, HOT)
        cb = self.font_sm.render(f"COMBO  x{self.combo}", True, LIME)
        surf.blit(sc, sc.get_rect(center=(W // 2, H - 168)))
        surf.blit(lv, lv.get_rect(center=(W // 2, H - 108)))
        surf.blit(cb, cb.get_rect(center=(W // 2, H - 58)))

    def play_interactive(self):
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                    self.reset()
                    self.score = 0
                elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_LEFT, pygame.K_a):
                    self.lane = max(0, self.lane - 1)
                elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RIGHT, pygame.K_d):
                    self.lane = min(self.lanes - 1, self.lane + 1)
                elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    self.do_bind()
            self.tick()
            self.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def record(self):
        frames = FPS * SECS
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart",
            OUT,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        canvas = pygame.Surface((W, H))
        try:
            for i in range(frames):
                self.autoplay()
                self.tick()
                self.draw(canvas)
                proc.stdin.write(pygame.image.tostring(canvas, "RGB"))
                if i % 30 == 0:
                    print(f"frame {i}/{frames}", flush=True)
        finally:
            proc.stdin.close()
            err = proc.stderr.read().decode("utf-8", "ignore")
            rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1200:]}")
        print("wrote", OUT)
        pygame.quit()


def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()


if __name__ == "__main__":
    main()
