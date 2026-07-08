import math
import time
import random
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
from PIL import Image, ImageDraw

# ==========================================
# 1. CONFIG / CONSTANTS
# ==========================================

def hex_to_rgb(hex_str: str):
    h = hex_str.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

class Color(Enum):
    RED = "#ff6b6b"
    BLUE = "#4dabf7"
    GREEN = "#69db7c"
    YELLOW = "#fcc419"
    PURPLE = "#be4bdb"
    PINK = "#faa2c1"
    ORANGE = "#ff922b"
    TEAL = "#20c997"
    BROWN = "#8b4513"
    TRASH = "#ced4da"
    BG_PASTEL = "#ffffff"
    BLACK = "#212529"

class Shape(Enum):
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"

class Expression(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"

class Timing:
    MOVE_DURATION = 1.2
    PAUSE_SHORT = 1.0
    PAUSE_MEDIUM = 2.0
    REWARD_DURATION = 2.5
    TRANSITION_BLANK = 1.0
    TRANSITION_AG = 1.5
    JUMP_DURATION = 0.5

FPS = 25
WIDTH = 500
HEIGHT = 350
AGENT_SIZE = 65  # Scaled up per user request
GROUND_Y = 270

# ==========================================
# 2. DATA MODELS
# ==========================================

class Agent:
    def __init__(self, name: str, shape: Shape, color: Color, x: float, y: float):
        self.name, self.shape, self.color = name, shape, color
        self.x = self.start_x = x
        self.y = self.start_y = y
        self.expression = Expression.NEUTRAL
        self.has_star = False
        self.visible = True
        self.arm_target_l: Optional[Tuple[float, float]] = None
        self.arm_target_r: Optional[Tuple[float, float]] = None

class Prop:
    def __init__(self, obj_type: str, x: float, y: float, visible: bool = False):
        self.type, self.x, self.y, self.visible = obj_type, x, y, visible

# ==========================================
# 3. RENDER LAYER
# ==========================================

class Renderer:
    def draw_sphere_3d(self, draw, cx, cy, radius, color):
        rgb = hex_to_rgb(color)
        hl_x, hl_y = cx - radius * 0.3, cy - radius * 0.3
        draw.ellipse([cx - radius-1, cy - radius-1, cx + radius+1, cy + radius+1], fill=Color.BLACK.value)
        for i in range(20):
            t = i / 20.0
            r_val = radius * (1.0 - t)
            curr_c = tuple(int(c + (255 - c) * (t**1.8)) for c in rgb)
            draw.ellipse([cx + (hl_x-cx)*t - r_val, cy + (hl_y-cy)*t - r_val, cx + (hl_x-cx)*t + r_val, cy + (hl_y-cy)*t + r_val], fill=curr_c)

    def draw_face(self, draw, x, y, expression):
        draw.ellipse([x - 10, y - 11, x - 7, y - 3], fill=Color.BLACK.value)
        draw.ellipse([x + 7, y - 11, x + 10, y - 3], fill=Color.BLACK.value)
        if expression == Expression.NEUTRAL:
            draw.line([x - 6, y + 7, x + 6, y + 7], fill=Color.BLACK.value, width=3)
        elif expression == Expression.HAPPY:
            draw.arc([x-8, y+2, x+8, y+13], 0, 180, fill=Color.BLACK.value, width=3)
        elif expression == Expression.SAD:
            draw.arc([x-8, y+4, x+8, y+15], 180, 360, fill=Color.BLACK.value, width=3)
        elif expression == Expression.ANGRY:
            draw.line([x - 14, y - 17, x - 4, y - 11], fill=Color.BLACK.value, width=3)
            draw.line([x + 14, y - 17, x + 4, y - 11], fill=Color.BLACK.value, width=3)
            draw.arc([x-8, y+4, x+8, y+15], 180, 360, fill=Color.BLACK.value, width=3)

    def draw_star(self, draw, x, y):
        pts = []
        for i in range(10):
            r = 25 if i % 2 == 0 else 10 # Massive star
            a = i * (math.pi / 5) - (math.pi / 2)
            pts.append((x + r * math.cos(a), y + r * math.sin(a)))
        draw.polygon(pts, fill="#fcc419", outline=Color.BLACK.value)

    def draw_agent(self, draw, agent):
        r = AGENT_SIZE / 2
        # REPLACED GROUND SHADOW HERE: (No shadow drawn beneath agents)
        ac = Color.BLACK.value
        if agent.name != "green":
            draw.line([agent.x-10, agent.y+r-3, agent.x-15, GROUND_Y], fill=ac, width=4)
            draw.line([agent.x+10, agent.y+r-3, agent.x+15, GROUND_Y], fill=ac, width=4)
        
        root_lx, root_rx, root_y = agent.x-r+8, agent.x+r-8, agent.y
        if agent.arm_target_l: draw.line([root_lx, root_y, agent.arm_target_l[0], agent.arm_target_l[1]], fill=ac, width=4)
        else: draw.line([root_lx, root_y, root_lx-15, root_y+20], fill=ac, width=4)
        if agent.arm_target_r: draw.line([root_rx, root_y, agent.arm_target_r[0], agent.arm_target_r[1]], fill=ac, width=4)
        else: draw.line([root_rx, root_y, root_rx+15, root_y+20], fill=ac, width=4)

        if agent.shape == Shape.CIRCLE: self.draw_sphere_3d(draw, agent.x, agent.y, r, agent.color.value)
        elif agent.shape == Shape.SQUARE:
            draw.rectangle([agent.x-r, agent.y-r, agent.x+r, agent.y+r], fill=agent.color.value, outline=ac, width=3)
        elif agent.shape == Shape.TRIANGLE:
            draw.polygon([(agent.x-r, agent.y+r), (agent.x+r, agent.y+r), (agent.x, agent.y-r)], fill=agent.color.value, outline=ac, width=3)
        
        face_y = agent.y + (12 if agent.shape == Shape.TRIANGLE else 0)
        self.draw_face(draw, agent.x, face_y, agent.expression)
        if agent.has_star: self.draw_star(draw, agent.x+r+15, agent.y-r-10)

    def draw_bullseye(self, draw, x, y, scale):
        for i in range(4):
            r = 40 * scale * (1.0 - i/4.0)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=Color.BLACK.value if i%2==0 else Color.BG_PASTEL.value)

    def draw_trash_blob(self, draw, x, y):
        pts = [(x-10, y-2), (x-6, y-10), (x, y-6), (x+6, y-11), (x+11, y-3), (x+9, y+8), (x+2, y+6), (x-5, y+10), (x-12, y+4)]
        draw.polygon(pts, fill=Color.TRASH.value, outline=Color.BLACK.value, width=1)
        draw.line([x-5, y-10, x+2, y+6], fill=Color.BLACK.value, width=1)
        draw.line([x+2, y-11, x-6, y+4], fill=Color.BLACK.value, width=1)

    def render(self, agents, props, ag_scale=None):
        img = Image.new("RGB", (WIDTH, HEIGHT), Color.BG_PASTEL.value)
        draw = ImageDraw.Draw(img)
        if ag_scale: self.draw_bullseye(draw, WIDTH/2, HEIGHT/2, ag_scale); return img
        draw.line([0, GROUND_Y, WIDTH, GROUND_Y], fill=Color.BLACK.value, width=2)
        for p in props:
            if p.visible and p.type == "bin":
                draw.rectangle([p.x-15, p.y-25, p.x+15, p.y+10], fill="#ced4da", outline=Color.BLACK.value)
                draw.ellipse([p.x-15, p.y-30, p.x+15, p.y-20], fill=Color.BLACK.value)
        for a in agents: self.draw_agent(draw, a)
        for p in props:
            if p.visible and p.type == "trash":
                self.draw_trash_blob(draw, p.x, p.y)
        return img

# ==========================================
# 4. ANIMATION HELPERS
# ==========================================

class AnimationHelper:
    def __init__(self, renderer, agents, props):
        self.renderer, self.agents, self.props = renderer, agents, props
        self.frames = []

    def snap(self, ag_scale=None): self.frames.append(self.renderer.render(self.agents, self.props, ag_scale))
    def pause(self, d):
        for _ in range(int(d*FPS)): self.snap()
    def blank(self, d):
        img = Image.new("RGB", (WIDTH, HEIGHT), Color.BG_PASTEL.value)
        for _ in range(int(d*FPS)): self.frames.append(img.copy())
    def ag(self, d):
        for i in range(int(d*FPS)): self.snap(ag_scale=1.0 + 0.15*math.sin(i*0.4))

    def move(self, agent, tx, ty, d, carry_prop=None):
        sx, sy = agent.x, agent.y
        num = int(d*FPS)
        for i in range(num+1):
            t = i/num
            v = t*t*(3-2*t)
            agent.x, agent.y = sx+(tx-sx)*v, sy+(ty-sy)*v
            if carry_prop:
                # Hold prop far enough to completely avoid face blocking (scaled to 45 for larger size)
                # Raise Y coordinate to pass consistently above the bin lip
                offset = 45 if tx > sx else -45
                if tx == sx: offset = 45 # Default
                carry_prop.x, carry_prop.y = agent.x + offset, agent.y - 30
                if offset > 0:
                    agent.arm_target_r = (carry_prop.x, carry_prop.y)
                    agent.arm_target_l = None
                else:
                    agent.arm_target_l = (carry_prop.x, carry_prop.y)
                    agent.arm_target_r = None
            self.snap()

    def jump(self, agent):
        sy = agent.y
        num = int(Timing.JUMP_DURATION*FPS)
        for i in range(num+1):
            t = i/num
            v = math.sin(t*math.pi)
            agent.y = sy - 25*v
            self.snap()
        agent.y = sy

# ==========================================
# 5. EXPERIMENT LOGIC
# ==========================================

class Experiment:
    def __init__(self, c1, c2):
        self.r = Renderer()
        self.a1 = Agent("A", c1["shape"], c1["color"], 100, 240)
        self.a2 = Agent("B", c2["shape"], c2["color"], 400, 240)
        self.green = Agent("green", Shape.SQUARE, Color.GREEN, 250, 60)
        self.bin = Prop("bin", 250, 260, True)
        self.props = [self.bin]
        self.anim = AnimationHelper(self.r, [self.a1, self.a2, self.green], self.props)

    def introduce(self):
        self.anim.pause(1.0)
        self.anim.jump(self.a1); self.anim.pause(0.5); self.anim.jump(self.a2); self.anim.pause(1.0)

    def reset_agents(self):
        self.a1.x, self.a1.y, self.a1.has_star, self.a1.expression = 100, 240, False, Expression.NEUTRAL
        self.a2.x, self.a2.y, self.a2.has_star, self.a2.expression = 400, 240, False, Expression.NEUTRAL
        self.green.expression = Expression.NEUTRAL

    def run_reward_pair(self):
        self.introduce()
        self._reward_phase(self.a1); self.anim.blank(Timing.TRANSITION_BLANK); self.anim.ag(Timing.TRANSITION_AG)
        self.reset_agents(); self._reward_phase(self.a2)

    def run_punish_pair(self):
        self.a1.has_star = self.a2.has_star = True; self.introduce()
        self._punish_phase(self.a1); self.anim.blank(Timing.TRANSITION_BLANK); self.anim.ag(Timing.TRANSITION_AG)
        self.reset_agents(); self.a1.has_star = self.a2.has_star = True; self._punish_phase(self.a2)

    def _reward_phase(self, helper):
        trash = Prop("trash", helper.x + (70 if helper.x < 250 else -70), 260, True)
        self.props.append(trash); self.anim.pause(0.8)
        # Move body to trash
        self.anim.move(helper, trash.x, 240, Timing.MOVE_DURATION)
        # Explicit reach
        if helper.start_x < 250:
            helper.arm_target_r = (trash.x, trash.y)
            helper.arm_target_l = None
        else:
            helper.arm_target_l = (trash.x, trash.y)
            helper.arm_target_r = None
        self.anim.pause(0.4)
        
        # Lift and position before transit
        ty_start = trash.y
        tx_start = trash.x
        target_offset = 45 if helper.start_x < 250 else -45
        target_x = helper.x + target_offset
        for i in range(1, 9):
            trash.y = ty_start - i * ((ty_start - (helper.y - 30)) / 8)
            trash.x = tx_start + (target_x - tx_start) * (i/8)
            if helper.start_x < 250: helper.arm_target_r = (trash.x, trash.y)
            else: helper.arm_target_l = (trash.x, trash.y)
            self.anim.snap()
            
        # Carry to bin near side
        stop_x = self.bin.x - 45 if helper.start_x < 250 else self.bin.x + 45
        self.anim.move(helper, stop_x, 240, Timing.MOVE_DURATION, carry_prop=trash)
        
        # Drop into bin explicitly - Stop at bin opening center
        ty_start = trash.y
        for i in range(8):
            trash.y = ty_start + i * 1 # Drops smoothly exactly into the black opening
            if helper.start_x < 250:
                helper.arm_target_r = (trash.x, trash.y)
                helper.arm_target_l = None
            else:
                helper.arm_target_l = (trash.x, trash.y)
                helper.arm_target_r = None
            self.anim.snap()
        trash.visible = False; helper.arm_target_l = helper.arm_target_r = None; self.anim.pause(0.5)
        # Green Reward - Descend from above
        self.anim.move(self.green, helper.x, helper.y - 75, Timing.MOVE_DURATION)
        self.green.expression = Expression.HAPPY
        # Small reach pointing to the massive star attached to the right side
        self.green.arm_target_r = (helper.x + 45, helper.y - 40)
        helper.has_star, helper.expression = True, Expression.HAPPY
        self.anim.pause(Timing.REWARD_DURATION)
        self.green.arm_target_r = None; self.green.expression = Expression.NEUTRAL
        self.anim.move(self.green, 250, 60, Timing.MOVE_DURATION)
        self.anim.move(helper, helper.start_x, helper.start_y, Timing.MOVE_DURATION)
        self.props.remove(trash)

    def _punish_phase(self, mischief):
        # Trash starts explicitly at the center height of the bin opening
        trash = Prop("trash", self.bin.x, 215, False)
        self.props.append(trash); self.anim.pause(0.8)
        
        # Move to near side of bin
        stop_x = self.bin.x - 45 if mischief.start_x < 250 else self.bin.x + 45
        self.anim.move(mischief, stop_x, 240, Timing.MOVE_DURATION)
        
        # Reach deep into bin (mischief on left uses right arm, mischief on right uses left arm)
        if mischief.start_x < 250:
            mischief.arm_target_r = (self.bin.x, 225)
            mischief.arm_target_l = None
        else:
            mischief.arm_target_l = (self.bin.x, 225)
            mischief.arm_target_r = None
        self.anim.pause(0.5); trash.visible = True; trash.x = self.bin.x; trash.y = 225; self.anim.snap()
        
        # Smoothly pull trash out across the body and swap hands
        target_offset = -45 if mischief.start_x < 250 else 45
        target_x = mischief.x + target_offset
        target_y = mischief.y - 30
        
        frames = 8
        ty_start = trash.y
        tx_start = trash.x
        
        for i in range(1, frames+1):
            trash.x = tx_start + (target_x - tx_start) * (i/frames)
            trash.y = ty_start + (target_y - ty_start) * (i/frames)
            
            if i < frames/2:
                # Held by inner arm
                if mischief.start_x < 250: mischief.arm_target_r = (trash.x, trash.y)
                else: mischief.arm_target_l = (trash.x, trash.y)
            else:
                # Swapped to outer arm ready for carry
                if mischief.start_x < 250:
                    mischief.arm_target_l = (trash.x, trash.y)
                    mischief.arm_target_r = None
                else:
                    mischief.arm_target_r = (trash.x, trash.y)
                    mischief.arm_target_l = None
            self.anim.snap()
            
        self.anim.pause(0.2)
        
        # Carry back to start location +/-
        return_x = mischief.start_x + (80 if mischief.start_x < 250 else -80)
        self.anim.move(mischief, return_x, 240, Timing.MOVE_DURATION, carry_prop=trash)
        
        # Drop trash to floor so it doesn't block agent face during punishment
        ty_start = trash.y
        for i in range(12):
            trash.y = min(265, ty_start + i * 5) # Drop fast fully to ground level
            if return_x < stop_x: # Moving left uses left arm
                mischief.arm_target_l = (trash.x, trash.y)
            else:
                mischief.arm_target_r = (trash.x, trash.y)
            self.anim.snap()
            
        mischief.arm_target_l = mischief.arm_target_r = None
        # Green Punishment
        self.anim.move(self.green, mischief.x, mischief.y - 75, Timing.MOVE_DURATION)
        self.green.expression = Expression.ANGRY
        self.green.arm_target_r = (mischief.x + 45, mischief.y - 40)
        start_gx = self.green.x
        for i in range(15):
            self.green.x = start_gx + 5 * math.sin(i*1.5); self.anim.snap()
        self.green.x = start_gx
        mischief.has_star, mischief.expression = False, Expression.SAD; self.anim.pause(Timing.REWARD_DURATION)
        self.green.arm_target_l = self.green.arm_target_r = None
        self.green.expression = Expression.NEUTRAL
        self.anim.move(self.green, 250, 60, Timing.MOVE_DURATION); self.anim.move(mischief, mischief.start_x, mischief.start_y, Timing.MOVE_DURATION)
        self.props.remove(trash)

    def save(self, name):
        self.anim.frames[0].save(name, save_all=True, append_images=self.anim.frames[1:], duration=1000//FPS, loop=0)

if __name__ == "__main__":
    A, B = {"shape": Shape.CIRCLE, "color": Color.PINK}, {"shape": Shape.TRIANGLE, "color": Color.YELLOW}
    C, D = {"shape": Shape.SQUARE, "color": Color.PURPLE}, {"shape": Shape.CIRCLE, "color": Color.ORANGE}
    
    e1 = Experiment(A, B); e1.run_reward_pair(); e1.save("reward_AB_final.gif")
    e2 = Experiment(C, D); e2.run_punish_pair(); e2.save("punish_CD_final.gif")
    e3 = Experiment(A, B); e3.run_punish_pair(); e3.save("punish_AB_final.gif")
    e4 = Experiment(C, D); e4.run_reward_pair(); e4.save("reward_CD_final.gif")
    
    # Transition animation generator
    trans = AnimationHelper(Renderer(), [], [])
    trans.blank(Timing.TRANSITION_BLANK)
    trans.ag(Timing.TRANSITION_AG)
    
    # Familiarization combo 1: AB Reward + Trans + CD Punish
    c1_frames = e1.anim.frames + trans.frames + e2.anim.frames
    c1_frames[0].save("Fam_Combo_1.gif", save_all=True, append_images=c1_frames[1:], duration=1000//FPS, loop=0)
    
    # Familiarization combo 2: CD Reward + Trans + AB Punish
    c2_frames = e4.anim.frames + trans.frames + e3.anim.frames
    c2_frames[0].save("Fam_Combo_2.gif", save_all=True, append_images=c2_frames[1:], duration=1000//FPS, loop=0)
