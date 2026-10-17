"""Allocates memory 200 MB at a time so you can watch the memory guard trip.

Run it with the guard on: it should be stopped when memory reaches your trip level.
Set STEP_MB / MAX_GB below if you want something gentler.
"""
import time

STEP_MB = 200
MAX_GB = 64

hog = []
while len(hog) * STEP_MB < MAX_GB * 1024:
    hog.append(bytearray(STEP_MB * 1024 * 1024))
    for i in range(0, len(hog[-1]), 4096):  # touch pages so they are really resident
        hog[-1][i] = 1
    print(f"allocated {len(hog) * STEP_MB} MB", flush=True)
    time.sleep(0.5)
