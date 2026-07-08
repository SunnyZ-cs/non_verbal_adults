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
    STAR = "star"

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
WIDTH = 800
HEIGHT = 300
CENTER_X = WIDTH // 2
AGENT_SIZE = 65
GROUND_Y = 260

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
        self.expression = Expression.NEUTRAL

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

    def draw_face(self, draw, x, y, expression, scale=1.0):
        fc = "#495057"
        # Eyes
        ex_off, ey_top, ey_bot = 10 * scale, 11 * scale, 3 * scale
        draw.ellipse([x - ex_off, y - ey_top, x - (6*scale), y - ey_bot], fill=fc)
        draw.ellipse([x + (6*scale), y - ey_top, x + ex_off, y - ey_bot], fill=fc)
        
        if expression == Expression.NEUTRAL:
            draw.line([x - 6*scale, y + 7*scale, x + 6*scale, y + 7*scale], fill=fc, width=max(1, int(3*scale)))
        elif expression == Expression.HAPPY:
            draw.arc([x-8*scale, y+2*scale, x+8*scale, y+13*scale], 0, 180, fill=fc, width=max(1, int(3*scale)))
        elif expression == Expression.SAD:
            draw.arc([x-8*scale, y+4*scale, x+8*scale, y+15*scale], 180, 360, fill=fc, width=max(1, int(3*scale)))
        elif expression == Expression.ANGRY:
            draw.line([x - 14*scale, y - 17*scale, x - 4*scale, y - 11*scale], fill=fc, width=max(1, int(3*scale)))
            draw.line([x + 14*scale, y - 17*scale, x + 4*scale, y - 11*scale], fill=fc, width=max(1, int(3*scale)))
            draw.arc([x-8*scale, y+4*scale, x+8*scale, y+15*scale], 180, 360, fill=fc, width=max(1, int(3*scale)))

    def get_highlight(self, color_hex):
        rgb = hex_to_rgb(color_hex)
        return '#%02x%02x%02x' % tuple(min(255, int(c + (255 - c) * 0.45)) for c in rgb)

    def draw_star(self, draw, x, y, r=25, color="#fcc419"):
        pts = []
        hl_pts = []
        for i in range(10):
            curr_r = r if i % 2 == 0 else r * 0.4
            a = i * (math.pi / 5) - (math.pi / 2)
            pts.append((x + curr_r * math.cos(a), y + curr_r * math.sin(a)))
            if i <= 4: # Top left edges for highlight
                hl_pts.append((x - r*0.1 + curr_r * 0.7 * math.cos(a), y - r*0.1 + curr_r * 0.7 * math.sin(a)))
        
        draw.polygon(pts, fill=color)
        if len(hl_pts) >= 3:
            draw.polygon(hl_pts, fill=self.get_highlight(color))

    def draw_wand(self, draw, root_x, root_y, target_x, target_y):
        # Draw a brown stick with a tiny star at the end
        draw.line([root_x, root_y, target_x, target_y], fill="#8b4513", width=5)
        self.draw_star(draw, target_x, target_y, r=10)

    def draw_agent(self, draw, agent):
        r = AGENT_SIZE / 2
        ac = "#495057" # Soft dark brown for arms
        
        if agent.shape == Shape.TRIANGLE:
            root_lx, root_rx = agent.x - r/2, agent.x + r/2
        elif agent.shape == Shape.STAR:
            root_lx, root_rx = agent.x - 15, agent.x + 15
        else:
            root_lx, root_rx = agent.x-r+8, agent.x+r-8
        root_y = agent.y
        if agent.name == "authority":
            if agent.arm_target_r: 
                self.draw_wand(draw, root_rx, root_y, agent.arm_target_r[0], agent.arm_target_r[1])
            else:
                self.draw_wand(draw, root_rx, root_y, root_rx+20, root_y-25)
            if agent.arm_target_l:
                draw.line([root_lx, root_y, agent.arm_target_l[0], agent.arm_target_l[1]], fill=ac, width=4)
            else:
                draw.line([root_lx, root_y, root_lx-15, root_y+20], fill=ac, width=4)
        else:
            if agent.arm_target_l: draw.line([root_lx, root_y, agent.arm_target_l[0], agent.arm_target_l[1]], fill=ac, width=4)
            else: draw.line([root_lx, root_y, root_lx-15, root_y+20], fill=ac, width=4)
            if agent.arm_target_r: draw.line([root_rx, root_y, agent.arm_target_r[0], agent.arm_target_r[1]], fill=ac, width=4)
            else: draw.line([root_rx, root_y, root_rx+15, root_y+20], fill=ac, width=4)

        color = agent.color.value
        hl = self.get_highlight(color)

        if agent.shape == Shape.CIRCLE: 
            self.draw_sphere_3d(draw, agent.x, agent.y, r, color)
        elif agent.shape == Shape.SQUARE:
            draw.rectangle([agent.x-r, agent.y-r, agent.x+r, agent.y+r], fill=color)
            # Add glossy highlight curve
            draw.polygon([(agent.x-r, agent.y-r), (agent.x, agent.y-r), (agent.x-r*0.2, agent.y-r*0.2), (agent.x-r, agent.y)], fill=hl)
        elif agent.shape == Shape.TRIANGLE:
            draw.polygon([(agent.x-r, agent.y+r), (agent.x+r, agent.y+r), (agent.x, agent.y-r)], fill=color)
            # Add glossy highlight curve
            draw.polygon([(agent.x, agent.y-r), (agent.x-r, agent.y+r), (agent.x-r*0.6, agent.y+r*0.8), (agent.x-r*0.1, agent.y-r*0.6)], fill=hl)
        elif agent.shape == Shape.STAR:
            self.draw_star(draw, agent.x, agent.y, r * 1.5 if agent.name == "authority" else r, color)

        
        face_y = agent.y + (12 if agent.shape == Shape.TRIANGLE else 0)
        f_scale = 0.75 if agent.shape == Shape.STAR else 1.0
        self.draw_face(draw, agent.x, face_y, agent.expression, scale=f_scale)
        if agent.has_star: self.draw_star(draw, agent.x, agent.y-r-25)

    def draw_bullseye(self, draw, x, y, scale):
        for i in range(4):
            r = 40 * scale * (1.0 - i/4.0)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=Color.BLACK.value if i%2==0 else Color.BG_PASTEL.value)

    def draw_trash_blob(self, draw, x, y):
        pts = [(x-10, y-2), (x-6, y-10), (x, y-6), (x+6, y-11), (x+11, y-3), (x+9, y+8), (x+2, y+6), (x-5, y+10), (x-12, y+4)]
        draw.polygon(pts, fill=Color.TRASH.value)
        draw.polygon([(x-10, y-2), (x-6, y-10), (x, y-6), (x-3, y-2)], fill=self.get_highlight(Color.TRASH.value))
        draw.line([x-5, y-10, x+2, y+6], fill="#adb5bd", width=1)
        draw.line([x+2, y-11, x-6, y+4], fill="#adb5bd", width=1)

    def render(self, agents, props, ag_scale=None):
        img = Image.new("RGB", (WIDTH, HEIGHT), Color.BG_PASTEL.value)
        draw = ImageDraw.Draw(img)
        if ag_scale: self.draw_bullseye(draw, WIDTH/2, HEIGHT/2, ag_scale); return img
        draw.line([0, GROUND_Y, WIDTH, GROUND_Y], fill=Color.BLACK.value, width=2)
        
        # Draw background props first
        for p in props:
            if p.visible:
                if p.type == "bin":
                    draw.rectangle([p.x-25, p.y-35, p.x+25, p.y+15], fill="#adb5bd", outline=Color.BLACK.value, width=2)
                    for lx in range(int(p.x-15), int(p.x+20), 10):
                        draw.line([lx, p.y-35, lx, p.y+15], fill="#868e96", width=2)
                    draw.ellipse([p.x-28, p.y-42, p.x+28, p.y-28], fill="#6c757d", outline=Color.BLACK.value, width=2)
                    draw.ellipse([p.x-25, p.y-40, p.x+25, p.y-30], fill=Color.BLACK.value)
                elif p.type == "tower_base":
                    draw.rectangle([p.x-15, p.y, p.x+15, p.y+30], fill="#fcc419", outline=Color.BLACK.value, width=2)
                    draw.rectangle([p.x-15, p.y-30, p.x+15, p.y], fill="#fcc419", outline=Color.BLACK.value, width=2)
                elif p.type == "baby":
                    r = 20
                    self.draw_sphere_3d(draw, p.x, p.y, r, Color.BLUE.value)
                    self.draw_face(draw, p.x, p.y, p.expression, scale=0.8)
                elif p.type == "flower":
                    # Stem
                    draw.line([p.x, p.y, p.x, p.y+30], fill=Color.GREEN.value, width=4)
                    if p.expression == Expression.SAD:
                        # Wilted flower head
                        draw.ellipse([p.x-10, p.y+20, p.x+10, p.y+35], fill=Color.RED.value, outline=Color.BLACK.value)
                    else:
                        # Healthy flower head
                        for i in range(5):
                            a = i * (2*math.pi/5)
                            px, py = p.x + 12*math.cos(a), p.y + 12*math.sin(a)
                            draw.ellipse([px-8, py-8, px+8, py+8], fill=Color.RED.value, outline=Color.BLACK.value)
                        draw.ellipse([p.x-6, p.y-6, p.x+6, p.y+6], fill=Color.YELLOW.value, outline=Color.BLACK.value)

        for a in agents: self.draw_agent(draw, a)
        
        # Draw foreground props (carried ones)
        for p in props:
            if p.visible:
                if p.type == "trash":
                    self.draw_trash_blob(draw, p.x, p.y)
                elif p.type == "block":
                    draw.rectangle([p.x-15, p.y-15, p.x+15, p.y+15], fill="#fcc419", outline=Color.BLACK.value, width=2)
                elif p.type == "toy":
                    r = 8
                    self.draw_sphere_3d(draw, p.x, p.y, r, Color.PINK.value)
                    
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

    def move(self, agent, tx, ty, d, carry_prop=None, carry_side=None):
        sx, sy = agent.x, agent.y
        num = int(d*FPS)
        for i in range(num+1):
            t = i/num
            v = t*t*(3-2*t)
            agent.x, agent.y = sx+(tx-sx)*v, sy+(ty-sy)*v
            if carry_prop:
                if carry_side: offset = 45 if carry_side == "right" else -45
                else: offset = 45 if tx >= sx else -45
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
        self.a1 = Agent("A", c1["shape"], c1["color"], CENTER_X - 150, 227)
        self.a2 = Agent("B", c2["shape"], c2["color"], CENTER_X + 150, 227)
        self.authority = Agent("authority", Shape.STAR, Color.YELLOW, CENTER_X, 60)
        self.props = []
        self.anim = AnimationHelper(self.r, [self.a1, self.a2, self.authority], self.props)

    def introduce(self):
        self.anim.pause(1.0)
        self.anim.jump(self.a1); self.anim.pause(0.5); self.anim.jump(self.a2); self.anim.pause(1.0)

    def reset_agents(self):
        self.a1.x, self.a1.y, self.a1.has_star, self.a1.expression = CENTER_X - 150, 227, False, Expression.NEUTRAL
        self.a2.x, self.a2.y, self.a2.has_star, self.a2.expression = CENTER_X + 150, 227, False, Expression.NEUTRAL
        self.authority.expression = Expression.NEUTRAL

    def setup_scene(self, scene_name, is_reward):
        self.props.clear()
        if scene_name == "trash":
            self.center_prop = Prop("bin", CENTER_X, 245, True)
        elif scene_name == "tower":
            self.center_prop = Prop("tower_base", CENTER_X, 230, True)
            if not is_reward:
                # Add the 3rd block immediately so it's there during introduction
                self.props.append(Prop("block", CENTER_X, 185, True))
        elif scene_name == "toy":
            self.center_prop = Prop("baby", CENTER_X, 240, True)
        elif scene_name == "flower":
            self.center_prop = Prop("flower", CENTER_X, 230, True)
            if is_reward: self.center_prop.expression = Expression.SAD # Start wilted
        self.props.append(self.center_prop)

    def generate_full_familiarization(self, is_reward):
        for i, scene in enumerate(["trash", "tower", "toy"]):
            self.run_scene_pair(scene, is_reward)
            if i < 2:
                self.anim.blank(Timing.TRANSITION_BLANK)
                self.anim.ag(Timing.TRANSITION_AG)

    def run_scene_pair(self, scene_name, is_reward):
        self.setup_scene(scene_name, is_reward)
        if not is_reward:
            self.a1.has_star = self.a2.has_star = True
        self.introduce()
        
        self._run_phase(self.a1, scene_name, is_reward)
        self.anim.blank(Timing.TRANSITION_BLANK)
        self.anim.ag(Timing.TRANSITION_AG)
        
        self.reset_agents()
        self.setup_scene(scene_name, is_reward) # Ensure props reset
        if not is_reward:
            self.a1.has_star = self.a2.has_star = True
            
        self._run_phase(self.a2, scene_name, is_reward)

    def _run_phase(self, helper, scene_name, is_reward):
        if scene_name == "trash":
            if is_reward: self._trash_reward_phase(helper)
            else: self._trash_punish_phase(helper)
        elif scene_name == "tower":
            if is_reward: self._tower_reward_phase(helper)
            else: self._tower_punish_phase(helper)
        elif scene_name == "toy":
            if is_reward: self._toy_reward_phase(helper)
            else: self._toy_punish_phase(helper)
        elif scene_name == "flower":
            if is_reward: self._flower_reward_phase(helper)
            else: self._flower_punish_phase(helper)

    def _trash_reward_phase(self, helper):
        trash = Prop("trash", helper.x + (70 if helper.x < CENTER_X else -70), 250, True)
        self.props.append(trash); self.anim.pause(0.8)
        # Move closer so arms aren't too long
        pickup_x = trash.x - 35 if helper.x < trash.x else trash.x + 35
        self.anim.move(helper, pickup_x, 227, Timing.MOVE_DURATION)
        if helper.start_x < CENTER_X: helper.arm_target_r = (trash.x, trash.y)
        else: helper.arm_target_l = (trash.x, trash.y)
        self.anim.pause(0.4)
        
        ty_start, tx_start = trash.y, trash.x
        target_x = helper.x + (45 if helper.start_x < CENTER_X else -45)
        for i in range(1, 9):
            trash.y = ty_start - i * ((ty_start - (helper.y - 30)) / 8)
            trash.x = tx_start + (target_x - tx_start) * (i/8)
            if helper.start_x < CENTER_X: helper.arm_target_r = (trash.x, trash.y)
            else: helper.arm_target_l = (trash.x, trash.y)
            self.anim.snap()
            
        stop_x = self.center_prop.x - 45 if helper.start_x < CENTER_X else self.center_prop.x + 45
        c_side = "right" if helper.start_x < CENTER_X else "left"
        self.anim.move(helper, stop_x, 227, Timing.MOVE_DURATION, carry_prop=trash, carry_side=c_side)
        
        ty_start = trash.y
        for i in range(8):
            trash.y = ty_start + i * 1
            if helper.start_x < CENTER_X: helper.arm_target_r = (trash.x, trash.y)
            else: helper.arm_target_l = (trash.x, trash.y)
            self.anim.snap()
        trash.visible = False; helper.arm_target_l = helper.arm_target_r = None; self.anim.pause(0.5)
        
        self._give_reward(helper)
        if trash in self.props: self.props.remove(trash)

    def _trash_punish_phase(self, mischief):
        trash = Prop("trash", self.center_prop.x, 175, False)
        self.props.append(trash); self.anim.pause(0.8)
        
        stop_x = self.center_prop.x - 45 if mischief.start_x < CENTER_X else self.center_prop.x + 45
        self.anim.move(mischief, stop_x, 230, Timing.MOVE_DURATION)
        
        if mischief.start_x < CENTER_X: mischief.arm_target_r = (self.center_prop.x, 185)
        else: mischief.arm_target_l = (self.center_prop.x, 185)
        self.anim.pause(0.5); trash.visible = True; trash.x = self.center_prop.x; trash.y = 185; self.anim.snap()
        
        target_x = mischief.x + (-45 if mischief.start_x < CENTER_X else 45)
        target_y = mischief.y - 30
        
        frames = 8
        ty_start, tx_start = trash.y, trash.x
        
        for i in range(1, frames+1):
            trash.x = tx_start + (target_x - tx_start) * (i/frames)
            trash.y = ty_start + (target_y - ty_start) * (i/frames)
            
            if i < frames/2:
                if mischief.start_x < CENTER_X: mischief.arm_target_r = (trash.x, trash.y)
                else: mischief.arm_target_l = (trash.x, trash.y)
            else:
                if mischief.start_x < CENTER_X: mischief.arm_target_l = (trash.x, trash.y)
                else: mischief.arm_target_r = (trash.x, trash.y)
            self.anim.snap()
            
        self.anim.pause(0.2)
        
        return_x = mischief.start_x - 50 if mischief.start_x < CENTER_X else mischief.start_x + 50
        c_side = "left" if mischief.start_x < CENTER_X else "right"
        self.anim.move(mischief, return_x, 227, Timing.MOVE_DURATION, carry_prop=trash, carry_side=c_side)
        
        ty_start = trash.y
        for i in range(12):
            trash.y = min(250, ty_start + i * 6)
            if c_side == "left": mischief.arm_target_l = (trash.x, trash.y)
            else: mischief.arm_target_r = (trash.x, trash.y)
            self.anim.snap()
            
        mischief.arm_target_l = mischief.arm_target_r = None
        
        self._give_punishment(mischief)
        if trash in self.props: self.props.remove(trash)

    def _tower_reward_phase(self, helper):
        block = Prop("block", helper.x + (70 if helper.x < CENTER_X else -70), 245, True)
        self.props.append(block); self.anim.pause(0.8)
        # Move closer so arms aren't too long
        pickup_x = block.x - 35 if helper.x < block.x else block.x + 35
        self.anim.move(helper, pickup_x, 227, Timing.MOVE_DURATION)
        if helper.start_x < CENTER_X: helper.arm_target_r = (block.x, block.y)
        else: helper.arm_target_l = (block.x, block.y)
        self.anim.pause(0.4)
        
        ty_start, tx_start = block.y, block.x
        target_x = helper.x + (45 if helper.start_x < CENTER_X else -45)
        for i in range(1, 9):
            block.y = ty_start - i * ((ty_start - (helper.y - 30)) / 8)
            block.x = tx_start + (target_x - tx_start) * (i/8)
            if helper.start_x < CENTER_X: helper.arm_target_r = (block.x, block.y)
            else: helper.arm_target_l = (block.x, block.y)
            self.anim.snap()
            
        stop_x = self.center_prop.x - 45 if helper.start_x < CENTER_X else self.center_prop.x + 45
        c_side = "right" if helper.start_x < CENTER_X else "left"
        self.anim.move(helper, stop_x, 227, Timing.MOVE_DURATION, carry_prop=block, carry_side=c_side)
        
        ty_start = block.y
        # Drop block on top of tower (top of base is 200, so block y is 185)
        for i in range(8):
            block.y = ty_start + i * ((185 - ty_start)/8)
            if helper.start_x < CENTER_X: helper.arm_target_r = (block.x, block.y)
            else: helper.arm_target_l = (block.x, block.y)
            self.anim.snap()
        helper.arm_target_l = helper.arm_target_r = None; self.anim.pause(0.5)
        
        self._give_reward(helper)
        # We don't remove block so it stays on tower

    def _tower_punish_phase(self, mischief):
        # 3rd block is already added in setup_scene
        block = [p for p in self.props if p.type == "block"][0]
        self.anim.pause(0.8)
        
        stop_x = self.center_prop.x - 45 if mischief.start_x < CENTER_X else self.center_prop.x + 45
        self.anim.move(mischief, stop_x, 230, Timing.MOVE_DURATION)
        
        if mischief.start_x < CENTER_X: mischief.arm_target_r = (self.center_prop.x, 185)
        else: mischief.arm_target_l = (self.center_prop.x, 185)
        self.anim.pause(0.5); self.anim.snap()
        
        target_x = mischief.x + (-45 if mischief.start_x < CENTER_X else 45)
        target_y = mischief.y - 30
        
        frames = 8
        ty_start, tx_start = block.y, block.x
        for i in range(1, frames+1):
            block.x = tx_start + (target_x - tx_start) * (i/frames)
            block.y = ty_start + (target_y - ty_start) * (i/frames)
            if i < frames/2:
                if mischief.start_x < CENTER_X: mischief.arm_target_r = (block.x, block.y)
                else: mischief.arm_target_l = (block.x, block.y)
            else:
                if mischief.start_x < CENTER_X: mischief.arm_target_l = (block.x, block.y)
                else: mischief.arm_target_r = (block.x, block.y)
            self.anim.snap()
            
        self.anim.pause(0.2)
        
        return_x = mischief.start_x - 50 if mischief.start_x < CENTER_X else mischief.start_x + 50
        c_side = "left" if mischief.start_x < CENTER_X else "right"
        self.anim.move(mischief, return_x, 227, Timing.MOVE_DURATION, carry_prop=block, carry_side=c_side)
        
        ty_start = block.y
        for i in range(12):
            block.y = min(245, ty_start + i * 6)
            if c_side == "left": mischief.arm_target_l = (block.x, block.y)
            else: mischief.arm_target_r = (block.x, block.y)
            self.anim.snap()
            
        mischief.arm_target_l = mischief.arm_target_r = None
        
        self._give_punishment(mischief)
        if block in self.props: self.props.remove(block)

    def _toy_reward_phase(self, helper):
        toy = Prop("toy", helper.x + (70 if helper.x < CENTER_X else -70), 252, True)
        self.props.append(toy); self.anim.pause(0.8)
        # Move closer so arms aren't too long
        pickup_x = toy.x - 35 if helper.x < toy.x else toy.x + 35
        self.anim.move(helper, pickup_x, 227, Timing.MOVE_DURATION)
        if helper.start_x < CENTER_X: helper.arm_target_r = (toy.x, toy.y)
        else: helper.arm_target_l = (toy.x, toy.y)
        self.anim.pause(0.4)
        
        ty_start, tx_start = toy.y, toy.x
        target_x = helper.x + (45 if helper.start_x < CENTER_X else -45)
        for i in range(1, 9):
            toy.y = ty_start - i * ((ty_start - (helper.y - 30)) / 8)
            toy.x = tx_start + (target_x - tx_start) * (i/8)
            if helper.start_x < CENTER_X: helper.arm_target_r = (toy.x, toy.y)
            else: helper.arm_target_l = (toy.x, toy.y)
            self.anim.snap()
            
        stop_x = self.center_prop.x - 70 if helper.start_x < CENTER_X else self.center_prop.x + 70
        c_side = "right" if helper.start_x < CENTER_X else "left"
        self.anim.move(helper, stop_x, 227, Timing.MOVE_DURATION, carry_prop=toy, carry_side=c_side)
        
        ty_start = toy.y
        for i in range(8):
            toy.y = ty_start + i * ((252 - ty_start)/8)
            toy.x = self.center_prop.x + (-20 if stop_x < CENTER_X else 20)
            if helper.start_x < CENTER_X: helper.arm_target_r = (toy.x, toy.y)
            else: helper.arm_target_l = (toy.x, toy.y)
            self.anim.snap()
            
        helper.arm_target_l = helper.arm_target_r = None
        self.center_prop.expression = Expression.HAPPY
        self.anim.pause(0.5)
        
        self._give_reward(helper)

    def _toy_punish_phase(self, mischief):
        toy = Prop("toy", self.center_prop.x - 20, 252, True)
        self.props.append(toy); self.anim.pause(0.8)
        
        stop_x = self.center_prop.x - 70 if mischief.start_x < CENTER_X else self.center_prop.x + 70
        self.anim.move(mischief, stop_x, 227, Timing.MOVE_DURATION)
        
        if mischief.start_x < CENTER_X: mischief.arm_target_r = (toy.x, toy.y)
        else: mischief.arm_target_l = (toy.x, toy.y)
        self.anim.pause(0.5); self.anim.snap()
        
        target_x = mischief.x + (-45 if mischief.start_x < CENTER_X else 45)
        target_y = mischief.y - 30
        
        self.center_prop.expression = Expression.SAD
        
        frames = 8
        ty_start, tx_start = toy.y, toy.x
        for i in range(1, frames+1):
            toy.x = tx_start + (target_x - tx_start) * (i/frames)
            toy.y = ty_start + (target_y - ty_start) * (i/frames)
            if i < frames/2:
                if mischief.start_x < CENTER_X: mischief.arm_target_r = (toy.x, toy.y)
                else: mischief.arm_target_l = (toy.x, toy.y)
            else:
                if mischief.start_x < CENTER_X: mischief.arm_target_l = (toy.x, toy.y)
                else: mischief.arm_target_r = (toy.x, toy.y)
            self.anim.snap()
            
        self.anim.pause(0.2)
        
        return_x = mischief.start_x - 50 if mischief.start_x < CENTER_X else mischief.start_x + 50
        c_side = "left" if mischief.start_x < CENTER_X else "right"
        self.anim.move(mischief, return_x, 227, Timing.MOVE_DURATION, carry_prop=toy, carry_side=c_side)
        
        ty_start = toy.y
        for i in range(12):
            toy.y = min(252, ty_start + i * 6)
            if c_side == "left":
                mischief.arm_target_l = (toy.x, toy.y)
                mischief.arm_target_r = None
            else:
                mischief.arm_target_r = (toy.x, toy.y)
                mischief.arm_target_l = None
            self.anim.snap()
            
        mischief.arm_target_l = mischief.arm_target_r = None
        
        self._give_punishment(mischief)
        if toy in self.props: self.props.remove(toy)

    def _flower_reward_phase(self, helper):
        flower = self.center_prop
        self.anim.pause(0.8)
        
        # Agent approaches and "waters" (moves arm)
        stop_x = flower.x - 70 if helper.start_x < CENTER_X else flower.x + 70
        self.anim.move(helper, stop_x, 227, Timing.MOVE_DURATION)
        
        target_hand = (flower.x, flower.y + 10)
        if helper.start_x < CENTER_X: helper.arm_target_r = target_hand
        else: helper.arm_target_l = target_hand
        self.anim.pause(0.6)
        
        # Flower becomes happy and upright
        flower.expression = Expression.HAPPY
        self.anim.pause(0.5)
        
        helper.arm_target_l = helper.arm_target_r = None
        self._give_reward(helper)

    def _flower_punish_phase(self, mischief):
        flower = self.center_prop
        self.anim.pause(0.8)
        
        # Agent approaches and "steps on" (moves body over)
        stop_x = flower.x - 30 if mischief.start_x < CENTER_X else flower.x + 30
        self.anim.move(mischief, stop_x, 227, Timing.MOVE_DURATION)
        
        # "Stomp" move
        self.anim.move(mischief, flower.x, 220, 0.4)
        self.anim.move(mischief, flower.x, 227, 0.2)
        flower.expression = Expression.SAD # Wilts
        self.anim.pause(0.4)
        
        # Return slightly to give space for punisher
        return_x = flower.x - 70 if mischief.start_x < CENTER_X else flower.x + 70
        self.anim.move(mischief, return_x, 227, Timing.MOVE_DURATION)
        
        self._give_punishment(mischief)

    def _give_reward(self, helper):
        self.anim.move(self.authority, helper.x, helper.y - 140, Timing.MOVE_DURATION)
        self.authority.expression = Expression.HAPPY
        self.authority.arm_target_r = (helper.x, helper.y - (AGENT_SIZE/2) - 25)
        helper.has_star, helper.expression = True, Expression.HAPPY
        self.anim.pause(0.5)
        self.anim.jump(helper)
        self.anim.pause(0.5)
        self.anim.jump(helper)
        self.anim.pause(0.5)
        self.authority.arm_target_r = None; self.authority.expression = Expression.NEUTRAL
        self.anim.move(self.authority, CENTER_X, 60, Timing.MOVE_DURATION)
        self.anim.move(helper, helper.start_x, helper.start_y, Timing.MOVE_DURATION)

    def _give_punishment(self, mischief):
        self.anim.move(self.authority, mischief.x, mischief.y - 140, Timing.MOVE_DURATION)
        self.authority.expression = Expression.ANGRY
        self.authority.arm_target_r = (mischief.x, mischief.y - (AGENT_SIZE/2) - 25)
        start_gx = self.authority.x
        for i in range(15):
            self.authority.x = start_gx + 5 * math.sin(i*1.5); self.anim.snap()
        self.authority.x = start_gx
        mischief.has_star, mischief.expression = False, Expression.SAD; self.anim.pause(Timing.REWARD_DURATION)
        self.authority.arm_target_l = self.authority.arm_target_r = None
        self.authority.expression = Expression.NEUTRAL
        self.anim.move(self.authority, CENTER_X, 60, Timing.MOVE_DURATION)
        self.anim.move(mischief, mischief.start_x, mischief.start_y, Timing.MOVE_DURATION)

    def save(self, name):
        self.anim.frames[0].save(name, save_all=True, append_images=self.anim.frames[1:], duration=1000//FPS, loop=0)

if __name__ == "__main__":
    # Define 6 distinct agents for familiarization using colors that DO NOT overlap
    # with the Test Phase (which uses Teal, Red, Brown, Blue).
    A = {"shape": Shape.CIRCLE, "color": Color.PINK}
    B = {"shape": Shape.TRIANGLE, "color": Color.GREEN}
    C = {"shape": Shape.SQUARE, "color": Color.PURPLE}
    D = {"shape": Shape.CIRCLE, "color": Color.ORANGE}
    I_agent = {"shape": Shape.SQUARE, "color": Color.PINK}
    J_agent = {"shape": Shape.CIRCLE, "color": Color.GREEN}
    K_agent = {"shape": Shape.TRIANGLE, "color": Color.PURPLE}
    L_agent = {"shape": Shape.SQUARE, "color": Color.ORANGE}

    def generate_combo(scenes_config, out_filename):
        print(f"Generating {out_filename}...")
        all_frames = []
        trans = AnimationHelper(Renderer(), [], [])
        trans.blank(Timing.TRANSITION_BLANK)
        trans.ag(Timing.TRANSITION_AG)
        
        for idx, (pair, scene, is_reward) in enumerate(scenes_config):
            e = Experiment(pair[0], pair[1])
            e.run_scene_pair(scene, is_reward)
            all_frames.extend(e.anim.frames)
            
            if idx < len(scenes_config) - 1:
                all_frames.extend(trans.frames)
                
        all_frames[0].save(out_filename, save_all=True, append_images=all_frames[1:], duration=1000//FPS, loop=0)
        print(f"Exported {out_filename}")

    # The 4 baseline scenes and their dedicated pairs
    S1_Trash = ((A, B), "trash")
    S2_Tower = ((C, D), "tower")
    S3_Toy = ((I_agent, J_agent), "toy")
    S4_Flower = ((K_agent, L_agent), "flower")
    
    # Valence Set 1: Trash=Rew, Tower=Pun, Toy=Rew, Flower=Pun (2R, 2P)
    # Valence Set 2: Trash=Pun, Tower=Rew, Toy=Pun, Flower=Rew (2P, 2R)
    
    def apply_valences(scenes, set_num):
        out = []
        for i, (pair, scene) in enumerate(scenes):
            # Interleave reward and punishment
            if set_num == 1:
                is_rew = True if i % 2 == 0 else False
            else:
                is_rew = False if i % 2 == 0 else True
            out.append((pair, scene, is_rew))
        return out

    # Latin Square (ish) for 4 scenes
    order_1 = [S1_Trash, S2_Tower, S3_Toy, S4_Flower]
    order_2 = [S2_Tower, S3_Toy, S4_Flower, S1_Trash]
    order_3 = [S3_Toy, S4_Flower, S1_Trash, S2_Tower]
    order_4 = [S4_Flower, S1_Trash, S2_Tower, S3_Toy]

    generate_combo(apply_valences(order_1, 1), "Fam_Combo_1.gif")
    generate_combo(apply_valences(order_1, 2), "Fam_Combo_2.gif")
    generate_combo(apply_valences(order_2, 1), "Fam_Combo_3.gif")
    generate_combo(apply_valences(order_2, 2), "Fam_Combo_4.gif")
    generate_combo(apply_valences(order_3, 1), "Fam_Combo_5.gif")
    generate_combo(apply_valences(order_3, 2), "Fam_Combo_6.gif")
    # Adding more combos if needed for full balance
    generate_combo(apply_valences(order_4, 1), "Fam_Combo_7.gif")
    generate_combo(apply_valences(order_4, 2), "Fam_Combo_8.gif")
