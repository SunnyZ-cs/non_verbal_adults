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
# EXPERIMENT ORCHESTRATOR
# ==========================================

class TestTrialsExperiment:
    def __init__(self, c1_dict, c2_dict):
        self.r = Renderer()
        self.agent1 = Agent("Agent1", c1_dict["shape"], c1_dict["color"], 160, 227)
        self.agent2 = Agent("Agent2", c2_dict["shape"], c2_dict["color"], CENTER_X, 227)
        self.authority = Agent("authority", Shape.STAR, Color.YELLOW, CENTER_X, 60)
        
        # Place cube on right
        self.cube = BreakableCube(WIDTH - 100, GROUND_Y)
        
        self.props = [self.cube]
        self.anim = AnimationHelper(self.r, [self.agent1, self.agent2, self.authority], self.props)

    def reset_state(self):
        self.agent1.x, self.agent1.y = 160, 227
        self.agent2.x, self.agent2.y = CENTER_X, 227
        
        self.agent1.expression = Expression.NEUTRAL
        self.agent2.expression = Expression.NEUTRAL
        self.authority.expression = Expression.NEUTRAL
        
        self.cube.state = "whole"
        self.cube.fragments = []
        self.cube.visible = True

    def run_chain(self):
        # 1. Agent 1 (distal cause) does nothing, pause for 9/FPS seconds to keep frame alignment
        self.anim.pause(9 / FPS)
        
        # 2. Agent 2 (proximal cause) directly hits the Cube
        stop_x_2 = WIDTH - 100 - AGENT_SIZE + 5
        self.anim.move(self.agent2, stop_x_2, 227, 0.35) # direct hit
        
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
            
        self.anim.pause(1.5)
        
    def punish(self, target_agent):
        # 1. Authority descends above target at proper distance
        self.anim.move(self.authority, target_agent.x, target_agent.y - 140, Timing.MOVE_DURATION)
        self.authority.expression = Expression.ANGRY
        
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
        
        durations = [1000//FPS] * len(self.anim.frames)
        
        self.anim.frames[0].save(filename, save_all=True, append_images=self.anim.frames[1:], duration=durations, loop=0)
        
        png_filename = filename.replace('.gif', '_freeze.png')
        print(f"Exporting {png_filename}...")
        self.anim.frames[-1].save(png_filename)


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

    # Durations mapping
    d_distal = [1000//FPS] * len(distal_exp.anim.frames)
    
    d_proximal = [1000//FPS] * len(proximal_exp.anim.frames)
    
    d_trans = [1000//FPS] * len(trans.frames)

    # Test combo 1: Distal_Test_Final + Trans + Proximal_Test_Final
    c1_frames = distal_exp.anim.frames + trans.frames + proximal_exp.anim.frames
    c1_durations = d_distal + d_trans + d_proximal
    
    print("Exporting Test_Combo_1.gif...")
    c1_frames[0].save("Test_Combo_1.gif", save_all=True, append_images=c1_frames[1:], duration=c1_durations, loop=0)
    
    c1_png_filename = "Test_Combo_1_freeze.png"
    print(f"Exporting {c1_png_filename}...")
    c1_frames[-1].save(c1_png_filename)

    # Test combo 2: Proximal_Test_Final + Trans + Distal_Test_Final
    c2_frames = proximal_exp.anim.frames + trans.frames + distal_exp.anim.frames
    c2_durations = d_proximal + d_trans + d_distal
    
    print("Exporting Test_Combo_2.gif...")
    c2_frames[0].save("Test_Combo_2.gif", save_all=True, append_images=c2_frames[1:], duration=c2_durations, loop=0)
    
    c2_png_filename = "Test_Combo_2_freeze.png"
    print(f"Exporting {c2_png_filename}...")
    c2_frames[-1].save(c2_png_filename)
