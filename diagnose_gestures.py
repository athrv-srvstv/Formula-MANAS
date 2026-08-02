
import os
import sys


def hr(title):
    print("\n" + "=" * 58)
    print(title)
    print("=" * 58)


def main():
    hr("1. Environment")
    print(f"python     : {sys.version.split()[0]}")
    print(f"cwd        : {os.getcwd()}")

    # A local file named mediapipe.py / cv2.py shadows the real package.
    for shadow in ("mediapipe.py", "cv2.py", "mediapipe", "cv2"):
        if os.path.exists(shadow):
            print(f"!! WARNING: '{shadow}' exists in this folder and will "
                  f"shadow the installed package. Rename it.")

    hr("2. OpenCV")
    try:
        import cv2
        print(f"OK  opencv  : {cv2.__version__}")
    except Exception as e:
        print(f"FAIL opencv : {type(e).__name__}: {e}")
        print("     fix    : pip install opencv-python")
        return

    hr("3. MediaPipe")
    try:
        import mediapipe as mp
        ver = getattr(mp, "__version__", "unknown")
        print(f"OK  mediapipe: {ver}")
        print(f"    location : {getattr(mp, '__file__', '?')}")
        has_sol = hasattr(mp, "solutions")
        has_tasks = hasattr(mp, "tasks")
        print(f"    mp.solutions present: {has_sol}")
        print(f"    mp.tasks     present: {has_tasks}")
        if not has_sol:
            print("    note: this is the known regression in recent builds;")
            print("          the Tasks backend below is the way around it.")
    except Exception as e:
        print(f"FAIL mediapipe: {type(e).__name__}: {e}")
        print("     fix     : pip install mediapipe")
        return

    hr("4. Hand-tracking backends")
    try:
        from hand_tracking import LegacyBackend, TasksBackend
    except Exception as e:
        print(f"FAIL import hand_tracking: {e}")
        return

    working = []
    for cls in (LegacyBackend, TasksBackend):
        try:
            b = cls()
            print(f"OK   {cls.__name__:<15} -> {b.name}")
            b.close()
            working.append(cls.__name__)
        except Exception as e:
            print(f"FAIL {cls.__name__:<15} -> {type(e).__name__}: {e}")

    hr("5. Camera")
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok:
                h, w = frame.shape[:2]
                print(f"OK  camera 0 opened, frame {w}x{h}")
            else:
                print("FAIL camera 0 opened but returned no frame")
            cap.release()
        else:
            print("FAIL could not open camera 0")
            print("     fix: close other apps using the webcam; on Linux")
            print("          check permissions on /dev/video0")
    except Exception as e:
        print(f"FAIL camera: {type(e).__name__}: {e}")

    hr("Verdict")
    if working:
        print(f"Gesture control should work via: {', '.join(working)}")
        print("Run:  python main.py --host")
    else:
        print("No backend available. Options:")
        print("  a) pip install 'mediapipe==0.10.21'   # older, has solutions")
        print("  b) check the Tasks error above (usually a failed model")
        print("     download -- needs internet on first run)")
        print("  c) play with --keyboard; everything else works fine")


if __name__ == "__main__":
    main()