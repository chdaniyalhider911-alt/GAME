import cv2
import numpy as np
import time
import random
from collections import deque, Counter
import sys
import os
import urllib.request

# --- INITIAL COGNITIVE PACKETS ---
print("--- INITIALIZING MAIN COMBAT ROUTINE ---")

# Verify core MediaPipe installation availability
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
except ImportError:
    print("ERROR: MediaPipe is not installed or incomplete!")
    print("Please run: pip install mediapipe")
    sys.exit(1)

# Automated runtime model asset verification 
MODEL_PATH = "hand_landmarker.task"
if not os.path.exists(MODEL_PATH):
    print("Modern MediaPipe requires a local model asset file.")
    print("Downloading 'hand_landmarker.task' from Google servers...")
    try:
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        urllib.request.urlretrieve(url, MODEL_PATH)
        print("Download completed successfully!")
    except Exception as e:
        print(f"ERROR: Failed to download model file automatically: {e}")
        sys.exit(1)


class RockPaperScissorsBot:
    def __init__(self):
        print("Assembling UI Modules...")

        # Game state variables
        self.score_player = 0
        self.score_bot = 0
        self.round = 0
        self.game_state = "IDLE"
        self.countdown_start = 0
        self.detect_start = 0
        self.result_start = 0
        self.player_move = None
        self.bot_move = None
        self.result_text = ""
        self.result_color = (0, 0, 255)

        # History buffer for stabilizing gesture detection
        self.gesture_history = deque(maxlen=15)

        # Initialize webcam
        print("Powering up optics capture...")
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("CRITICAL ERROR: Optical feed failed to initialize!")
            sys.exit(1)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Initialize MediaPipe Tasks Hand Landmarker
        try:
            base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=1
            )
            self.detector = vision.HandLandmarker.create_from_options(options)
            print("Neural gesture tracking matrix: CALIBRATED.")
        except Exception as e:
            print(f"CRITICAL ENGINE FAULT: {e}")
            sys.exit(1)

        # Aggressive BGR Color Profiles
        self.NEON_RED = (0, 0, 255)
        self.NEON_GREEN = (0, 255, 0)
        self.FIRE_ORANGE = (0, 102, 255)
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.WARNING_YELLOW = (0, 235, 235)
        self.DARK_CHARCOAL = (10, 10, 15)

        print("\n=== SYSTEM ONLINE ===")
        print("CONTROLS: [SPACEBAR] = ENGAGE COMBAT | [Q] = ABORT SYSTEM")

    def classify_gesture(self, landmarks):
        """Analyze tracking node data stream to discover combat signatures."""
        if not landmarks:
            return 'UNKNOWN'
        
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        
        fingers = []
        for tip, pip in zip(tips, pips):
            extended = landmarks[tip].y < landmarks[pip].y
            fingers.append(extended)
        
        extended_count = sum(fingers)
        
        if extended_count == 0:
            return 'ROCK'
        elif extended_count == 2 and fingers[0] and fingers[1]:
            return 'SCISSORS'
        elif extended_count >= 4:
            return 'PAPER'
        else:
            return 'UNKNOWN'

    def draw_ui(self, frame, gesture='UNKNOWN', hand_detected=False):
        """Applies headers, scores, trackers, and combat canvas elements."""
        h, w = frame.shape[:2]
        
        # Gritty dark ambient background dimming 
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), self.DARK_CHARCOAL, -1)
        cv2.addWeighted(frame, 0.65, overlay, 0.35, 0, frame)
        
        # --- TRACKING CONSOLE HEADER (Top Left) ---
        cv2.rectangle(frame, (15, 15), (280, 105), self.BLACK, -1)
        cv2.rectangle(frame, (15, 15), (280, 105), self.NEON_RED, 3)
        
        status, color = ("TARGET LOCKED", self.NEON_GREEN) if hand_detected else ("SCANNING FOR TARGET...", self.NEON_RED)
        cv2.putText(frame, status, (25, 45), cv2.FONT_HERSHEY_TRIPLEX, 0.55, color, 1, cv2.LINE_AA)
        cv2.putText(frame, f"SIGNATURE: {gesture}", (25, 85), cv2.FONT_HERSHEY_TRIPLEX, 0.55, self.WHITE, 1, cv2.LINE_AA)
        
        # --- COMBAT SCOREBOARD (Top Right) ---
        cv2.rectangle(frame, (w - 235, 15), (w - 15, 105), self.BLACK, -1)
        cv2.rectangle(frame, (w - 235, 15), (w - 15, 105), self.NEON_RED, 3)
        cv2.putText(frame, f"PLAYER : {self.score_player}", (w - 215, 45), cv2.FONT_HERSHEY_TRIPLEX, 0.6, self.NEON_GREEN, 2, cv2.LINE_AA)
        cv2.putText(frame, f"BOT CPU: {self.score_bot}", (w - 215, 85), cv2.FONT_HERSHEY_TRIPLEX, 0.6, self.NEON_RED, 2, cv2.LINE_AA)
        
        # --- LOWER INFOBAR ---
        cv2.putText(frame, f"STAGE STRIKE: {self.round + 1}", (20, h - 15), cv2.FONT_HERSHEY_TRIPLEX, 0.45, self.WHITE, 1, cv2.LINE_AA)
        cv2.putText(frame, "[SPACE] UNLEASH HELL | [Q] ESCAPE", (w - 335, h - 15), cv2.FONT_HERSHEY_TRIPLEX, 0.45, self.NEON_RED, 1, cv2.LINE_AA)
        
        # --- STATE MACHINE GRAPHICS CORE (Lower Third Area) ---
        if self.game_state == "IDLE":
            self.draw_hud_text(frame, "READY TO FIGHT", self.FIRE_ORANGE, 1.2, thickness=3)
            self.draw_hud_text(frame, "\n\nPRESS SPACEBAR TO ENGAGE", self.WHITE, 0.55, thickness=1)
            
        elif self.game_state == "COUNTDOWN":
            elapsed = time.time() - self.countdown_start
            if elapsed < 1.0:
                self.draw_hud_text(frame, "READY...", self.FIRE_ORANGE, 2.0, thickness=4)
            elif elapsed < 2.0:
                self.draw_hud_text(frame, "SET...", self.WARNING_YELLOW, 2.0, thickness=4)
            elif elapsed < 3.0:
                self.draw_hud_text(frame, "STRIKE!", self.NEON_RED, 2.5, thickness=5)
            else:
                self.draw_hud_text(frame, "SHOOT!", self.NEON_GREEN, 2.5, thickness=5)
                
        elif self.game_state == "DETECTING":
            self.draw_hud_text(frame, "EXTRACTING MOVE...", self.WARNING_YELLOW, 1.3, thickness=3)
            
        elif self.game_state == "RESULT":
            # Flash border around the screen edge based on round outcome
            cv2.rectangle(frame, (0, 0), (w, h), self.result_color, 12)
            
            box_w, box_h = 480, 160
            box_x = (w - box_w) // 2
            box_y = h - box_h - 45 
            
            # Heavy panel graphic
            cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), self.BLACK, -1)
            cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), self.result_color, 4)
            
            cv2.putText(frame, f"YOUR ATTACK: {self.player_move}", (box_x + 30, box_y + 40), 
                        cv2.FONT_HERSHEY_TRIPLEX, 0.6, self.NEON_GREEN, 2, cv2.LINE_AA)
            cv2.putText(frame, f"BOT DEFENSE: {self.bot_move}", (box_x + 30, box_y + 80), 
                        cv2.FONT_HERSHEY_TRIPLEX, 0.6, self.NEON_RED, 2, cv2.LINE_AA)
            
            text_size = cv2.getTextSize(self.result_text, cv2.FONT_HERSHEY_TRIPLEX, 1.1, 3)[0]
            msg_x = box_x + (box_w - text_size[0]) // 2
            cv2.putText(frame, self.result_text, (msg_x, box_y + 135), 
                        cv2.FONT_HERSHEY_TRIPLEX, 1.1, self.result_color, 3, cv2.LINE_AA)
        
        return frame

    def draw_hud_text(self, frame, text, color, scale, thickness=3):
        """Utility function drawing alert lines cleanly into the lower-third zone."""
        h, w = frame.shape[:2]
        lines = text.split('\n')
        
        start_y = int(h * 0.72)
        current_y = start_y
        
        for line in lines:
            if not line.strip():
                current_y += int(30 * scale)
                continue
            size = cv2.getTextSize(line, cv2.FONT_HERSHEY_TRIPLEX, scale, thickness)[0]
            x = (w - size[0]) // 2
            
            # Semi-transparent backing rectangle behind text lines
            cv2.rectangle(frame, (x - 15, current_y - size[1] - 10), (x + size[0] + 15, current_y + 10), self.BLACK, -1)
            
            cv2.putText(frame, line, (x, current_y), cv2.FONT_HERSHEY_TRIPLEX, scale, color, thickness, cv2.LINE_AA)
            current_y += size[1] + 15

    def determine_winner(self, player, bot):
        """Evaluates game rules using intense combat-styled responses."""
        if player == bot:
            return "STALEMATE!", self.WHITE
        
        rules = {'ROCK': 'SCISSORS', 'PAPER': 'ROCK', 'SCISSORS': 'PAPER'}
        
        if rules[player] == bot:
            self.score_player += 1
            return "BOT CRUSHED!", self.NEON_GREEN
        else:
            self.score_bot += 1
            return "YOU WASTED!", self.NEON_RED

    def draw_landmarks(self, frame, hand_landmarks):
        """Draws a sharper neon skeletal frame model."""
        h, w, _ = frame.shape
        points = []
        
        for lm in hand_landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            points.append((cx, cy))
            cv2.circle(frame, (cx, cy), 4, self.NEON_RED, -1)
            
        connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),
            (5, 6), (6, 7), (7, 8),
            (9, 10), (10, 11), (11, 12),
            (13, 14), (14, 15), (15, 16),
            (17, 18), (18, 19), (19, 20),
            (0, 5), (5, 9), (9, 13), (13, 17), (17, 0)
        ]
        
        for start, end in connections:
            if start < len(points) and end < len(points):
                cv2.line(frame, points[start], points[end], self.WHITE, 2, cv2.LINE_AA)

    def run(self):
        """Camera loop execution run block."""
        print("\n==============================")
        print("      ARENA INITIALIZED")
        print("==============================")

        # Unlocks complete window scale modification properties
        cv2.namedWindow("Rock Paper Scissors", cv2.WINDOW_NORMAL)

        while True:
            ret, frame = self.cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            try:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                detection_result = self.detector.detect(mp_image)
            except Exception as e:
                print(f"Skipping telemetry packet frame anomaly: {e}")
                continue
            
            hand_detected = False
            current_gesture = 'UNKNOWN'
            
            if detection_result.hand_landmarks:
                hand_detected = True
                for hand_landmarks in detection_result.hand_landmarks:
                    self.draw_landmarks(frame, hand_landmarks)
                    current_gesture = self.classify_gesture(hand_landmarks)
                    self.gesture_history.append(current_gesture)
            
            # Core Combat State Driver Logic
            if self.game_state == "COUNTDOWN":
                if time.time() - self.countdown_start >= 3.5:
                    self.game_state = "DETECTING"
                    self.detect_start = time.time()
                    self.gesture_history.clear()
            
            elif self.game_state == "DETECTING":
                if time.time() - self.detect_start >= 0.5:
                    if len(self.gesture_history) > 0:
                        gesture_counts = Counter(self.gesture_history)
                        self.player_move = gesture_counts.most_common(1)[0][0]
                    else:
                        self.player_move = 'UNKNOWN'
                    
                    self.bot_move = random.choice(['ROCK', 'PAPER', 'SCISSORS'])
                    
                    if self.player_move == 'UNKNOWN':
                        self.result_text = "CRITICAL FAILURE!"
                        self.result_color = self.NEON_RED
                    else:
                        self.result_text, self.result_color = self.determine_winner(
                            self.player_move, self.bot_move
                        )
                        self.round += 1
                    
                    self.game_state = "RESULT"
                    self.result_start = time.time()
            
            elif self.game_state == "RESULT":
                if time.time() - self.result_start >= 3.0:
                    self.game_state = "IDLE"
                    self.gesture_history.clear()
            
            # Output Display Frame Refresh
            frame = self.draw_ui(frame, current_gesture, hand_detected)
            cv2.imshow("Rock Paper Scissors", frame)
            
            # System Event Interrupt Monitor
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord(' ') and self.game_state == "IDLE":
                self.game_state = "COUNTDOWN"
                self.countdown_start = time.time()
                self.gesture_history.clear()
                print(f"BATTLE ENGAGED: Round {self.round + 1}")

        # Resource termination execution lifecycle handlers
        self.detector.close()
        self.cap.release()
        cv2.destroyAllWindows()
        print("\n==============================")
        print(f"FINAL SCORE - YOU: {self.score_player} | BOT: {self.score_bot}")
        print("==============================")
        print("System shutdown completed.")


# --- CORE SYSTEM INVOKER BLOCK ---
def main():
    bot = RockPaperScissorsBot()
    bot.run()


if __name__ == "__main__":
    main()