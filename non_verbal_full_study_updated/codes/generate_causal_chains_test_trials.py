import math
from PIL import ImageDraw
from familiarization_trials import (
    Color, Shape, Expression, Agent, Prop, Renderer, AnimationHelper,
    Timing, FPS, WIDTH, HEIGHT, CENTER_X, AGENT_SIZE, GROUND_Y
)

# ==========================================
# CUBE & PHYSICS LOGIC
# ==========================================

class BreakableCube(Prop):
    def __init__(self, x, y):
        super().__init__("breakable_cube", x, y, True)
        self.state = "whole"
        # fragments list of (x, y, dx, dy, rot)
        self.fragments = []


def draw_breakable_cube(self, draw: ImageDraw.ImageDraw, cube: BreakableCube):
    if not cube.visible: return
    # Size roughly fits well with AGENT_SIZE scaled geometry
    size = AGENT_SIZE
    base_color = "#868e96"
    hl = "#ced4da"
    crease = "#495057"

    if cube.state == "whole":
        # Draw solid block resting on the ground
        left, top, right, bottom = cube.x - size/2, cube.y - size, cube.x + size/2, cube.y
        draw.rectangle([left, top, right, bottom], fill=base_color)
        draw.polygon([(left, top), (cube.x, top), (left+size*0.2, top+size*0.2), (left, top+size*0.5)], fill=hl)
        # Internal crease lines
        draw.line([cube.x, top, cube.x - size/4, cube.y], fill=crease, width=2)
        draw.line([cube.x - size/4, cube.y - size/2, right, cube.y - size/3], fill=crease, width=2)
    else:
        # Draw dynamic ballistic shards
        fs = size / 3  # finer shards
        for fx, fy, _, _, rot in cube.fragments:
            rad = math.radians(rot)
            # define a small triangle shard
            pts = [(-fs/2, -fs/2), (fs/2, -fs/4), (0, fs/2)]
            rotated_pts = []
            for px, py in pts:
                rx = px * math.cos(rad) - py * math.sin(rad) + fx
                ry = px * math.sin(rad) + py * math.cos(rad) + fy
                rotated_pts.append((rx, ry))
            draw.polygon(rotated_pts, fill=base_color)
            if len(rotated_pts) >= 2:
                mx = (rotated_pts[0][0] + rotated_pts[1][0])/2
                my = (rotated_pts[0][1] + rotated_pts[1][1])/2
                draw.polygon([rotated_pts[0], rotated_pts[1], (mx, my+2)], fill=hl)

# Inject support for BreakableCube into the Renderer
original_render = Renderer.render

def extended_render(self, agents, props, ag_scale=None):
    img = original_render(self, agents, props, ag_scale)
    if ag_scale: return img

    draw = ImageDraw.Draw(img)
    for p in props:
        if p.type == "breakable_cube":
            draw_breakable_cube(self, draw, p)
    return img

# Monkey-patch Renderer with our updated render handler
Renderer.render = extended_render

# ==========================================
# EYES-ONLY CHARACTERS (star authority keeps its expressions)
# ==========================================
# Matches the eyes-only redesign used everywhere else in the study: agents
# other than "authority" are drawn with eyes only (no mouth/eyebrows).

def eyes_only_draw_face(self, draw, x, y, expression, scale=1.0, eyes_only=False):
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


def eyes_only_draw_agent(self, draw, agent):
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
        self.draw_star(draw, agent.x, agent.y, r * 1.5 if agent.name == "authority" else r, color, rotation=getattr(agent, 'shake_rotation', 0.0))

    face_y = agent.y + (12 if agent.shape == Shape.TRIANGLE else 0)
    f_scale = 0.75 if agent.shape == Shape.STAR else 1.0
    eyes_only = (agent.name != "authority")
    self.draw_face(draw, agent.x, face_y, agent.expression, scale=f_scale, eyes_only=eyes_only)
    if agent.has_star:
        self.draw_star(draw, agent.x, agent.y - r - 25)


Renderer.draw_face = eyes_only_draw_face
Renderer.draw_agent = eyes_only_draw_agent


def dither(frames):
    """Toggle one corner pixel between two near-white values every other
    frame so Pillow's GIF encoder can never treat two frames as byte-
    identical and collapse them -- see the comment at its call site."""
    out = []
    for i, f in enumerate(frames):
        f = f.copy()
        f.putpixel((0, 0), (255, 255, 255) if i % 2 == 0 else (254, 254, 254))
        out.append(f)
    return out


# ==========================================
# EXPERIMENT ORCHESTRATOR
# ==========================================

# Anticipatory-cue timing constants (David's post-lab-meeting spec):
#   after the block breaks, leave the star centered -> almost immediately,
#   brief angry+shake+sound (still centered) -> star stops shaking, stays
#   angry+centered -> THIS is where part1 ends / the anticipatory freeze is
#   captured. The 2-2.5s hold itself is a static PNG held by the JS (not
#   baked into the GIF), matching the existing part1/antic_freeze/part2
#   architecture. THEN (part2) the star moves over and takes the star, as
#   before.
POST_BREAK_PAUSE = 0.15   # let the shards visibly settle, no longer than that
PRE_SHAKE_PAUSE = 0.3     # "almost immediately after the block breaks"
SHAKE_DURATION = 0.48     # "briefly shakes" (12 frames @ 25fps)
SHAKE_ROTATION_AMPLITUDE = 0.14  # radians (~8deg); matches warmup_single_character_trials.py
                                  # exactly -- the star's points rock in place, x/y never change.
# cross-context timing-parity pad so chains' part1 length exactly matches
# single_cause's part1 length (single_cause's bystander hop adds time that
# chains doesn't otherwise have) -- tuned empirically, see build script output.
CHAINS_PAD = 0.75


class TestTrialsExperiment:
    def __init__(self, c1_dict, c2_dict):
        self.r = Renderer()
        self.agent1 = Agent("Agent1", c1_dict["shape"], c1_dict["color"], AGENT_SIZE/2, 227)
        self.agent2 = Agent("Agent2", c2_dict["shape"], c2_dict["color"], 200 + AGENT_SIZE, 227)
        self.authority = Agent("authority", Shape.STAR, Color.YELLOW, CENTER_X, 60)

        # Place cube on right
        self.cube = BreakableCube(WIDTH - 100, GROUND_Y)

        self.props = [self.cube]
        self.anim = AnimationHelper(self.r, [self.agent1, self.agent2, self.authority], self.props)
        self.split_frame = None   # end of part1 / anticipatory-freeze frame index
        self.sound_frame = None   # frame index where the anticipatory shake+sound cue begins

    def reset_state(self):
        self.agent1.x, self.agent1.y = AGENT_SIZE/2, 227
        self.agent2.x, self.agent2.y = 200 + AGENT_SIZE, 227

        self.agent1.expression = Expression.NEUTRAL
        self.agent2.expression = Expression.NEUTRAL
        self.authority.expression = Expression.NEUTRAL

        self.cube.state = "whole"
        self.cube.fragments = []
        self.cube.visible = True

    def run_chain(self):
        # Cross-context timing-parity pad (see CHAINS_PAD comment above).
        self.anim.pause(CHAINS_PAD)

        # 1. Agent 1 rushes violently to Agent 2
        stop_x_1 = 200
        self.anim.move(self.agent1, stop_x_1, 227, 0.35) # speeded up for causation

        # 2. Agent 2 is propelled instantly into the Cube on collision
        stop_x_2 = WIDTH - 100 - AGENT_SIZE + 5
        self.anim.move(self.agent2, stop_x_2, 227, 0.35) # momentum transfer

        # 3. Cube Breaks Instantly!
        self.cube.state = "broken"
        cx = WIDTH - 100
        self.cube.fragments = [
            (cx-5, 230, -4, -7, 0),
            (cx+5, 220, 2, -12, 45),
            (cx+15, 235, 6, -10, 90),
            (cx-15, 245, -7, -5, 15),
            (cx-5, 250, -2, -15, 200),
            (cx+5, 240, 1, -7, 75),
            (cx+15, 255, 9, -6, -45),
            (cx-10, 260, -1, -4, 120),
            (cx, 265, 4, -2, 60),
            (cx+20, 260, 11, -9, -90)
        ]

        # 4. Resolve Ballistic Shards
        gravity = 1.5
        active = True
        frame_count = 0
        while active and frame_count < 100:
            active = False
            new_frags = []
            for fx, fy, dx, dy, rot in self.cube.fragments:
                nfx = fx + dx
                nfy = fy + dy
                ndy = dy + gravity
                nrot = rot + dx * 3 # spin naturally

                # Ground bounce collision (fs/2 is roughly 11 radius)
                bound_y = GROUND_Y - 11
                if nfy >= bound_y:
                    nfy = bound_y
                    ndy = 0          # Hard THUD, no vertical bouncing to eliminate jitter
                    dx = dx * 0.8   # Friction slide smoothly

                    if abs(dx) < 0.5: dx = 0

                if ndy != 0 or dx != 0:
                    active = True

                new_frags.append((nfx, nfy, dx, ndy, nrot))
            self.cube.fragments = new_frags
            self.anim.snap()
            frame_count += 1

        # Cue starts almost immediately after the block breaks -- just
        # enough of a pause for the shards to visibly stop moving.
        self.anim.pause(POST_BREAK_PAUSE)

    def anticipatory_cue(self):
        """Star stays centered: goes angry, briefly shakes IN PLACE (a
        rotational wobble only -- x/y position never changes) with the
        sound cue firing at shake onset, then holds still -- angry and
        centered -- which is exactly where part1 ends (the anticipatory-
        freeze PNG is the last frame of this). Both characters are
        untouched here (still matched, neither has moved or lost its
        star), and the star gives no directional cue. Records
        self.sound_frame for the JS audio trigger.
        """
        self.anim.pause(PRE_SHAKE_PAUSE)
        self.sound_frame = len(self.anim.frames)
        self.authority.expression = Expression.ANGRY
        shake_frames = int(SHAKE_DURATION * FPS)
        for i in range(shake_frames):
            self.authority.shake_rotation = SHAKE_ROTATION_AMPLITUDE * math.sin(i * 1.8)
            self.anim.snap()
        self.authority.shake_rotation = 0.0
        self.split_frame = len(self.anim.frames)

    def reveal_and_punish(self, target_agent):
        # authority is already angry-faced and centered (anticipatory_cue()
        # ran just before this) -- it only needs to move in and take the star.
        # 1. Authority descends above target at proper distance
        self.anim.move(self.authority, target_agent.x, target_agent.y - 140, Timing.MOVE_DURATION)

        # 2. Authority uses Magic Wand to interact with the star
        star_x, star_y = target_agent.x, target_agent.y - (AGENT_SIZE/2) - 25
        self.authority.arm_target_r = (star_x, star_y)
        self.anim.pause(0.2) # Contact pause

        # 3. Shake/Struggle logic (matching familiarization style but keeping tension)
        start_gx = self.authority.x
        for i in range(25):
            # Jitter the star and the wand tip slightly
            off = 5 * math.sin(i * 1.5)
            self.authority.x = start_gx + off
            target_agent.expression = Expression.SAD
            self.authority.arm_target_r = (star_x + off, star_y)
            self.anim.snap()

        self.authority.x = start_gx

        # FIERCE SNAP: Transfer Star
        target_agent.has_star = False
        target_agent.expression = Expression.SAD
        self.authority.has_star = False # Star vanishes from screen completely!

        # Retract wand to resting pose
        self.authority.arm_target_r = None
        self.anim.pause(0.5)

    def build_test_loop(self, target_agent, filename):
        self.agent1.has_star = True
        self.agent2.has_star = True
        self.reset_state()

        self.anim.pause(2.0) # Introduce initial scene with stars calmly

        # Causal event shown ONCE (not repeated) so the anticipatory window
        # isn't contaminated by a scanning pattern from repeated viewing.
        self.run_chain()

        # Centered angry+shake+sound cue, ending with the star settled --
        # angry and centered -- exactly at the part1/anticipatory-freeze
        # boundary.
        self.anticipatory_cue()

        # After the cue, punish the designated agent (part2).
        self.reveal_and_punish(target_agent)

        # Pillow can silently collapse consecutive near-identical frames when
        # saving a GIF (corrupting apparent motion, e.g. eating frames of the
        # brief shake). dither() forces every frame to be byte-distinct so
        # none get merged -- same fix already used in
        # warmup_single_character_trials.py. Applied once here so it
        # propagates through every save below AND through the combo/reverse
        # generation in __main__ (which reuses self.anim.frames).
        self.anim.frames = dither(self.anim.frames)

        # Finalize and Output
        print(f"Exporting {filename}...")

        # Embed the static 10 second pause natively to the last frame metadata
        durations = [1000//FPS] * len(self.anim.frames)
        durations[-1] = 10000

        self.anim.frames[0].save(filename, save_all=True, append_images=self.anim.frames[1:], duration=durations, loop=0, optimize=False)

        # Save freeze PNG
        freeze_filename = filename.replace(".gif", "_freeze.png")
        print(f"Exporting {freeze_filename}...")
        self.anim.frames[-1].save(freeze_filename)

        # Generate and save part1, part2, and anticipatory freeze (split
        # dynamically at self.split_frame, computed by anticipatory_cue()).
        sf = self.split_frame
        part1_frames = self.anim.frames[0:sf]
        part2_frames = self.anim.frames[sf:]
        antic_freeze = self.anim.frames[sf - 1]

        part1_filename = filename.replace('_final.gif', '_part1.gif')
        part2_filename = filename.replace('_final.gif', '_part2.gif')
        antic_filename = filename.replace('_final.gif', '_anticipatory_freeze.png')

        print(f"Exporting {part1_filename}... ({len(part1_frames)} frames, sound cue at frame {self.sound_frame})")
        part1_frames[0].save(part1_filename, save_all=True, append_images=part1_frames[1:], duration=durations[:sf], loop=0, optimize=False)

        print(f"Exporting {part2_filename}... ({len(part2_frames)} frames)")
        part2_frames[0].save(part2_filename, save_all=True, append_images=part2_frames[1:], duration=durations[sf:], loop=0, optimize=False)

        print(f"Exporting {antic_filename}...")
        antic_freeze.save(antic_filename)


if __name__ == "__main__":
    from PIL import Image
    import shutil
    import os
    import json

    # E = Teal Triangle, F = Red Square, G = Brown Circle, H = Blue Square
    E = {"shape": Shape.TRIANGLE, "color": Color.TEAL}
    F = {"shape": Shape.SQUARE, "color": Color.RED}
    G = {"shape": Shape.CIRCLE, "color": Color.BROWN}
    H = {"shape": Shape.SQUARE, "color": Color.BLUE}

    # ==========================
    # 1. Distal Role Focus Test
    # ==========================
    # Setup: E on Left, F in Middle.
    # Green punishes E (Agent1)
    distal_exp = TestTrialsExperiment(E, F)
    distal_exp.build_test_loop(target_agent=distal_exp.agent1, filename="distal_test_final.gif")

    # ==========================
    # 2. Proximal Role Focus Test
    # ==========================
    # Setup: G on Left, H in Middle.
    # Green punishes H (Agent2)
    proximal_exp = TestTrialsExperiment(G, H)
    proximal_exp.build_test_loop(target_agent=proximal_exp.agent2, filename="proximal_test_final.gif")

    timing_info = {
        "distal": {"split_frame": distal_exp.split_frame, "sound_frame": distal_exp.sound_frame,
                    "part1_ms": distal_exp.split_frame * (1000 // FPS),
                    "sound_ms": distal_exp.sound_frame * (1000 // FPS)},
        "proximal": {"split_frame": proximal_exp.split_frame, "sound_frame": proximal_exp.sound_frame,
                      "part1_ms": proximal_exp.split_frame * (1000 // FPS),
                      "sound_ms": proximal_exp.sound_frame * (1000 // FPS)},
    }
    print("Chains timing:", json.dumps(timing_info, indent=2))

    # ==========================
    # COMBO GENERATION (Original)
    # ==========================
    # Transition animation generator (blank then attention getter)
    trans = AnimationHelper(Renderer(), [], [])
    trans.blank(Timing.TRANSITION_BLANK)
    trans.ag(Timing.TRANSITION_AG)

    # Durations mapping (respect the 10 sec freeze for test ending frames)
    d_distal = [1000//FPS] * len(distal_exp.anim.frames)
    d_distal[-1] = 10000

    d_proximal = [1000//FPS] * len(proximal_exp.anim.frames)
    d_proximal[-1] = 10000

    d_trans = [1000//FPS] * len(trans.frames)

    # Test combo 1: Distal_Test_Final + Trans + Proximal_Test_Final
    c1_frames = distal_exp.anim.frames + trans.frames + proximal_exp.anim.frames
    c1_durations = d_distal + d_trans + d_proximal

    print("Exporting Test_Combo_1.gif...")
    c1_frames[0].save("Test_Combo_1.gif", save_all=True, append_images=c1_frames[1:], duration=c1_durations, loop=0, optimize=False)
    print("Exporting Test_Combo_1_freeze.png...")
    c1_frames[-1].save("Test_Combo_1_freeze.png")

    # Test combo 2: Proximal_Test_Final + Trans + Distal_Test_Final
    c2_frames = proximal_exp.anim.frames + trans.frames + distal_exp.anim.frames
    c2_durations = d_proximal + d_trans + d_distal

    print("Exporting Test_Combo_2.gif...")
    c2_frames[0].save("Test_Combo_2.gif", save_all=True, append_images=c2_frames[1:], duration=c2_durations, loop=0, optimize=False)
    print("Exporting Test_Combo_2_freeze.png...")
    c2_frames[-1].save("Test_Combo_2_freeze.png")

    # ==========================================
    # MIRRORED (REVERSE) GENERATION
    # ==========================================
    def get_reversed_frames(frames):
        return [f.transpose(Image.FLIP_LEFT_RIGHT) for f in frames]

    reverse_distal_frames = get_reversed_frames(distal_exp.anim.frames)
    reverse_proximal_frames = get_reversed_frames(proximal_exp.anim.frames)
    reverse_trans_frames = get_reversed_frames(trans.frames)

    # Save reverse distal test
    print("Exporting reverse_distal_test_final.gif...")
    reverse_distal_frames[0].save("reverse_distal_test_final.gif", save_all=True, append_images=reverse_distal_frames[1:], duration=d_distal, loop=0, optimize=False)
    print("Exporting reverse_distal_test_final_freeze.png...")
    reverse_distal_frames[-1].save("reverse_distal_test_final_freeze.png")

    # Save reverse distal test parts (dynamic split point)
    sf_d = distal_exp.split_frame
    reverse_distal_part1 = get_reversed_frames(distal_exp.anim.frames[0:sf_d])
    reverse_distal_part2 = get_reversed_frames(distal_exp.anim.frames[sf_d:])
    reverse_distal_antic = distal_exp.anim.frames[sf_d - 1].transpose(Image.FLIP_LEFT_RIGHT)

    print("Exporting reverse_distal_test_part1.gif...")
    reverse_distal_part1[0].save("reverse_distal_test_part1.gif", save_all=True, append_images=reverse_distal_part1[1:], duration=d_distal[:sf_d], loop=0, optimize=False)
    print("Exporting reverse_distal_test_part2.gif...")
    reverse_distal_part2[0].save("reverse_distal_test_part2.gif", save_all=True, append_images=reverse_distal_part2[1:], duration=d_distal[sf_d:], loop=0, optimize=False)
    print("Exporting reverse_distal_test_anticipatory_freeze.png...")
    reverse_distal_antic.save("reverse_distal_test_anticipatory_freeze.png")

    # Save reverse proximal test
    print("Exporting reverse_proximal_test_final.gif...")
    reverse_proximal_frames[0].save("reverse_proximal_test_final.gif", save_all=True, append_images=reverse_proximal_frames[1:], duration=d_proximal, loop=0, optimize=False)
    print("Exporting reverse_proximal_test_final_freeze.png...")
    reverse_proximal_frames[-1].save("reverse_proximal_test_final_freeze.png")

    # Save reverse proximal test parts (dynamic split point)
    sf_p = proximal_exp.split_frame
    reverse_proximal_part1 = get_reversed_frames(proximal_exp.anim.frames[0:sf_p])
    reverse_proximal_part2 = get_reversed_frames(proximal_exp.anim.frames[sf_p:])
    reverse_proximal_antic = proximal_exp.anim.frames[sf_p - 1].transpose(Image.FLIP_LEFT_RIGHT)

    print("Exporting reverse_proximal_test_part1.gif...")
    reverse_proximal_part1[0].save("reverse_proximal_test_part1.gif", save_all=True, append_images=reverse_proximal_part1[1:], duration=d_proximal[:sf_p], loop=0, optimize=False)
    print("Exporting reverse_proximal_test_part2.gif...")
    reverse_proximal_part2[0].save("reverse_proximal_test_part2.gif", save_all=True, append_images=reverse_proximal_part2[1:], duration=d_proximal[sf_p:], loop=0, optimize=False)
    print("Exporting reverse_proximal_test_anticipatory_freeze.png...")
    reverse_proximal_antic.save("reverse_proximal_test_anticipatory_freeze.png")

    # Reverse Combo 1: Reverse Distal + Trans + Reverse Proximal
    rc1_frames = reverse_distal_frames + reverse_trans_frames + reverse_proximal_frames
    print("Exporting Reverse_Test_Combo_1.gif...")
    rc1_frames[0].save("Reverse_Test_Combo_1.gif", save_all=True, append_images=rc1_frames[1:], duration=c1_durations, loop=0, optimize=False)
    print("Exporting Reverse_Test_Combo_1_freeze.png...")
    rc1_frames[-1].save("Reverse_Test_Combo_1_freeze.png")

    # Reverse Combo 2: Reverse Proximal + Trans + Reverse Distal
    rc2_frames = reverse_proximal_frames + reverse_trans_frames + reverse_distal_frames
    print("Exporting Reverse_Test_Combo_2.gif...")
    rc2_frames[0].save("Reverse_Test_Combo_2.gif", save_all=True, append_images=rc2_frames[1:], duration=c2_durations, loop=0, optimize=False)
    print("Exporting Reverse_Test_Combo_2_freeze.png...")
    rc2_frames[-1].save("Reverse_Test_Combo_2_freeze.png")

    # ==========================================
    # COPY TO REPOSITORY MATERIALS FOLDER
    # ==========================================
    dest_dir = "../materials/"
    files_to_copy = [
        "distal_test_final.gif",
        "distal_test_final_freeze.png",
        "distal_test_part1.gif",
        "distal_test_part2.gif",
        "distal_test_anticipatory_freeze.png",
        "proximal_test_final.gif",
        "proximal_test_final_freeze.png",
        "proximal_test_part1.gif",
        "proximal_test_part2.gif",
        "proximal_test_anticipatory_freeze.png",
        "reverse_distal_test_final.gif",
        "reverse_distal_test_final_freeze.png",
        "reverse_distal_test_part1.gif",
        "reverse_distal_test_part2.gif",
        "reverse_distal_test_anticipatory_freeze.png",
        "reverse_proximal_test_final.gif",
        "reverse_proximal_test_final_freeze.png",
        "reverse_proximal_test_part1.gif",
        "reverse_proximal_test_part2.gif",
        "reverse_proximal_test_anticipatory_freeze.png",
    ]

    if os.path.exists(dest_dir):
        print(f"Copying files to materials directory with chains prefix: {dest_dir}")
        for f in files_to_copy:
            if os.path.exists(f):
                dest_filename = f"chains_{f}"
                shutil.copy(f, os.path.join(dest_dir, dest_filename))
                print(f"  Copied {f} -> {dest_filename}")
        with open(os.path.join(dest_dir, "chains_timing.json"), "w") as fh:
            json.dump(timing_info, fh, indent=2)
    else:
        print(f"Destination directory {dest_dir} does not exist.")
