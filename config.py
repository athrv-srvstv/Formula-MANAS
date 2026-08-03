

import pygame

WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS = 60


BG_HEIGHT = 460
BG_Y_OFFSET = 40

BG_VERTICAL_PARALLAX = 0.35
BG_SEED = 1337            

ROAD_W = 2000          # road half-width in world units
SEG_L = 200            # segment length (world units along Z)
CAM_D = 0.84           
SHOW_N_SEG = 300       
NUM_SEGMENTS = 1600    

MAX_SPEED = 12000.0        # world units / second
ACCEL = 7000.0             
BRAKE = 12000.0            
FRICTION = 3000.0          # passive slowdown / s^2 (no throttle)
OFFROAD_MAX_SPEED = 4500.0 # speed cap when off the tarmac
STEER_RESPONSE = 8.0       
STEER_STRENGTH = 0.65

CENTRIFUGAL = 0.30

X_BOUND = 5300.0

DARK_GRASS = pygame.Color(0, 154, 0)
LIGHT_GRASS = pygame.Color(16, 200, 16)
WHITE_RUMBLE = pygame.Color(255, 255, 255)
BLACK_RUMBLE = pygame.Color(0, 0, 0)
DARK_ROAD = pygame.Color(105, 105, 105)
LIGHT_ROAD = pygame.Color(107, 107, 107)
SKY_FILL = (105, 205, 240)

HOST_CAR = pygame.Color(210, 40, 40)     # red   (player who hosts)
CLIENT_CAR = pygame.Color(40, 90, 210)   # blue  (player who joins)


CAR_SCALE = 7.0           # pixel multiplier on the 20x12 native art
CAR_MAX_TURN = 22.0       # degrees of steering angle at full lock
CAR_LAYER_SPACING = 0.42 
CAR_SWING = 0.8           # how far the nose swings out when turning
CAR_ROT_FACTOR = 0.25     # extra per-slice tilt; 0 = off
CAR_FRONT_ANCHORED = False  
CAR_DRIFT_PX = 22.0       # how far the whole car slides toward the turn

CAR_HALF_WIDTH = 380.0     # player car half-width in WORLD units
CAR_LENGTH = 900.0         # Z extent for car-vs-car overlap
PROP_HALF_WIDTH = 110.0    
PROP_DEPTH_SEGMENTS = 3
                           #   raise = harder to squeeze past trees

CRASH_DURATION = 0.55      # seconds of lost control after a tree
CRASH_SPEED_KEEP = 0.45    
BUMP_SPEED_KEEP = 0.72     
CRASH_STEER_SPIN = 0.35
CRASH_FLASH_TIME = 0.45    
CRASH_GRACE = 0.9          # seconds of invulnerability after a crash


SCENERY_WALL_X = 3200.0
SCENERY_WALL_ENABLED = True
CRASH_SHAKE_PX = 14.0      # screen-shake amplitude at impact


PROP_ROWS_X = (3300.0, 3500.0, 4200.0)
PROP_WORLD_WIDTH = 700.0   # how wide a tree is, in world units

PROP_HALF_WIDTH = 350.0
PROP_MIN_OFFSET = 2.1
PROP_COLLIDE_RATIO = 0.9


PROP_DEPTH_SEGMENTS = 3


PROP_MAX_UPSCALE = 2.5

DEFAULT_PORT = 50007

NET_INTERP_DELAY = 0.10    # seconds
NET_INTERP_ENABLED = True  # False -> snap to raw packets (to compare)


WHEEL_MAX_DEG = 55.0


THROTTLE_GRIP_NARROW = 0.45
THROTTLE_GRIP_WIDE = 0.65
THROTTLE_DEADZONE = 0.25   # fraction of the range treated as "coast"


THROTTLE_CALIBRATE_SPAN = 0.28   
THROTTLE_HOLD_ON_LOST = False

GESTURE_SMOOTHING = 0.4    # 0..1 low-pass on gesture values
SHOW_CAMERA_DEBUG = True   # pop a small OpenCV window with the tracked wheel



DUST_RATE_LAUNCH = 90.0     # wheelspin when flooring it from low speed
DUST_RATE_BRAKE = 130.0     # heavy braking
DUST_RATE_CORNER = 70.0     # tyre scrub while turning at speed
DUST_RATE_OFFROAD = 55.0    # just from driving on dirt
DUST_OFFROAD_MULT = 2.2     # everything kicks up more off the tarmac

DUST_LAUNCH_SPEED_FRAC = 0.35   # "low speed" = below this fraction of MAX
DUST_BRAKE_ACCEL = 2500.0       # deceleration (units/s^2) that counts as braking
DUST_STEER_MIN = 0.35           # steering past this scrubs the tyres

DUST_VY_BACK = 75.0         # initial downward/backward push (screen px/s)
DUST_VX_CORNER = 150.0      # sideways throw when cornering
DUST_JITTER = 55.0          # random velocity spread
DUST_SPREAD = 70.0          # horizontal spawn spread across the rear axle
DUST_DRAG = 2.4             # how fast particles lose momentum
DUST_RISE = 26.0            # upward drift (px/s^2), dust hangs and lifts
DUST_GROWTH = 13.0          # px/s the puff expands as it diffuses


DUST_LIFE = (0.15, 1.5)     # seconds
DUST_SIZE = (2.6, 6.0)      # starting radius in px
DUST_ALPHA = 200             # peak opacity (0-255); lower = subtler
DUST_TINT_ROAD = (130, 165) # grey-ish grit on tarmac
DUST_TINT_DIRT = (150, 185) # browner dust off-road
DUST_MAX = 1000              # hard cap on live particles