import tkinter as tk
from tkinter import ttk, simpledialog, filedialog
import tkinter.font as tkfont
import json
import threading
import time
from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController, Key
import keyboard as kb_lib
import tempfile
import subprocess
import winsound
import sys
import os
import requests
import ctypes

if hasattr(sys, '_MEIPASS'):
    os.chdir(sys._MEIPASS)

VERSION_URL = "https://raw.githubusercontent.com/0venToast/Action-Runner/refs/heads/main/version.json"
version = "2.4.12"

def download_new_version(download_url, temp_path):
    try:
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        print("Download error:", e)
        return False

def check_for_updates():
    try:
        response = requests.get(VERSION_URL)
        data = response.json()
        latest_version = data["version"]
        download_url = data["url"]

        if version != latest_version:
            answer = tk.messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available. Update now?")
            if answer:
                # Download new file to temp
                temp_path = os.path.join(tempfile.gettempdir(), "new_version.exe")
                if download_new_version(download_url, temp_path):
                    launcher_path = os.path.join(os.path.dirname(sys.executable), "Updater.exe")
                    subprocess.Popen([launcher_path, sys.executable, temp_path])
                    root.destroy()
                    sys.exit()
    except Exception as e:
        print("Update check failed:", e)

# DPI awareness for mouse accuracy
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception as e:
    print("DPI awareness error:", e)

# Globals
recorded_actions = []
recording = False
running = False
stop_key = 'ctrl+f1'
record_toggle_key = 'ctrl+f2'
mouse_ctrl = MouseController()
keyboard_ctrl = KeyboardController()

def play_sound(sound_file):
        try:
            winsound.PlaySound(f"sounds/{sound_file}", winsound.SND_FILENAME)  # Play the sound
        except Exception as e:
            print(f"Error playing sound: {e}")  # If there's an error, print it

def save_actions():
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")],
        title="Save Recorded Actions"
    )
    if file_path:
        try:
            with open(file_path, "w") as f:
                json.dump(recorded_actions, f)
        except Exception as e:
            print("Save failed:", e)

def load_actions():
    global recorded_actions
    file_path = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json")],
        title="Load Recorded Actions"
    )
    if file_path:
        try:
            with open(file_path, "r") as f:
                recorded_actions = json.load(f)
            update_action_list()
        except Exception as e:
            print("Load failed:", e)


# --- Format for UI ---
def format_action(action):
    if action[0] == 'delay':
        return f"Delay: {action[1]:.2f}s"
    elif action[0] == 'mouse':
        _, _, (x, y, btn, pressed) = action
        return f"Mouse {'Down' if pressed else 'Up'} ({btn}) at ({x},{y})"
    elif action[0] == 'key':
        _, _, key = action
        return f"Key Press: {key}"
    return "Unknown"

# --- Recording ---
def toggle_recording():
    global recording, recorded_actions
    if not recording:
        recorded_actions.clear()
        update_action_list()
        recording = True
        play_sound("toggled.wav")
        update_status("Recording")
        start_time = [time.time()]

        def add_delay():
            now = time.time()
            delay = now - start_time[0]
            if delay > 0.01:
                recorded_actions.append(('delay', delay))
            start_time[0] = now

        def on_click(x, y, button, pressed):
            if not recording:
                return False
            add_delay()
            recorded_actions.append(('mouse', time.time(), (x, y, button.name, pressed)))
            update_action_list()

        key_states = {}

        
        def on_press(key):
            """Handles key press events to record actions."""
            if not recording:
                return False
            
            try:
                # Check if the key is a character key or a special key
                k = key.char if hasattr(key, 'char') and key.char else key.name
            except AttributeError:
                k = str(key)

            # If the key is not already pressed, record the action
            if not key_states.get(k, False):  # If the key is not already pressed
                add_delay()
                recorded_actions.append(('key', time.time(), k))  # Record the key press
                update_action_list()
                
                # Update the key state to "pressed"
                key_states[k] = True

        def on_release(key):
            """Handles key release events to record actions."""
            if not recording:
                return False
            
            try:
                k = key.char if hasattr(key, 'char') and key.char else key.name
            except AttributeError:
                k = str(key)

            # If the key is already pressed, record the key release action
            if key_states.get(k, False):  # If the key is already pressed
                key_states[k] = False

        def record_thread():
            mouse_listener = mouse.Listener(on_click=on_click)
            keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            mouse_listener.start()
            keyboard_listener.start()
            while recording:
                time.sleep(0.1)
            mouse_listener.stop()
            keyboard_listener.stop()

        threading.Thread(target=record_thread, daemon=True).start()
    else:
        recording = False
        play_sound("toggled.wav")
        update_status("Idle")

# --- Playback ---
def get_button(btn_name):
    return {
        'left': Button.left,
        'right': Button.right,
        'middle': Button.middle
    }.get(btn_name, Button.left)

def play_action(repeat):
    global running
    if not recorded_actions:
        return
    running = True
    play_sound("toggled.wav")
    update_status("Running")

    def action_loop():
        global running
        count = 0
        while running and (repeat == 0 or count < repeat):
            for action in recorded_actions:
                if not running:
                    break
                if action[0] == 'delay':
                    time.sleep(action[1])
                elif action[0] == 'mouse':
                    _, _, (x, y, btn_name, pressed) = action
                    mouse_ctrl.position = (x, y)
                    time.sleep(0.05)
                    btn = get_button(btn_name)
                    if pressed:
                        mouse_ctrl.press(btn)
                    else:
                        mouse_ctrl.release(btn)
                elif action[0] == 'key':
                    _, _, key = action
                    try:
                        if len(key) == 1:
                            keyboard_ctrl.press(key)
                            keyboard_ctrl.release(key)
                        else:
                            k_obj = getattr(Key, key, None)
                            if k_obj:
                                keyboard_ctrl.press(k_obj)
                                keyboard_ctrl.release(k_obj)
                    except Exception as e:
                        print("Key error:", e)
            count += 1
        play_sound("toggled.wav")
        update_status("Idle")
        running = False

    threading.Thread(target=action_loop, daemon=True).start()

def toggle_action():
    global running
    if running:
        running = False
        play_sound("toggled.wav")
        update_status("Idle")
    else:
        try:
            repeat = int(repeat_entry.get())
            play_action(repeat)
        except ValueError:
            print("Invalid repeat input")

# --- GUI Updates ---
def update_status(text):
    status_var.set(f"Status: {text}")

def update_action_list():
    action_listbox.delete(0, tk.END)
    for action in recorded_actions:
        action_listbox.insert(tk.END, format_action(action))

# --- Action Editor ---
def delete_selected_action():
    selected = list(action_listbox.curselection())
    for i in reversed(selected):
        recorded_actions.pop(i)
    update_action_list()

def insert_delay():
    selected = action_listbox.curselection()
    if not selected:
        return
    try:
        delay = float(simpledialog.askstring("Insert Delay", "Enter delay in seconds:"))
        recorded_actions.insert(selected[0], ('delay', delay))
        update_action_list()
    except (ValueError, TypeError):
        pass

def edit_delay():
    selected = action_listbox.curselection()
    if not selected:
        return
    i = selected[0]
    if recorded_actions[i][0] != 'delay':
        return
    try:
        new_delay = float(simpledialog.askstring("Edit Delay", "New delay in seconds:"))
        recorded_actions[i] = ('delay', new_delay)
        update_action_list()
    except (ValueError, TypeError):
        pass

# --- Drag-and-Drop Support ---
dragging_indices = []

def on_drag_start(event):
    global dragging_indices
    dragging_indices = list(action_listbox.curselection())

def on_drag_motion(event):
    global dragging_indices
    if not dragging_indices:
        return
    new_index = action_listbox.nearest(event.y)
    if new_index < 0 or new_index >= len(recorded_actions):
        return
    # Move selected actions as a block
    selected = [recorded_actions[i] for i in dragging_indices]
    for i in sorted(dragging_indices, reverse=True):
        recorded_actions.pop(i)
    for i, action in enumerate(selected):
        recorded_actions.insert(new_index + i, action)
    update_action_list()
    action_listbox.selection_clear(0, tk.END)
    for i in range(len(selected)):
        action_listbox.selection_set(new_index + i)
    dragging_indices = list(range(new_index, new_index + len(selected)))

def on_drag_end(event):
    global dragging_indices
    dragging_indices = []

# --- GUI Setup ---
root = tk.Tk()
root.iconbitmap("icon.ico")
root.title("Action-Runner")
check_for_updates()

custom_font = tkfont.Font(family="TkDefaultFont", size=12)

mainframe = ttk.Frame(root, padding="10")
mainframe.grid(row=0, column=0, sticky="nsew")

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

mainframe.columnconfigure(0, weight=1)
mainframe.columnconfigure(1, weight=1)
mainframe.columnconfigure(2, weight=0)
mainframe.rowconfigure(3, weight=1)  # Make row with listbox expandable


ttk.Label(mainframe, text="Repeat Count (0 = Infinite):").grid(row=0, column=0, sticky="w")
repeat_entry = ttk.Entry(mainframe)
repeat_entry.insert(0, "1")
repeat_entry.grid(row=0, column=1)

status_var = tk.StringVar(value="Status: Idle")
ttk.Label(mainframe, textvariable=status_var, foreground="blue").grid(row=1, column=0, columnspan=2, pady=5)

ttk.Label(mainframe, text="Recorded Actions:").grid(row=2, column=0, columnspan=2, sticky="w")
ttk.Button(mainframe, text="Save", command=save_actions).grid(row=5, column=0)
ttk.Button(mainframe, text="Load", command=load_actions).grid(row=5, column=1)
action_listbox = tk.Listbox(mainframe, width=60, height=12, selectmode=tk.EXTENDED)
action_listbox.grid(row=3, column=0, columnspan=2, pady=5, sticky="nsew")

scrollbar = ttk.Scrollbar(mainframe, orient="vertical", command=action_listbox.yview)
scrollbar.grid(row=3, column=2, sticky="ns")
action_listbox.config(yscrollcommand=scrollbar.set)
action_listbox.config(font=custom_font)

def select_all(event=None):
    action_listbox.select_set(0, tk.END)
    return "break"  # Prevent default behavior (like beep)

action_listbox.bind("<Control-a>", select_all)


action_listbox.bind("<Button-1>", on_drag_start)
action_listbox.bind("<B1-Motion>", on_drag_motion)
action_listbox.bind("<ButtonRelease-1>", on_drag_end)

ttk.Button(mainframe, text="Delete", command=delete_selected_action).grid(row=4, column=0)
ttk.Button(mainframe, text="Insert Delay", command=insert_delay).grid(row=4, column=1)
ttk.Button(mainframe, text="Edit Delay", command=edit_delay).grid(row=5, column=0, columnspan=2)

ttk.Label(mainframe, text="Hotkeys: 'ctrl+F2' = Record, 'ctrl+F1' = Run/Stop action").grid(row=6, column=0, columnspan=2, pady=5)
ttk.Label(mainframe, text="Version: " + version).grid(row=7, column=0, columnspan=2, pady=5)

# --- Global Hotkeys ---
def hotkey_listener():
    kb_lib.add_hotkey(record_toggle_key, toggle_recording)
    kb_lib.add_hotkey(stop_key, toggle_action)
    kb_lib.wait()

threading.Thread(target=hotkey_listener, daemon=True).start()

root.mainloop()