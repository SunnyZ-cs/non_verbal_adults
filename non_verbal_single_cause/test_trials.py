import math
from PIL import ImageDraw
from familiarization_trials import (
    Color, Shape, Expression, Agent, Prop, Renderer, AnimationHelper, 
    Timing, FPS, WIDTH, HEIGHT, AGENT_SIZE, GROUND_Y
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
    
    if cube.state == "whole":
        # Draw solid block resting on the ground
        left, top, right, bottom = cube.x - size/2, cube.y - size, cube.x + size/2, cube.y
        draw.rectangle([left, top, right, bottom], fill="#868e96", outline=Color.BLACK.value, width=3)
        # Internal crease lines
        draw.line([cube.x, top, cube.x - size/4, cube.y], fill=Color.BLACK.value, width=2)
        draw.line([cube.x - size/4, cube.y - size/2, right, cube.y - size/3], fill=Color.BLACK.value, width=2)
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
            draw.polygon(rotated_pts, fill="#868e96", outline=Color.BLACK.value, width=2)

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
# EXPERIMENT ORCHESTRATOR
# ==========================================

class TestTrialsExperiment:
    def __init__(self, c1_dict, c2_dict):
        self.r = Renderer()
        self.agent1 = Agent("Agent1", c1_dict["shape"], c1_dict["color"], 100, 240)
        self.agent2 = Agent("Agent2", c2_dict["shape"], c2_dict["color"], 250, 240)
        self.green = Agent("green", Shape.SQUARE, Color.GREEN, 250, 60)
        
        # Place cube on right
        self.cube = BreakableCube(400, GROUND_Y)
        
        self.props = [self.cube]
        self.anim = AnimationHelper(self.r, [self.agent1, self.agent2, self.green], self.props)

    def reset_state(self):
        self.agent1.x, self.agent1.y = 100, 240
        self.agent2.x, self.agent2.y = 250, 240
        
        self.agent1.expression = Expression.NEUTRAL
        self.agent2.expression = Expression.NEUTRAL
        self.green.expression = Expression.NEUTRAL
        
        self.cube.state = "whole"
        self.cube.fragments = []
        self.cube.visible = True

    def run_chain(self):
        # 1. Agent 1 (distal cause) does nothing, pause for 0.15 seconds to keep timing alignment
        self.anim.pause(0.15)
        
        # 2. Agent 2 (proximal cause) directly hits the Cube
        stop_x_2 = 400 - AGENT_SIZE + 5
        self.anim.move(self.agent2, stop_x_2, 240, 0.15) # direct hit
        
        # 3. Cube Breaks Instantly!
        self.cube.state = "broken"
        self.cube.fragments = [
            (395, 230, -8, -15, 0),
            (405, 220, 5, -25, 45),
            (415, 235, 12, -20, 90),
            (385, 245, -15, -10, 15),
            (395, 250, -5, -30, 200),
            (405, 240, 3, -15, 75),
            (415, 255, 18, -12, -45),
            (390, 260, -2, -8, 120),
            (400, 265, 8, -5, 60),
            (420, 260, 22, -18, -90)
        ]
        
        # 4. Resolve Ballistic Shards
        gravity = 3
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
                    dx = dx * 0.75   # Friction slide smoothly
                    
                    if abs(dx) < 0.5: dx = 0
                
                if ndy != 0 or dx != 0:
                    active = True
                    
                new_frags.append((nfx, nfy, dx, ndy, nrot))
            self.cube.fragments = new_frags
            self.anim.snap()
            frame_count += 1
            
        self.anim.pause(1.5)
        
    def punish(self, target_agent):
        # 1. Green descends violently above target
        self.anim.move(self.green, target_agent.x, target_agent.y - 75, Timing.MOVE_DURATION)
        self.green.expression = Expression.ANGRY
        
        # 2. Green reaches straight down to grab the star
        star_x, star_y = target_agent.x + 45, target_agent.y - 45
        self.green.arm_target_r = (star_x, star_y)
        self.anim.pause(0.2) # Hold initial contact
        
        # 3. VIOLENT STRUGGLE / TENSION
        import random
        bases_gx, bases_gy = self.green.x, self.green.y
        bases_tx, bases_ty = target_agent.x, target_agent.y
        
        for _ in range(25): # ~1 second of violent shaking
            # Extreme jitter vectors
            gx_off = random.uniform(-6, 6)
            gy_off = random.uniform(-3, 3)
            tx_off = random.uniform(-4, 4)
            ty_off = random.uniform(-1, 1)
            
            self.green.x = bases_gx + gx_off
            self.green.y = bases_gy + gy_off
            
            target_agent.x = bases_tx + tx_off
            target_agent.y = bases_ty + ty_off
            target_agent.expression = Expression.SAD # Sad/Shocked during struggle
            
            # Keep Hand anchored to the shaking star location
            self.green.arm_target_r = (bases_tx + 45 + tx_off, bases_ty - 45 + ty_off)
            self.anim.snap()
            
        # Restore perfect resting anchors
        self.green.x, self.green.y = bases_gx, bases_gy
        target_agent.x, target_agent.y = bases_tx, bases_ty
        
        # FIERCE SNAP: Transfer Star
        target_agent.has_star = False
        target_agent.expression = Expression.SAD
        self.green.has_star = False # Star vanishes from screen completely!
        
        # Retract arm instantly to visually complete the physics of a fierce yank
        self.green.arm_target_r = None
        self.anim.pause(0.1) # Minimum pose settling

    def build_test_loop(self, target_agent, filename):
        self.agent1.has_star = True
        self.agent2.has_star = True
        self.reset_state()
        
        self.anim.pause(2.0) # Introduce initial scene with stars calmly
        
        # 3x Loop Iteration for Causal Chains
        for i in range(3):
            self.run_chain()
            
            # If not the last run, blank the screen to reset for next iteration
            if i < 2:
                self.anim.blank(Timing.TRANSITION_BLANK)
                self.reset_state()
                self.anim.pause(1.0) # Wait a second after resetting to show whole cube again
                
        # After runs, punish the designated agent
        self.punish(target_agent)
        
        # Finalize and Output
        print(f"Exporting {filename}...")
        
        # Embed the static 10 second pause natively to the last frame metadata 
        durations = [1000//FPS] * len(self.anim.frames)
        durations[-1] = 10000 
        
        self.anim.frames[0].save(filename, save_all=True, append_images=self.anim.frames[1:], duration=durations, loop=0)
        
        # Export freeze frame (the last frame of the animation)
        freeze_filename = filename.replace(".gif", "_freeze.png")
        self.anim.frames[-1].save(freeze_filename)
        print(f"Exporting freeze frame {freeze_filename}...")


if __name__ == "__main__":
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
    
    # ==========================
    # COMBO GENERATION
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
    c1_frames[0].save("Test_Combo_1.gif", save_all=True, append_images=c1_frames[1:], duration=c1_durations, loop=0)

    # Test combo 2: Proximal_Test_Final + Trans + Distal_Test_Final
    c2_frames = proximal_exp.anim.frames + trans.frames + distal_exp.anim.frames
    c2_durations = d_proximal + d_trans + d_distal
    
    print("Exporting Test_Combo_2.gif...")
    c2_frames[0].save("Test_Combo_2.gif", save_all=True, append_images=c2_frames[1:], duration=c2_durations, loop=0)
