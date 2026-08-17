"""
Single-character punishment warmup trials.

Reuses the exact rendering primitives and punishment-action choreography from
familiarization_trials.py (trash-bin, tower-block, flower scenes), but:
  (1) features a SINGLE character (the pink circle) instead of two agents,
  (2) places each scene at a different canvas position (trash=left,
      tower=center, flower=right) instead of always at center,
  (3) the character is drawn EYES-ONLY (no mouth/eyebrows), matching the
      rest of the redesigned study; the star authority keeps its expressions.

Outputs: warmup_punish_left.gif, warmup_punish_center.gif, warmup_punish_right.gif
"""
import math
from PIL import Image
from familiarization_trials import (
    Color, Shape, Expression, Timing, FPS, WIDTH, HEIGHT, CENTER_X,
    AGENT_SIZE, GROUND_Y, Agent, Prop, Renderer, AnimationHelper,
)


class SingleCharRenderer(Renderer):
    def draw_face(self, draw, x, y, expression, scale=1.0, eyes_only=False):
        fc = "#495057"
        ex_off, ey_top, ey_bot = 10 * scale, 11 * scale, 3 * scale
        draw.ellipse([x - ex_off, y - ey_top, x - (6 * scale), y - ey_bot], fill=fc)
        draw.ellipse([x + (6 * scale), y - ey_top, x + ex_off, y - ey_bot], fill=fc)
        if eyes_only:
            return
        if expression == Expression.NEUTRAL:
            draw.line([x - 6 * scale, y + 7 * scale, x + 6 * scale, y + 7 * scale], fill=fc, width=max(1, int(3 * scale)))
        elif expression == Expression.HAPPY:
            draw.arc([x - 8 * scale, y + 2 * scale, x + 8 * scale, y + 13 * scale], 0, 180, fill=fc, width=max(1, int(3 * scale)))
        elif expression == Expression.SAD:
            draw.arc([x - 8 * scale, y + 4 * scale, x + 8 * scale, y + 15 * scale], 180, 360, fill=fc, width=max(1, int(3 * scale)))
        elif expression == Expression.ANGRY:
            draw.line([x - 14 * scale, y - 17 * scale, x - 4 * scale, y - 11 * scale], fill=fc, width=max(1, int(3 * scale)))
            draw.line([x + 14 * scale, y - 17 * scale, x + 4 * scale, y - 11 * scale], fill=fc, width=max(1, int(3 * scale)))
            draw.arc([x - 8 * scale, y + 4 * scale, x + 8 * scale, y + 15 * scale], 180, 360, fill=fc, width=max(1, int(3 * scale)))

    def draw_agent(self, draw, agent):
        r = AGENT_SIZE / 2
        ac = "#495057"

        if agent.shape == Shape.TRIANGLE:
            root_lx, root_rx = agent.x - r / 2, agent.x + r / 2
        elif agent.shape == Shape.STAR:
            root_lx, root_rx = agent.x - 15, agent.x + 15
        else:
            root_lx, root_rx = agent.x - r + 8, agent.x + r - 8
        root_y = agent.y
        if agent.name == "authority":
            if agent.arm_target_r:
                self.draw_wand(draw, root_rx, root_y, agent.arm_target_r[0], agent.arm_target_r[1])
            else:
                self.draw_wand(draw, root_rx, root_y, root_rx + 20, root_y - 25)
            if agent.arm_target_l:
                draw.line([root_lx, root_y, agent.arm_target_l[0], agent.arm_target_l[1]], fill=ac, width=4)
            else:
                draw.line([root_lx, root_y, root_lx - 15, root_y + 20], fill=ac, width=4)
        else:
            if agent.arm_target_l:
                draw.line([root_lx, root_y, agent.arm_target_l[0], agent.arm_target_l[1]], fill=ac, width=4)
            else:
                draw.line([root_lx, root_y, root_lx - 15, root_y + 20], fill=ac, width=4)
            if agent.arm_target_r:
                draw.line([root_rx, root_y, agent.arm_target_r[0], agent.arm_target_r[1]], fill=ac, width=4)
            else:
                draw.line([root_rx, root_y, root_rx + 15, root_y + 20], fill=ac, width=4)

        color = agent.color.value
        hl = self.get_highlight(color)

        if agent.shape == Shape.CIRCLE:
            self.draw_sphere_3d(draw, agent.x, agent.y, r, color)
        elif agent.shape == Shape.SQUARE:
            draw.rectangle([agent.x - r, agent.y - r, agent.x + r, agent.y + r], fill=color)
            draw.polygon([(agent.x - r, agent.y - r), (agent.x, agent.y - r), (agent.x - r * 0.2, agent.y - r * 0.2), (agent.x - r, agent.y)], fill=hl)
        elif agent.shape == Shape.TRIANGLE:
            draw.polygon([(agent.x - r, agent.y + r), (agent.x + r, agent.y + r), (agent.x, agent.y - r)], fill=color)
            draw.polygon([(agent.x, agent.y - r), (agent.x - r, agent.y + r), (agent.x - r * 0.6, agent.y + r * 0.8), (agent.x - r * 0.1, agent.y - r * 0.6)], fill=hl)
        elif agent.shape == Shape.STAR:
            self.draw_star(draw, agent.x, agent.y, r * 1.5 if agent.name == "authority" else r, color)

        face_y = agent.y + (12 if agent.shape == Shape.TRIANGLE else 0)
        f_scale = 0.75 if agent.shape == Shape.STAR else 1.0
        eyes_only = (agent.name != "authority")
        self.draw_face(draw, agent.x, face_y, agent.expression, scale=f_scale, eyes_only=eyes_only)
        if agent.has_star:
            self.draw_star(draw, agent.x, agent.y - r - 25)


def setup_scene(scene_name, scene_x, props):
    props.clear()
    if scene_name == "trash":
        center_prop = Prop("bin", scene_x, 245, True)
    elif scene_name == "tower":
        center_prop = Prop("tower_base", scene_x, 230, True)
        props.append(Prop("block", scene_x, 185, True))
    elif scene_name == "flower":
        center_prop = Prop("flower", scene_x, 230, True)
    else:
        raise ValueError(scene_name)
    props.append(center_prop)
    return center_prop


# Anticipatory-cue timing constants (David's post-lab-meeting spec):
#   very shortly after the outcome -> brief angry+shake+sound, centered
#   -> star stops shaking, stays angry+centered -> 2-2.5s pause (the MAIN
#   anticipatory-looking window) -> THEN move over and take the star.
PRE_SHAKE_PAUSE = 0.3     # "very shortly after the outcome"
SHAKE_DURATION = 0.48     # "briefly shakes" (12 frames @ 25fps)
ANTICIPATORY_PAUSE = 2.5  # main anticipatory-looking window (2-2.5s range, upper bound)


def anticipatory_cue(anim, authority):
    """Star stays put at its home/centered position (CENTER_X, 60): goes
    angry, briefly shakes (sound cue fires at shake onset), then holds
    still -- angry and centered -- for ANTICIPATORY_PAUSE seconds. Returns
    the frame index at which the shake (and sound cue) begins, so the
    caller can compute the matching ms offset for the JS audio trigger.
    """
    anim.pause(PRE_SHAKE_PAUSE)
    sound_cue_frame = len(anim.frames)
    authority.expression = Expression.ANGRY
    start_gx = authority.x
    shake_frames = int(SHAKE_DURATION * FPS)
    for i in range(shake_frames):
        authority.x = start_gx + 4 * math.sin(i * 1.8)
        anim.snap()
    authority.x = start_gx
    anim.pause(ANTICIPATORY_PAUSE)
    return sound_cue_frame


def give_punishment(anim, mischief, authority):
    # authority is already angry-faced and centered (anticipatory_cue() ran
    # just before this), so it only needs to move in and take the star.
    anim.move(authority, mischief.x, mischief.y - 140, Timing.MOVE_DURATION)
    authority.arm_target_r = (mischief.x, mischief.y - (AGENT_SIZE / 2) - 25)
    start_gx = authority.x
    for i in range(15):
        authority.x = start_gx + 5 * math.sin(i * 1.5)
        anim.snap()
    authority.x = start_gx
    mischief.has_star, mischief.expression = False, Expression.SAD
    anim.pause(Timing.REWARD_DURATION)
    authority.arm_target_l = authority.arm_target_r = None
    authority.expression = Expression.NEUTRAL
    anim.move(authority, CENTER_X, 60, Timing.MOVE_DURATION)
    # mischief is already resting at its home/punish-moment position (the
    # punish-phase functions now return it directly to mischief.start_x
    # before calling give_punishment), so no further move is needed here.


def trash_punish_phase(anim, props, center_prop, mischief, authority, scene_x):
    trash = Prop("trash", center_prop.x, 175, False)
    props.append(trash)
    anim.pause(0.8)

    stop_x = center_prop.x - 45 if mischief.start_x < scene_x else center_prop.x + 45
    anim.move(mischief, stop_x, 230, Timing.MOVE_DURATION)

    if mischief.start_x < scene_x:
        mischief.arm_target_r = (center_prop.x, 185)
    else:
        mischief.arm_target_l = (center_prop.x, 185)
    anim.pause(0.5)
    trash.visible = True
    trash.x = center_prop.x
    trash.y = 185
    anim.snap()

    target_x = mischief.x + (-45 if mischief.start_x < scene_x else 45)
    target_y = mischief.y - 30

    frames = 8
    ty_start, tx_start = trash.y, trash.x
    for i in range(1, frames + 1):
        trash.x = tx_start + (target_x - tx_start) * (i / frames)
        trash.y = ty_start + (target_y - ty_start) * (i / frames)
        if i < frames / 2:
            if mischief.start_x < scene_x:
                mischief.arm_target_r = (trash.x, trash.y)
            else:
                mischief.arm_target_l = (trash.x, trash.y)
        else:
            if mischief.start_x < scene_x:
                mischief.arm_target_l = (trash.x, trash.y)
            else:
                mischief.arm_target_r = (trash.x, trash.y)
        anim.snap()

    anim.pause(0.2)

    return_x = mischief.start_x   # punish-moment position == start/home position
    c_side = "left" if mischief.start_x < scene_x else "right"
    anim.move(mischief, return_x, 227, Timing.MOVE_DURATION, carry_prop=trash, carry_side=c_side)

    ty_start = trash.y
    for i in range(12):
        trash.y = min(250, ty_start + i * 6)
        if c_side == "left":
            mischief.arm_target_l = (trash.x, trash.y)
        else:
            mischief.arm_target_r = (trash.x, trash.y)
        anim.snap()

    mischief.arm_target_l = mischief.arm_target_r = None

    sound_frame = anticipatory_cue(anim, authority)
    give_punishment(anim, mischief, authority)
    if trash in props:
        props.remove(trash)
    return sound_frame


def tower_punish_phase(anim, props, center_prop, mischief, authority, scene_x):
    block = [p for p in props if p.type == "block"][0]
    anim.pause(0.8)

    stop_x = center_prop.x - 45 if mischief.start_x < scene_x else center_prop.x + 45
    anim.move(mischief, stop_x, 230, Timing.MOVE_DURATION)

    if mischief.start_x < scene_x:
        mischief.arm_target_r = (center_prop.x, 185)
    else:
        mischief.arm_target_l = (center_prop.x, 185)
    anim.pause(0.5)
    anim.snap()

    target_x = mischief.x + (-45 if mischief.start_x < scene_x else 45)
    target_y = mischief.y - 30

    frames = 8
    ty_start, tx_start = block.y, block.x
    for i in range(1, frames + 1):
        block.x = tx_start + (target_x - tx_start) * (i / frames)
        block.y = ty_start + (target_y - ty_start) * (i / frames)
        if i < frames / 2:
            if mischief.start_x < scene_x:
                mischief.arm_target_r = (block.x, block.y)
            else:
                mischief.arm_target_l = (block.x, block.y)
        else:
            if mischief.start_x < scene_x:
                mischief.arm_target_l = (block.x, block.y)
            else:
                mischief.arm_target_r = (block.x, block.y)
        anim.snap()

    anim.pause(0.2)

    return_x = mischief.start_x   # punish-moment position == start/home position
    c_side = "left" if mischief.start_x < scene_x else "right"
    anim.move(mischief, return_x, 227, Timing.MOVE_DURATION, carry_prop=block, carry_side=c_side)

    ty_start = block.y
    for i in range(12):
        block.y = min(245, ty_start + i * 6)
        if c_side == "left":
            mischief.arm_target_l = (block.x, block.y)
        else:
            mischief.arm_target_r = (block.x, block.y)
        anim.snap()

    mischief.arm_target_l = mischief.arm_target_r = None

    sound_frame = anticipatory_cue(anim, authority)
    give_punishment(anim, mischief, authority)
    if block in props:
        props.remove(block)
    return sound_frame


def flower_punish_phase(anim, props, center_prop, mischief, authority, scene_x):
    flower = center_prop
    anim.pause(0.8)

    # Walk directly onto/over the flower (single "beside the prop" resting
    # position -- no intermediate waypoint), then stomp.
    anim.move(mischief, flower.x, 227, Timing.MOVE_DURATION)

    anim.move(mischief, flower.x, 220, 0.4)
    anim.move(mischief, flower.x, 227, 0.2)
    flower.expression = Expression.SAD
    anim.pause(0.4)

    return_x = mischief.start_x   # punish-moment position == start/home position
    anim.move(mischief, return_x, 227, Timing.MOVE_DURATION)

    sound_frame = anticipatory_cue(anim, authority)
    give_punishment(anim, mischief, authority)
    return sound_frame


def dither(frames):
    out = []
    for i, f in enumerate(frames):
        f = f.copy()
        f.putpixel((0, 0), (255, 255, 255) if i % 2 == 0 else (254, 254, 254))
        out.append(f)
    return out


# The pink circle only ever rests at TWO x-positions in each animation:
#   (1) home_x == the punish-moment position (start of the clip, and where
#       it settles again right before the authority swoops in and removes
#       its star -- the punish-phase functions now return it to exactly
#       mischief.start_x, so these two coincide by construction), and
#   (2) beside/over the prop (trash bin / tower / flower) while it commits
#       the bad action.
# home_x values are set directly to the desired punish-moment targets:
#   left   = 200  (200 px left  of canvas center)
#   center = 400  (exact canvas center, directly under the authority)
#   right  = 600  (200 px right of canvas center -- exact mirror of "left")
# scene_x (the prop position) is kept close (70px) to home_x on the correct
# side, so each prop sits right next to the character's home/punish-moment
# spot rather than far across the canvas.
SCENES = {
    "left":   dict(scene_name="tower",  scene_x=270, home_x=200),
    "center": dict(scene_name="trash",  scene_x=330, home_x=400),
    "right":  dict(scene_name="flower", scene_x=530, home_x=600),
}


def build_warmup(position):
    cfg = SCENES[position]
    scene_name, scene_x, home_x = cfg["scene_name"], cfg["scene_x"], cfg["home_x"]

    renderer = SingleCharRenderer()
    mischief = Agent("mischief", Shape.CIRCLE, Color.PINK, home_x, 227)
    authority = Agent("authority", Shape.STAR, Color.YELLOW, CENTER_X, 60)
    props = []
    anim = AnimationHelper(renderer, [mischief, authority], props)

    center_prop = setup_scene(scene_name, scene_x, props)
    mischief.has_star = True

    anim.pause(1.0)
    anim.jump(mischief)
    anim.pause(1.0)

    if scene_name == "trash":
        sound_frame = trash_punish_phase(anim, props, center_prop, mischief, authority, scene_x)
    elif scene_name == "tower":
        sound_frame = tower_punish_phase(anim, props, center_prop, mischief, authority, scene_x)
    elif scene_name == "flower":
        sound_frame = flower_punish_phase(anim, props, center_prop, mischief, authority, scene_x)

    anim.pause(1.0)

    frames = dither(anim.frames)
    out_name = f"warmup_punish_{position}.gif"
    frames[0].save(out_name, save_all=True, append_images=frames[1:], duration=1000 // FPS, loop=1, optimize=False)
    dur_ms = len(frames) * (1000 // FPS)
    sound_ms = sound_frame * (1000 // FPS)
    print(f"{out_name}: {len(frames)} frames, {dur_ms} ms; sound cue at frame {sound_frame} = {sound_ms} ms")
    return out_name, dur_ms, sound_ms


if __name__ == "__main__":
    import os
    import shutil
    import json

    total = {}
    sound_offsets = {}
    for pos in ["left", "center", "right"]:
        name, dur, sound_ms = build_warmup(pos)
        total[pos] = dur
        sound_offsets[pos] = sound_ms

    dest_dir = "../materials/"
    if os.path.exists(dest_dir):
        for pos in ["left", "center", "right"]:
            fn = f"warmup_punish_{pos}.gif"
            shutil.copy(fn, os.path.join(dest_dir, fn))
            print(f"  Copied {fn} -> {dest_dir}")
        with open(os.path.join(dest_dir, "warmup_timing.json"), "w") as fh:
            json.dump({"durations_ms": total, "sound_cue_offset_ms": sound_offsets}, fh, indent=2)
        print("  Wrote warmup_timing.json")

    print("Durations (ms):", total)
    print("Sound cue offsets (ms):", sound_offsets)
