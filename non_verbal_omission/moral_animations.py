"""
moral_animations.py
====================
Four moral-scenario animations, fully matching the rendering style of
familiarization_trials.py / test_trials.py (PIL-based, 800×300, same
Renderer / Agent / Prop infrastructure).

Scenarios
---------
fam1  – Shape A (star) breaks cube → STAR punishes A  (removes star)
fam2  – Shape A (no star) moves toward cube; B (no star) blocks → STAR rewards B
test1 – Shape A (star) moves, B (star) fails to act, cube breaks → STAR punishes B
test2 – Shape A (star) moves, B (star) fails to act, cube breaks → STAR punishes A
"""

import math
import sys
import os
from PIL import Image, ImageDraw

# ── Re-use every constant and helper from the reference code ──────────────────
sys.path.insert(0, "/Users/sunny/.gemini/antigravity-ide/scratch/cause_fault_punish/code/experiments/non_verbal_experiment_animation_materials")
from familiarization_trials import (
    Color, Shape, Expression, Agent, Prop, Renderer, AnimationHelper,
    Timing, FPS, WIDTH, HEIGHT, CENTER_X, AGENT_SIZE, GROUND_Y,
    hex_to_rgb,
)

OUT = "/Users/sunny/.gemini/antigravity-ide/scratch/non_verbal_adults/non_verbal_omission"

# ─────────────────────────────────────────────────────────────────────────────
# BreakableCube  (identical to test_trials.py)
# ─────────────────────────────────────────────────────────────────────────────

class BreakableCube(Prop):
    def __init__(self, x, y):
        super().__init__("breakable_cube", x, y, True)
        self.state = "whole"
        self.fragments = []   # list of (x, y, dx, dy, rot)


def draw_breakable_cube(renderer_self, draw: ImageDraw.ImageDraw, cube: BreakableCube):
    if not cube.visible:
        return
    size = AGENT_SIZE
    base_color = "#868e96"
    hl = "#ced4da"
    crease = "#495057"

    if cube.state == "whole":
        left, top = cube.x - size / 2, cube.y - size
        right, bottom = cube.x + size / 2, cube.y
        draw.rectangle([left, top, right, bottom], fill=base_color)
        draw.polygon(
            [(left, top), (cube.x, top),
             (left + size * 0.2, top + size * 0.2), (left, top + size * 0.5)],
            fill=hl,
        )
        draw.line([cube.x, top, cube.x - size / 4, cube.y], fill=crease, width=2)
        draw.line([cube.x - size / 4, cube.y - size / 2,
                   right, cube.y - size / 3], fill=crease, width=2)
    else:
        fs = size / 3
        for fx, fy, _, _, rot in cube.fragments:
            rad = math.radians(rot)
            pts = [(-fs / 2, -fs / 2), (fs / 2, -fs / 4), (0, fs / 2)]
            rpts = []
            for px, py in pts:
                rx = px * math.cos(rad) - py * math.sin(rad) + fx
                ry = px * math.sin(rad) + py * math.cos(rad) + fy
                rpts.append((rx, ry))
            draw.polygon(rpts, fill=base_color)
            if len(rpts) >= 2:
                mx = (rpts[0][0] + rpts[1][0]) / 2
                my = (rpts[0][1] + rpts[1][1]) / 2
                draw.polygon([rpts[0], rpts[1], (mx, my + 2)], fill=hl)


# Monkey-patch Renderer once (guard against double-patching)
_original_render = Renderer.render

def _extended_render(self, agents, props, ag_scale=None):
    img = _original_render(self, agents, props, ag_scale)
    if ag_scale:
        return img
    draw = ImageDraw.Draw(img)
    for p in props:
        if p.type == "breakable_cube":
            draw_breakable_cube(self, draw, p)
    return img

Renderer.render = _extended_render


# ─────────────────────────────────────────────────────────────────────────────
# Shared physics helper
# ─────────────────────────────────────────────────────────────────────────────

def _shatter_cube(cube: BreakableCube):
    """Set cube to broken and give shards initial velocities."""
    cube.state = "broken"
    cx = cube.x
    cube.fragments = [
        (cx - 5,  230, -4,  -7,   0),
        (cx + 5,  220,  2, -12,  45),
        (cx + 15, 235,  6, -10,  90),
        (cx - 15, 245, -7,  -5,  15),
        (cx - 5,  250, -2, -15, 200),
        (cx + 5,  240,  1,  -7,  75),
        (cx + 15, 255,  9,  -6, -45),
        (cx - 10, 260, -1,  -4, 120),
        (cx,      265,  4,  -2,  60),
        (cx + 20, 260, 11,  -9, -90),
    ]


def _settle_shards(anim: AnimationHelper, cube: BreakableCube, max_frames=100):
    """Advance shard physics until they settle, snapping each frame."""
    gravity = 1.5
    active = True
    count = 0
    bound_y = GROUND_Y - 11
    while active and count < max_frames:
        active = False
        new_frags = []
        for fx, fy, dx, dy, rot in cube.fragments:
            nfx = fx + dx
            nfy = fy + dy
            ndy = dy + gravity
            nrot = rot + dx * 3
            if nfy >= bound_y:
                nfy = bound_y
                ndy = 0
                dx = dx * 0.8
                if abs(dx) < 0.5:
                    dx = 0
            if ndy != 0 or dx != 0:
                active = True
            new_frags.append((nfx, nfy, dx, ndy, nrot))
        cube.fragments = new_frags
        anim.snap()
        count += 1
    anim.pause(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Shared reward / punishment helpers  (matching familiarization_trials.py)
# ─────────────────────────────────────────────────────────────────────────────

def give_reward(anim: AnimationHelper, authority: Agent, target: Agent):
    """Authority floats down, gives star, target jumps happily."""
    anim.move(authority, target.x, target.y - 140, Timing.MOVE_DURATION)
    authority.expression = Expression.HAPPY
    authority.arm_target_r = (target.x, target.y - (AGENT_SIZE / 2) - 25)
    target.has_star = True
    target.expression = Expression.HAPPY
    anim.pause(0.5)
    anim.jump(target)
    anim.pause(0.5)
    anim.jump(target)
    anim.pause(0.5)
    authority.arm_target_r = None
    authority.expression = Expression.NEUTRAL
    anim.move(authority, CENTER_X, 60, Timing.MOVE_DURATION)
    anim.move(target, target.start_x, target.start_y, Timing.MOVE_DURATION)


def give_punishment(anim: AnimationHelper, authority: Agent, target: Agent, move_back=True):
    """Authority floats down, shakes in anger, removes star."""
    anim.move(authority, target.x, target.y - 140, Timing.MOVE_DURATION)
    authority.expression = Expression.ANGRY
    star_x = target.x
    star_y = target.y - (AGENT_SIZE / 2) - 25
    authority.arm_target_r = (star_x, star_y)
    anim.pause(0.2)

    start_gx = authority.x
    for i in range(25):
        off = 5 * math.sin(i * 1.5)
        authority.x = start_gx + off
        authority.arm_target_r = (star_x + off, star_y)
        anim.snap()
    authority.x = start_gx

    target.has_star = False
    target.expression = Expression.SAD
    authority.arm_target_r = None
    anim.pause(Timing.REWARD_DURATION)
    authority.expression = Expression.NEUTRAL
    anim.move(authority, CENTER_X, 60, Timing.MOVE_DURATION)
    if move_back:
        anim.move(target, target.start_x, target.start_y, Timing.MOVE_DURATION)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: move agent into cube, shatter, settle
# ─────────────────────────────────────────────────────────────────────────────

def ram_into_cube(anim: AnimationHelper, agent: Agent, cube: BreakableCube):
    """Agent rushes into cube then cube shatters."""
    target_x = cube.x - AGENT_SIZE / 2 - 5
    anim.move(agent, target_x, agent.y, 0.45)
    _shatter_cube(cube)
    _settle_shards(anim, cube)


# ─────────────────────────────────────────────────────────────────────────────
# FAM 1 — A (star) breaks cube → A punished
# ─────────────────────────────────────────────────────────────────────────────

def make_fam1(out_dir):
    r = Renderer()
    # A is a teal triangle on the far left
    A = Agent("A", Shape.TRIANGLE, Color.TEAL,  AGENT_SIZE, 227)
    authority = Agent("authority", Shape.STAR, Color.YELLOW, CENTER_X, 60)
    cube = BreakableCube(WIDTH - 100, GROUND_Y)

    all_agents = [A, authority]
    props = [cube]
    anim = AnimationHelper(r, all_agents, props)

    # Scene setup: A starts with a star
    A.has_star = True
    A.expression = Expression.NEUTRAL

    # Introduce: pause then A jumps to show itself
    anim.pause(1.5)
    anim.jump(A)
    anim.pause(1.0)

    # A moves toward cube aggressively
    ram_into_cube(anim, A, cube)

    # A looks surprised / guilty
    A.expression = Expression.NEUTRAL

    # Authority descends and punishes A
    give_punishment(anim, authority, A)

    path = os.path.join(out_dir, "fam1.gif")
    anim.frames[0].save(path, save_all=True, append_images=anim.frames[1:],
                        duration=1000 // FPS, loop=None)
    print(f"  Saved {path}")
    # Freeze frame
    anim.frames[-1].save(path.replace(".gif", "_end.png"))


# ─────────────────────────────────────────────────────────────────────────────
# FAM 2 — A (no star) charges, B (no star) blocks → B rewarded
# ─────────────────────────────────────────────────────────────────────────────

def make_fam2(out_dir):
    r = Renderer()
    # A starts on far left, B starts between A and the cube
    A = Agent("A", Shape.TRIANGLE, Color.RED,  AGENT_SIZE, 227)
    B = Agent("B", Shape.CIRCLE,   Color.TEAL, CENTER_X - 30, 227)
    authority = Agent("authority", Shape.STAR, Color.YELLOW, CENTER_X, 60)
    cube = BreakableCube(WIDTH - 100, GROUND_Y)

    all_agents = [A, B, authority]
    props = [cube]
    anim = AnimationHelper(r, all_agents, props)

    A.has_star = False
    B.has_star = False

    # Introduce scene
    anim.pause(1.5)
    anim.jump(A)
    anim.pause(0.5)
    anim.jump(B)
    anim.pause(1.0)

    # A starts rushing toward cube
    intercept_x = cube.x - AGENT_SIZE - 5   # just in front of cube
    a_stop_x    = B.x - AGENT_SIZE - 5       # A is blocked by B

    # A moves toward cube quickly
    anim.move(A, a_stop_x, 227, 0.4)

    # B slides in to block (moves toward cube, stopping between A and cube)
    block_x = B.x - AGENT_SIZE * 0.5
    anim.move(B, block_x, 227, 0.3)

    # A pushes but cube stays whole — B holds firm
    A.expression = Expression.NEUTRAL
    B.expression = Expression.NEUTRAL
    anim.pause(0.5)

    # B's arm reaches out to hold A back
    B.arm_target_l = (A.x + AGENT_SIZE / 2, A.y)
    A.expression = Expression.ANGRY
    anim.pause(0.8)
    B.arm_target_l = None

    # A backs off, cube intact
    A.expression = Expression.SAD
    anim.move(A, A.start_x, 227, Timing.MOVE_DURATION)
    A.expression = Expression.NEUTRAL

    # Authority rewards B
    B.expression = Expression.NEUTRAL
    give_reward(anim, authority, B)

    path = os.path.join(out_dir, "fam2.gif")
    anim.frames[0].save(path, save_all=True, append_images=anim.frames[1:],
                        duration=1000 // FPS, loop=None)
    print(f"  Saved {path}")
    anim.frames[-1].save(path.replace(".gif", "_end.png"))


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1 — A (star) charges, B (star) fails to act, cube breaks → B punished
# ─────────────────────────────────────────────────────────────────────────────

def make_test1(out_dir):
    r = Renderer()
    A = Agent("A", Shape.TRIANGLE, Color.TEAL,  AGENT_SIZE, 227)
    B = Agent("B", Shape.CIRCLE,   Color.RED,   CENTER_X - 30, 227)
    authority = Agent("authority", Shape.STAR, Color.YELLOW, CENTER_X, 60)
    cube = BreakableCube(WIDTH - 100, GROUND_Y)

    all_agents = [A, B, authority]
    props = [cube]
    anim = AnimationHelper(r, all_agents, props)

    A.has_star = True
    B.has_star = True

    # Introduce
    anim.pause(1.5)
    anim.jump(A)
    anim.pause(0.5)
    anim.jump(B)
    anim.pause(1.0)

    # A rushes toward cube — B does nothing (stays put)
    # We keep B frozen in place; only A moves
    a_stop_x = cube.x - AGENT_SIZE / 2 - 5
    anim.move(A, a_stop_x, 227, 0.45)

    # Cube shatters
    _shatter_cube(cube)
    _settle_shards(anim, cube)

    # A looks surprised / relieved; B looks guilty
    A.expression = Expression.NEUTRAL
    B.expression = Expression.NEUTRAL
    anim.pause(0.5)

    # Authority punishes B (the bystander who failed to act)
    give_punishment(anim, authority, B)

    path = os.path.join(out_dir, "test1.gif")
    anim.frames[0].save(path, save_all=True, append_images=anim.frames[1:],
                        duration=1000 // FPS, loop=None)
    print(f"  Saved {path}")
    anim.frames[-1].save(path.replace(".gif", "_end.png"))


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2 — A (star) charges, B (star) fails to act, cube breaks → A punished
# ─────────────────────────────────────────────────────────────────────────────

def make_test2(out_dir):
    r = Renderer()
    A = Agent("A", Shape.TRIANGLE, Color.TEAL,  AGENT_SIZE, 227)
    B = Agent("B", Shape.CIRCLE,   Color.RED,   CENTER_X - 30, 227)
    authority = Agent("authority", Shape.STAR, Color.YELLOW, CENTER_X, 60)
    cube = BreakableCube(WIDTH - 100, GROUND_Y)

    all_agents = [A, B, authority]
    props = [cube]
    anim = AnimationHelper(r, all_agents, props)

    A.has_star = True
    B.has_star = True

    # Introduce
    anim.pause(1.5)
    anim.jump(A)
    anim.pause(0.5)
    anim.jump(B)
    anim.pause(1.0)

    # A rushes, B stays frozen
    a_stop_x = cube.x - AGENT_SIZE / 2 - 5
    anim.move(A, a_stop_x, 227, 0.45)

    _shatter_cube(cube)
    _settle_shards(anim, cube)

    # B stays neutral; A looks guilty
    B.expression = Expression.NEUTRAL
    A.expression = Expression.NEUTRAL
    anim.pause(0.5)

    # Authority punishes A (the direct cause)
    give_punishment(anim, authority, A, move_back=False)

    path = os.path.join(out_dir, "test2.gif")
    anim.frames[0].save(path, save_all=True, append_images=anim.frames[1:],
                        duration=1000 // FPS, loop=None)
    print(f"  Saved {path}")
    anim.frames[-1].save(path.replace(".gif", "_end.png"))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print("Rendering FAM 1 — A breaks cube, A punished...")
    make_fam1(OUT)
    print("Rendering FAM 2 — B blocks A, B rewarded...")
    make_fam2(OUT)
    print("Rendering TEST 1 — B fails to act, B punished...")
    make_test1(OUT)
    print("Rendering TEST 2 — B fails to act, A punished...")
    make_test2(OUT)
    print("\nAll done! GIFs and freeze-frames saved to:", OUT)
