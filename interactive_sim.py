import os
import sys
import termios
import tty
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SANDBOX] - %(levelname)s - %(message)s')

def send_packet(target_fd, x, y, intensity):
    # Match the firmware's exact sync bytes: 0xAA, 0xBB
    packet = bytearray([
        0xAA, 0xBB, 
        (x >> 8) & 0xFF, x & 0xFF, 
        (y >> 8) & 0xFF, y & 0xFF, 
        intensity, 
        (x + y) & 0xFF
    ])
    os.write(target_fd, packet)
    try:
        os.fsync(target_fd)
    except OSError:
        pass

def run_aligned_sim(target_port):
    try:
        target_fd = os.open(target_port, os.O_WRONLY | os.O_NONBLOCK)
        logging.info(f"Connected to virtual device at {target_port}")
    except Exception as e:
        print(f"Error: Couldn't open port {target_port}. ({e})")
        return

    x_pos, y_pos = 32768, 32768
    step = 1500
    mode = "MANUAL"

    square_corners = [
        (22768, 22768),
        (42768, 22768),
        (42768, 42768),
        (22768, 42768)
    ]
    corner_index = 0

    print("\n=== Project S.B.A.R. Aligned Hardware Bench ===")
    print("Mode Switches:  [M] Manual Mode  |  [A] Auto Square Loop")
    print("Manual Keys:    W (Up), S (Down), A (Left), D (Right)")
    print("Exit:           Press [Q] to quit.")
    print("-" * 50)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)
    os.set_blocking(fd, False)

    try:
        while True:
            try:
                key = sys.stdin.read(1).lower()
            except TypeError:
                key = None

            if key:
                if key == 'q':
                    mode = "QUIT"
                elif key == 'm':
                    mode = "MANUAL"
                elif key == 'a':
                    mode = "AUTO"
                
                if mode == "MANUAL":
                    if key == 'w': y_pos = min(65535, y_pos + step)
                    elif key == 's': y_pos = max(0, y_pos - step)
                    elif key == 'a': x_pos = max(0, x_pos - step)
                    elif key == 'd': x_pos = min(65535, x_pos + step)
                    send_packet(target_fd, x_pos, y_pos, 255)

            if mode == "QUIT":
                print("\nExiting simulator.")
                break

            if mode == "AUTO":
                x_pos, y_pos = square_corners[corner_index]
                send_packet(target_fd, x_pos, y_pos, 255)
                corner_index = (corner_index + 1) % 4
                time.sleep(0.1)

            sys.stdout.write(f"\r[{mode}] Transmitting -> X: {x_pos:5d} | Y: {y_pos:5d}")
            sys.stdout.flush()
            time.sleep(0.02)

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        os.close(target_fd)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 interactive_sim.py /dev/ttys001")
        sys.exit(1)
    run_aligned_sim(sys.argv[1])
