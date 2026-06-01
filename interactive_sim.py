import os
import sys
import termios
import tty
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SANDBOX] - %(levelname)s - %(message)s')

def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def run_interactive_beam(target_port):
    try:
        target_fd = os.open(target_port, os.O_WRONLY)
        logging.info(f"Connected to virtual device at {target_port}")
    except Exception as e:
        print(f"Error: Couldn't open port {target_port}. Did you run the receiver in Window 2? ({e})")
        return

    x_pos = 32768
    y_pos = 32768
    step = 1000  

    print("\n=== Project S.B.A.R. Virtual Alignment Tool ===")
    print("Use W (Up), S (Down), A (Left), D (Right) to nudge the vector.")
    print("Press 'Q' to quit.\n")

    while True:
        key = get_key().lower()
        
        if key == 'q':
            print("\nExiting simulation.")
            break
        elif key == 'w':
            y_pos = min(65535, y_pos + step)
        elif key == 's':
            y_pos = max(0, y_pos - step)
        elif key == 'a':
            x_pos = max(0, x_pos - step)
        elif key == 'd':
            x_pos = min(65535, x_pos + step)
        else:
            continue

        packet = bytearray([
            0x55, 0xAA, 
            (x_pos >> 8) & 0xFF, x_pos & 0xFF, 
            (y_pos >> 8) & 0xFF, y_pos & 0xFF, 
            255, 
            (x_pos + y_pos) & 0xFF
        ])
        
        os.write(target_fd, packet)
        sys.stdout.write("\rCurrent Signal Position -> [DAC_X: {:5d} | DAC_Y: {:5d}]".format(x_pos, y_pos))
        sys.stdout.flush()

    os.close(target_fd)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 interactive_sim.py /dev/ttys006")
        sys.exit(1)
    run_interactive_beam(sys.argv[1])
