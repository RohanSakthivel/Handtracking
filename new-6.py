import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import mediapipe as mp
import threading
import time

# Initialize MediaPipe Hand module
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# Define the coordinates for each reduced-size box
boxes = {
    "box1": [(50, 50), (250, 250)],
    "box2": [(50, 300), (250, 500)],
    "box3": [(300, 50), (500, 250)],
    "box4": [(300, 300), (500, 500)]
}

# Define the steps for SOP verification
sop_steps = [
    ["box1"],
    ["box2", "box3"],
    ["box4"]
]

class VerificationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Box Verification")
        self.root.geometry("1400x800")

        # Style configuration
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Arial', 12), padding=10)
        self.style.configure('TLabel', font=('Arial', 12))
        self.style.configure('TFrame', background='#f0f0f0')

        # Create the UI elements
        self.create_ui()

        # Initialize camera and hand tracking
        self.initialize_camera()
        self.running = False
        self.assemble_count = 0

        # Initialize the SOP step index
        self.current_step_index = 0
        self.alert_on = False  # To track the alert status
        self.last_alert_time = time.time()  # Time of the last alert
        self.alert_cooldown = 1  # Cooldown period for alerts in seconds

    def create_ui(self):
        main_frame = tk.Frame(self.root, bg='#f5f5f5')
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.instruction_sidebar = tk.Frame(main_frame, width=250, bg='#ffffff', padx=20, pady=20, borderwidth=2, relief='flat')
        self.instruction_sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=20, pady=20)

        self.instructions_label = tk.Label(self.instruction_sidebar, text="Instructions:", bg='#ffffff', fg='black', font=('Arial', 16, 'bold'))
        self.instructions_label.pack(pady=10)
        
        self.instructions_text = tk.Text(self.instruction_sidebar, wrap=tk.WORD, height=20, width=30, font=('Arial', 12), bg='#f0f0f0', borderwidth=1, relief='flat')
        self.instructions_text.pack(pady=10)
        self.instructions_text.insert(tk.END, "1. Place the oilcooler in the designated area.\n")
        self.instructions_text.insert(tk.END, "2. Position the gasket correctly.\n")
        self.instructions_text.insert(tk.END, "3. Ensure the casing is aligned properly.\n")
        self.instructions_text.insert(tk.END, "4. Click 'Start Verification' to begin the process.\n")
        self.instructions_text.config(state=tk.DISABLED)

        self.video_frame = tk.Frame(main_frame, bg='#ffffff', borderwidth=2, relief='flat')
        self.video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.canvas = tk.Canvas(self.video_frame, width=600, height=450, bg='#ffffff')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.verification_sidebar = tk.Frame(main_frame, width=400, bg='#ffffff', padx=20, pady=20, borderwidth=2, relief='flat')
        self.verification_sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=20)

        self.logo_image = Image.open('logo.png')  # Ensure logo.png is in the same directory or provide the full path
        self.logo_photo = ImageTk.PhotoImage(self.logo_image.resize((200, 100)))  # Resize the logo if needed
        self.logo_label = tk.Label(self.verification_sidebar, image=self.logo_photo, bg='#ffffff', pady=10)
        self.logo_label.pack(pady=10)

        self.start_button = tk.Button(self.verification_sidebar, text="Start Verification", command=self.start_verification,
                                      bg='#4CAF50', fg='white', font=('Arial', 14, 'bold'), relief='raised', borderwidth=1,
                                      padx=15, pady=10, activebackground='#45a049')
        self.start_button.pack(pady=20, fill=tk.X)
        self.start_button.bind("<Enter>", self.on_hover)
        self.start_button.bind("<Leave>", self.on_leave)

        self.box_status_labels = {}
        for box in boxes:
            label = tk.Label(self.verification_sidebar, text=f"{box}: Not Verified", bg='#f8d7da', fg='black', font=('Arial', 12),
                             anchor='w', padx=10, pady=10, relief='flat', borderwidth=1, width=30)
            label.pack(pady=5, fill=tk.X)
            self.box_status_labels[box] = label

        self.progress_frame = tk.Frame(self.verification_sidebar, bg='#ffffff', pady=20)
        self.progress_frame.pack(pady=20)

        self.progress_bar = tk.Canvas(self.progress_frame, width=200, height=30, bg='#e0e0e0', borderwidth=0,
                                      relief='flat')
        self.progress_bar.pack(pady=10, padx=10)
        self.progress_bar.create_rectangle(0, 0, 200, 30, fill='#e0e0e0', outline='#b0b0b0', width=0, tag="background")
        self.progress_fill = self.progress_bar.create_rectangle(0, 0, 0, 30, fill='#4CAF50', outline='#4CAF50', width=0,
                                                                 tag="fill")

        self.assemble_count_label = tk.Label(self.verification_sidebar, text=f"Assemble Count: 0", bg='#ffffff', fg='black',
                                             font=('Arial', 12, 'bold'))
        self.assemble_count_label.pack(pady=20)

    def initialize_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Could not open video capture.")
            self.root.quit()
        self.hands = mp_hands.Hands()

    def start_verification(self):
        if self.running:
            return
        
        self.running = True
        self.verified_boxes = {box: False for box in boxes}

        self.update_progress()

        self.verification_thread = threading.Thread(target=self.update_ui)
        self.verification_thread.start()

    def update_ui(self):
        frame_count = 0  # Frame count to control update frequency

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Failed to capture frame.")
                break

            frame_height, frame_width, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)

            # Draw boxes on the video frame
            for box_name, (start, end) in boxes.items():
                color = (0, 255, 0) if self.verified_boxes[box_name] else (0, 0, 255)
                cv2.rectangle(frame, start, end, color, 2)

            # Process hand landmarks
            if results.multi_hand_landmarks:
                for landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, landmarks, mp_hands.HAND_CONNECTIONS)
                    x = int(landmarks.landmark[mp_hands.HandLandmark.WRIST].x * frame_width)
                    y = int(landmarks.landmark[mp_hands.HandLandmark.WRIST].y * frame_height)

                    # Check if the hand is in the boxes of the current step
                    current_step_boxes = sop_steps[self.current_step_index]
                    for box_name in current_step_boxes:
                        if not self.verified_boxes[box_name] and self.is_hand_in_box(x, y, *boxes[box_name]):
                            self.verified_boxes[box_name] = True
                            self.update_status(box_name, "Verified")
                            self.update_progress()

                    # Check if the hand is in any box not currently being verified
                    out_of_sequence = False
                    for box_name in boxes:
                        if box_name not in current_step_boxes and self.is_hand_in_box(x, y, *boxes[box_name]):
                            out_of_sequence = True
                            self.set_sidebar_alert(out_of_sequence)
                            break

                    # If all boxes in the current step are verified, move to the next step
                    if all(self.verified_boxes[box] for box in current_step_boxes):
                        self.current_step_index += 1

                        # If all steps are completed
                        if self.current_step_index >= len(sop_steps):
                            self.current_step_index = 0
                            self.assemble_count += 1
                            self.assemble_count_label.config(text=f"Assemble Count: {self.assemble_count}")
                            self.reset_verification()

            # Update the frame in the Tkinter canvas
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            photo_frame = ImageTk.PhotoImage(image=Image.fromarray(rgb_frame))
            self.canvas.create_image(0, 0, image=photo_frame, anchor=tk.NW)
            self.canvas.image = photo_frame

            frame_count += 1
            if frame_count % 10 == 0:  # Update the UI every 10 frames
                self.root.update()

        self.cap.release()
        self.hands.close()

    def is_hand_in_box(self, x, y, start, end):
        return start[0] <= x <= end[0] and start[1] <= y <= end[1]

    def update_status(self, box_name, status):
        color = '#d4edda' if status == "Verified" else '#f8d7da'
        text = f"{box_name}: {status}"
        self.box_status_labels[box_name].config(text=text, bg=color)

    def update_progress(self):
        verified_count = sum(self.verified_boxes[box] for box in boxes)
        progress = int((verified_count / len(boxes)) * 200)  # Update the progress bar
        self.progress_bar.coords(self.progress_fill, (0, 0, progress, 30))

    def set_sidebar_alert(self, out_of_sequence):
        if out_of_sequence and (time.time() - self.last_alert_time >= self.alert_cooldown):
            self.instructions_text.config(state=tk.NORMAL)
            self.instructions_text.insert(tk.END, "Alert: Hand detected out of sequence!\n")
            self.instructions_text.config(state=tk.DISABLED)
            self.last_alert_time = time.time()

    def reset_verification(self):
        for box_name in self.verified_boxes:
            self.verified_boxes[box_name] = False
            self.update_status(box_name, "Not Verified")
        self.update_progress()
        self.current_step_index = 0

    def on_hover(self, event):
        self.start_button.config(bg='#45a049')

    def on_leave(self, event):
        self.start_button.config(bg='#4CAF50')

if __name__ == "__main__":
    root = tk.Tk()
    app = VerificationApp(root)
    root.mainloop()
