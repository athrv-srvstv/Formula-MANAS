"""Central config and tunables for the gesture racer.

Everything you'd want to tweak (screen size, physics feel, gesture
sensitivity, colors) lives here so the other modules stay clean.
"""

import pygame

WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS = 60


BG_HEIGHT = 460
BG_Y_OFFSET = 40

BG_VERTICAL_PARALLAX = 0.35
BG_SEED = 1337            # fixed so both players see identical mountains

ROAD_W = 2000          # road half-width in world units
SEG_L = 200            # segment length (world units along Z)
CAM_D = 0.84           # camera depth (field-of-view-ish)
SHOW_N_SEG = 300       # how many segments ahead we draw
NUM_SEGMENTS = 1600    # total track length in segments

MAX_SPEED = 12000.0        # world units / second
ACCEL = 7000.0             # units / s^2 when throttle == 1
BRAKE = 12000.0            # units / s^2 when throttle < 0
FRICTION = 3000.0          
OFFROAD_MAX_SPEED = 4500.0 
STEER_RESPONSE = 8.0       

STEER_STRENGTH = 0.65

CENTRIFUGAL = 0.30

X_BOUND = 4300.0

DARK_GRASS = pygame.Color(0, 154, 0)
LIGHT_GRASS = pygame.Color(16, 200, 16)
WHITE_RUMBLE = pygame.Color(255, 255, 255)
BLACK_RUMBLE = pygame.Color(0, 0, 0)
DARK_ROAD = pygame.Color(105, 105, 105)
LIGHT_ROAD = pygame.Color(107, 107, 107)
SKY_FILL = (105, 205, 240)

HOST_CAR = pygame.Color(210, 40, 40)     # red   (player who hosts)
CLIENT_CAR = pygame.Color(40, 90, 210)   # blue  (player who joins)


CAR_SCALE = 7.0           
CAR_MAX_TURN = 22.0       
CAR_LAYER_SPACING = 0.42  
                          
CAR_SWING = 1.8           
CAR_ROT_FACTOR = 0.25     
CAR_FRONT_ANCHORED = False  
CAR_DRIFT_PX = 22.0       

CAR_HALF_WIDTH = 500.0     
CAR_LENGTH = 900.0         
PROP_HALF_WIDTH = 420.0    

CRASH_DURATION = 1.1       
CRASH_SPEED_KEEP = 0.18    
BUMP_SPEED_KEEP = 0.72     
CRASH_STEER_SPIN = 0.35
CRASH_FLASH_TIME = 0.45    
CRASH_GRACE = 1.2          
SCENERY_WALL_X = 2100.0
SCENERY_WALL_ENABLED = True
CRASH_SHAKE_PX = 14.0      # screen-shake amplitude at impact


PROP_MIN_OFFSET = 2.8     # never place a prop closer to center than this

PROP_MAX_UPSCALE = 2.5

PROP_COLLIDE_RATIO = 2.6

DEFAULT_PORT = 50007

NET_INTERP_DELAY = 0.10    
NET_INTERP_ENABLED = True  


WHEEL_MAX_DEG = 55.0


THROTTLE_GRIP_NARROW = 0.40
THROTTLE_GRIP_WIDE = 0.75
THROTTLE_DEADZONE = 0.15   # fraction of the range treated as "coast"


THROTTLE_CALIBRATE_SPAN = 0.18   


THROTTLE_HOLD_ON_LOST = False

GESTURE_SMOOTHING = 0.4    
SHOW_CAMERA_DEBUG = True   