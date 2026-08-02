
import pygame


class KeyboardInput:
   

    name = "keyboard"

    def read(self):
        keys = pygame.key.get_pressed()
        steer = 0.0
        throttle = 0.0
        if keys[pygame.K_LEFT]:
            steer -= 1.0
        if keys[pygame.K_RIGHT]:
            steer += 1.0
        if keys[pygame.K_UP]:
            throttle += 1.0
        if keys[pygame.K_DOWN]:
            throttle -= 1.0
        return steer, throttle

    def calibrate(self):
        
        pass

    def close(self):
        pass


def make_input(prefer_gesture: bool):
    
    if prefer_gesture:
        try:
            from gestures import GestureInput
            gi = GestureInput()
            if gi.ok:
                print("[input] gesture control active (hold the invisible wheel)")
                return gi
            gi.close()
        except Exception as e:  # noqa: BLE001 - want any failure to fall back
            print(f"[input] gesture control unavailable: {type(e).__name__}: {e}")
            print("[input] run 'python diagnose_gestures.py' to see why")
    print("[input] keyboard control active (arrow keys)")
    return KeyboardInput()