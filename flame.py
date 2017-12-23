import TadStrip as tad
import time
import math
import random

# Simple flame effect based on https://github.com/timpear/NeoCandle

# Color
red = 255
green_high = 120
blue = 10
burn_depth = 10
flicker_depth = 15


flutter_depth = 25
base_hue = tad.rgb(red, green_high, blue)
burn_hue = tad.rgb(red, green_high - burn_depth, blue)
flicker_hue = tad.rgb(red, green_high - flicker_depth, blue)
flutter_hue = tad.rgb(red, green_high - flutter_depth, blue)

# Timing
tick = 0.0025
dip_ms = .125


def green_vary_hue(green):
    return tad.rgb(red, green, blue)


def translate(start_hue, end_hue, duration):
    cur_time = 0.0
    while cur_time < duration:
        progress = cur_time / duration
        cur_hue = tad.rgb_translate(start_hue, end_hue, progress)
        tad.wash(cur_hue)
        tad.strip.show()
        cur_time += tick
        time.sleep(tick)


def dip(dip_hue=burn_hue, start_hue=base_hue, dur=dip_ms):
    translate(start_hue, dip_hue, dur / 2)
    translate(dip_hue, start_hue, dur / 2)


def play(duration, dip_hue, start_hue=base_hue):
    the_time = 0.0
    while the_time < duration:
        dip(dip_hue, start_hue)
        the_time += dip_ms


def timpear():
    while True:
        play(10, burn_hue)
        play(5, flicker_hue)
        play(8, burn_hue)
        play(3, flutter_hue)
        play(6, burn_hue)
        # on 10
        play(10, burn_hue)
        play(10, flicker_hue)


def rand():
    while True:
        dip(random.choice([burn_hue, flicker_hue, flutter_hue]))


# def LFO(cycle_secs):
#     halfway = cycle_secs / 2.0
#     timer = 0.0
#     while True:
#         progress = (time % cycle_secs)
#         anti_depth = math.fabs(halfway - progress)
#         dip(green_vary_hue(green_high - ))

timpear()







