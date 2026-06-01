import os
import sys
import termios
import tty
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SANDBOX] - %(levelname)s - %(message)s')

def get_key():
    """Reads a single keypress without waiting for Enter."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def send_packet(target_fd, x, y, intensity):
    """Packs and writes a standard 8-byte Project S.B.A.R. hardware frame."""
    packet = bytearray([
        0x55, 0xAA, 
        (x >> 8) & 0xFF, x & 0xFF, 
        (y >> 8) & 0xFF, y & 0xFF, 
        intensity, 
        (x + y) & 0xFF
    ])
    os.write(target_fd, packet)

def run_combined_sim(target_port):
    try:
        target_fd = os.open(target_port, os.O_WRONLY | os.O_NONBLOCK)
        logging.info(f"Connected to virtual device at {target_port}")
    except Exception as e:
        print(f"Error: Couldn't open port {target_port}. Did you run the receiver in Window 2? ({e})")
        return

    # Default baseline center
    x_pos, y_pos = 32768, 32768
    step = 1500
    mode = "MANUAL"

    # Define a clean bounding box for the auto square loop
    # Center is 32768, so we sweep between 22768 and 42768
    square_corners = [
        (22768, 22768),  # Bottom Left
        (42768, 22768),  # Bottom Right
        (42768, 42768),  # Top Right
        (22768, 42768)   # Top Left
    ]
    corner_index = 0

    print("\n=== Project S.B.A.R. Dual-Mode Control Bench ===")
    print("Mode Switches:  [M] Manual Mode  |  [A] Auto Square Loop")
    print("Manual Keys:    W (Up), S (Down), A (Left), D (Right)")
    print("Exit:           Press [Q] to quit.")
    print("-" * 50)

    # Set stdin to non-blocking so we can loop safely in Auto mode
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)
    os.set_blocking(fd, False)

    try:
        while True:
            # Check for keyboard input without stalling the loop
            try:
                key = sys.stdin.read(1).lower()
            except TypeError:
                key = None

            if key:
                if key == 'q':
                    mode = "QUIT"
                elif key == 'm':
                    mode = "MANUAL"
                    sys.stdout.write("\n>> Switched to MANUAL mode. Use WASD.\n")
                elif key == 'a':
                    mode = "AUTO"
                    sys.stdout.write("\n>> Switched to AUTO mode. Tracing square...\n")
                
                # Manual WASD processing
                if mode == "MANUAL":
                    if key == 'w': y_pos = min(65535, y_pos + step)
                    elif key == 's': y_pos = max(0, y_pos - step)
                    elif key == 'a': x_pos = max(0, x_pos - step)
                    elif key == 'd': x_pos = min(65535, x_pos + step)
                    send_packet(target_fd, x_pos, y_pos, 255)

            if mode == "QUIT":
                print("\nExiting simulator.")
                break

            # If in Auto Mode, cycle through the geometry tracking nodes
            if mode == "AUTO":
                x_pos, y_pos = square_corners[corner_index]
                send_packet(target_fd, x_pos, y_pos, 255)
                
                # Advance to next target node
                corner_index = (corner_index + 1) % 4
                time.sleep(0.1)  # 100ms sweep delay to simulate mirror velocity limits

            # Keep the bench operator updated on coordinates
            sys.stdout.write(f"\r[{mode}] Active Signal Target -> X: {x_pos:5d} | Y: {y_pos:5d}")
            sys.stdout.flush()
            time.sleep(0.02)

    finally:
        # Revert terminal settings back to normal safely
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        os.close(target_fd)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 interactive_sim.py /dev/ttys006")
        sys.exit(1)
    run_combined_sim(sys.argv[1])
