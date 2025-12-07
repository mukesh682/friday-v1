import os
import time
import datetime
import base64
import cv2
import pyttsx3
import speech_recognition as sr
import serial
import ollama


# ==================================================================================
# CONFIGURATION
# ==================================================================================
class Config:
    WAKE_WORD = "friday"
    BRAIN_MODEL = "llama3"  # Standard chat model
    VISION_MODEL = "llava"  # Vision capable model
    SERIAL_PORT = "COM3"  # Change to your Arduino Port (e.g., '/dev/ttyUSB0' on Linux)
    BAUD_RATE = 9600
    CAMERA_INDEX = 0  # 0 is usually the default webcam


# ==================================================================================
# MODULE 1: THE MOUTH (Text-to-Speech)
# ==================================================================================
class VoiceEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.voices = self.engine.getProperty('voices')
        # Attempt to set a male voice (usually index 0 on Windows)
        self.engine.setProperty('voice', 'com.apple.speech.synthesis.voice.samantha')
        self.engine.setProperty('rate', 170)

    def speak(self, text):
        print(f"JARVIS: {text}")
        self.engine.say(text)
        self.engine.runAndWait()


# ==================================================================================
# MODULE 2: THE EARS (Speech Recognition)
# ==================================================================================
class Ears:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def listen(self, active_mode=False):
        """
        active_mode=True: Listens attentively for a command.
        active_mode=False: Listens passively for the wake word.
        """
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            if active_mode:
                print("Listening for command...")
                audio_timeout = 5
            else:
                print(f"Waiting for '{Config.WAKE_WORD}'...")
                audio_timeout = 1  # Short listen cycles for wake word

            try:
                audio = self.recognizer.listen(source, timeout=audio_timeout, phrase_time_limit=5)
                text = self.recognizer.recognize_google(audio).lower()
                print(f"Heard: {text}")
                return text
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                return ""
            except sr.RequestError:
                return ""


# ==================================================================================
# MODULE 3: THE BRAIN (LLM + Memory)
# ==================================================================================
class Brain:
    def __init__(self):
        self.history = [
            {"role": "system",
             "content": "You are JARVIS, an advanced AI assistant. You are helpful, witty, and concise. Your creator is the user. Keep answers under 2 sentences unless asked otherwise."}
        ]

    def think(self, user_text, image_path=None):
        # Add user message to history
        msg = {"role": "user", "content": user_text}

        # If image is provided, switch to vision model
        if image_path:
            print("Processing Visual Data...")
            with open(image_path, "rb") as f:
                img_bytes = f.read()
                msg['images'] = [img_bytes]
            response = ollama.chat(model=Config.VISION_MODEL, messages=[msg])
        else:
            self.history.append(msg)
            response = ollama.chat(model=Config.BRAIN_MODEL, messages=self.history)

        reply = response['message']['content']

        # Add AI reply to history only for text chats to keep context
        if not image_path:
            self.history.append({"role": "assistant", "content": reply})

        return reply


# ==================================================================================
# MODULE 4: THE EYES (Computer Vision)
# ==================================================================================
class Eyes:
    def capture_frame(self, filename="vision_input.jpg"):
        cap = cv2.VideoCapture(Config.CAMERA_INDEX)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(filename, frame)
            cap.release()
            return filename
        cap.release()
        return None


# ==================================================================================
# MODULE 5: THE HANDS (IoT / Serial Control)
# ==================================================================================
class IoTController:
    def __init__(self):
        try:
            self.ser = serial.Serial(Config.SERIAL_PORT, Config.BAUD_RATE, timeout=1)
            time.sleep(2)  # Wait for connection
            self.connected = True
            print("IoT System: Online")
        except:
            self.connected = False
            print("IoT System: Offline (Simulation Mode)")

    def send_command(self, command):
        # Command map: "on" -> '1', "off" -> '0'
        if self.connected:
            self.ser.write(command.encode())
        else:
            print(f"[SIMULATION] Sending '{command}' to Arduino via Serial.")


# ==================================================================================
# MAIN SYSTEM
# ==================================================================================
def main():
    # Initialize Modules
    voice = VoiceEngine()
    ears = Ears()
    brain = Brain()
    eyes = Eyes()
    iot = IoTController()

    voice.speak("System online. Initializing sensors.")

    while True:
        # 1. Passive Listening (Wake Word)
        text = ears.listen(active_mode=False)

        if Config.WAKE_WORD in text:
            voice.speak("Yes sir?")

            # 2. Active Listening (Command)
            command = ears.listen(active_mode=True)
            if not command:
                continue

            # --- COMMAND PROCESSING ---

            # A. VISION COMMANDS
            if "look at this" in command or "what do you see" in command or "describe" in command:
                voice.speak("Analyzing visual feed...")
                img_path = eyes.capture_frame()
                if img_path:
                    description = brain.think("Describe what you see in this image concisely.", image_path=img_path)
                    voice.speak(description)
                    # Clean up
                    if os.path.exists(img_path): os.remove(img_path)
                else:
                    voice.speak("I couldn't access the camera.")

            # B. IOT COMMANDS (Lights)
            elif "turn on" in command or "light on" in command:
                voice.speak("Turning ON the living room lights.")
                iot.send_command('1')  # Sends '1' to Arduino

            elif "turn off" in command or "light off" in command:
                voice.speak("Turning OFF the living room lights.")
                iot.send_command('0')  # Sends '0' to Arduino

            # C. SYSTEM COMMANDS
            elif "terminate" in command or "sleep" in command:
                voice.speak("Disconnecting. Goodbye sir.")
                break

            # D. GENERAL CONVERSATION (LLM)
            else:
                response = brain.think(command)
                voice.speak(response)


if __name__ == "__main__":
    main()