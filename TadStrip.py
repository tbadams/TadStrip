import math
import time
import datetime
import random
import colorsys
from dotstar import Adafruit_DotStar
import RPi.GPIO as GPIO

length = 120
data = 23
clock = 24
switch = 26
TRANSPARENT = 0xFFFFFFFF
BLACK = 0
interrupt = False
colors = {'red': 0xFF0000}
# For all time, the order of my working strip is bgr
strip = Adafruit_DotStar(length, data, clock, order='bgr')


# Utility functions

def rgb(r, g, b):
    out = min(255, b)
    out += min(255, g) * 0x100
    out += min(255, r) * 0x10000
    return out


def rgb_split(rgb_color):
    r = rgb_color >> 16
    g = (rgb_color >> 8) & 0xFF
    b = rgb_color & 0xFF
    return r, g, b


def hsv(h, s, v):
    normalized_hsv = list(colorsys.hsv_to_rgb(h, s, v))
    normalized_hsv = tuple(int(i * 255) for i in normalized_hsv)
    return rgb(*list(normalized_hsv))


def hls(h, l, s):
    colorsys.hls_to_rgb(h, l, s)


def set_color(index, color):
    strip.setPixelColor(index, int(color))


def rand_color():
    return random.randrange(0xFFFFFF)
    # return color(random.randrange(255), random.randrange(255), random.randrange(255))


def rand_hue():
    return hsv(random.random(), 1, 1)


def rgb_translate(color_one, color_two, percent, split_func=rgb_split):
    rgb_one = split_func(color_one)
    rgb_two = split_func(color_two)
    return rgb(*list(translate_triple(rgb_one, rgb_two, percent)))


def translate_triple(triple_one, triple_two, percent):
    translate = lambda i: triple_one[i] + int(percent * (triple_two[i] - triple_one[i]))
    r = translate(0)
    g = translate(1)
    b = translate(2)
    return r, g, b


# Simple Display Routines
def spaced_lights(spacing, color_func, offset=0):
    for i in range(offset, length, spacing):
        set_color(i, color_func())


def wash(color):
    # print format(color, '06x')
    for i in range(length):
        set_color(i, color)


def gradient(color_one, color_two):
    for i in range(length):
        set_color(i, rgb_translate(color_one, color_two, float(i) / length))


# program routines
def random_wash(color_func=rand_color):
    cur = color_func()
    # print(cur)
    wash(cur)


def random_lights(spacing, color_func=rand_hue):
    spaced_lights(spacing, color_func)
    strip.show()


def random_all(color_func=rand_hue):
    for i in range(length):
        set_color(i, color_func())


def random_gradient(color_func_1=rand_hue, color_func_2=rand_hue):
    gradient(color_func_1(), color_func_2())


def morph(duration=60, refresh=0.1):
    animate(lambda frame: wash(rgb_translate(0xFF0000, 0x0000FF, float(frame * refresh) / duration)), refresh, 0)


class DrawType:
    Transparent, Opaque, Blend = range(3)

    def __init__(self):
        pass


class Anim(object):
    def __init__(self, duration, width=length, draw_type=DrawType.Transparent, end_func=lambda: False):
        self.duration = float(duration)
        self.width = width
        self.end_func = end_func
        self.time = float(0)

    def tick(self, set_color_func, frame_length=0.01666):
        self.time += frame_length
        return self.time >= self.duration


# TODO Image


class Pew(Anim):
    def __init__(self, color, duration=2.0, width=length, up=True):
        super(Pew, self).__init__(duration, width)
        self.color = color
        if up:
            self.pos = 0
        else:
            self.pos = width - 1
        self.up = up

    def tick(self, set_color_func, frame_length=0.01666):
        if (self.up and self.pos < self.width) or (not self.up and self.pos >= 0):
            if callable(self.color):
                new_color = self.color()
            else:
                new_color = self.color
            set_color_func(int(self.pos), new_color)
            dx = float(frame_length) / self.duration
            if not self.up:
                dx *= -1
            self.pos += dx * self.width
        if self.up:
            return self.pos >= self.width
        else:
            return self.pos < 0


class Wipe(Pew):
    # TODO Fix off by one error.
    def __init__(self, color, duration=2.0, width=length, up=True, color_two=None):
        super(Wipe, self).__init__(color, duration, width, up)
        self.color_two = color_two

    def tick(self, set_color_func, frame_length=0.01666):
        super(Wipe, self).tick(set_color_func, frame_length)
        for i in range(0, self.width):
            if (self.up and i < self.pos) or (not self.up and i > self.pos):
                set_color_func(i, self.color)
            elif self.color_two is not None:
                set_color_func(i, self.color_two)


class Wash(Anim):
    def __init__(self, color):
        super(Wash, self).__init__(0)
        self.color = color

    def tick(self, set_color_func, frame_length=0.01666):
        for i in range(self.width):
            # Accept either a color or a color function
            if callable(self.color):
                set_color_func(i, self.color())
            else:
                set_color_func(i, self.color)
        return False


class Boom(Anim):
    def __init__(self, color, duration, width=50, fill=False):
        super(Boom, self).__init__(duration, width)
        self.color = color
        self.left = math.floor(width/2.0)
        self.right = math.ceil(width/2.0)

    def tick(self, set_color_func, frame_length=0.01666):
        if callable(self.color):
            new_color = self.color()
        else:
            new_color = self.color
        set_color_func(self.left, new_color)
        set_color_func(self.right, new_color)
        dx = float(frame_length) / self.duration
        self.right += dx * (self.width/2.0)
        self.left -= dx * (self.width/2.0)
        return self.right >= self.width


class ColorWalk(Anim):
    def __init__(self, duration=4, strength=1, start=0, width=length):
        super(ColorWalk, self).__init__(duration, width)
        self.strength = strength
        self.buffer = [start]

    def tick(self, set_color_func, frame_length=0.01666):
        # TODO Duration not used
        for i in range(self.width):
            if i < self.buffer.__len__():
                set_color_func(i, hsv(self.buffer[i], 1.0, 1.0))
        last_color = self.buffer[0]
        new_color = (last_color + ((self.strength/255.0) * random.choice([1, -1]))) % 1.0
        self.buffer.insert(0, new_color)
        # if self.buffer.__len__() > self.width:
        #     self.buffer.remove(self.width)


class RandFade(Anim):
    def __init__(self, color_one, color_two, duration=2.5):
        super(RandFade, self).__init__(duration)
        self.color_one = color_one
        self.color_two = color_two
        self.order = range(self.width)
        random.shuffle(self.order)

    def tick(self, set_color_func, frame_length=0.01666):
        super(RandFade, self).tick(set_color, frame_length)
        progress = int((self.time / self.duration) * self.width)
        for i in range(self.width):
            if i <= progress:
                set_color_func(self.order[i], self.color_two)
            else:
                set_color_func(self.order[i], self.color_one)
        return self.time >= 2 * self.duration


class MorphPew(Anim):
    def __init__(self, start_fg_hue=0.0, start_bg_hue=0.5, duration=2.0, interval=0.5, morph_length=20.0, up=True):
        super(MorphPew, self).__init__(duration, length)
        self.executor = Executor(0.01666)
        self.start_fg_hue = start_fg_hue
        self.start_bg_hue = start_bg_hue
        self.interval=interval
        self.morpg_length = morph_length
        self.up = up

    def tick(self, set_color_func, frame_length=0.01666):
        pass


class Executor:
    def __init__(self, refresh, override_func=lambda: False):
        self.layers = []
        self.offsets = {}
        self.refresh = refresh
        self.out_buffer = {}
        self.override_func = override_func

    def tick(self, set_color_func=set_color):
        for layer in self.layers:
            done = layer.tick(lambda index, color: self.set_color(index + self.offsets.get(layer, 0), color), self.refresh)
            if done:
                self.remove(layer)
        self.show(set_color_func)
        time.sleep(self.refresh)

    def set_color(self, index, color):
        self.out_buffer[index] = color

    def show(self, set_color_func, clear_buffer=True):
        for i in range(length):
            if i in self.out_buffer and self.override_func():
                set_color_func(i, self.out_buffer.get(i))
            else:
                set_color_func(i, 0x000000)
        strip.show()
        if clear_buffer:
            self.out_buffer.clear()

    def add(self, anim, offset=0):
        if anim is not None:
            self.layers.append(anim)
            self.offsets[anim] = offset

    def remove(self, anim):
        self.layers.remove(anim)
        self.offsets.pop(anim, None)

    def clear(self):
        del self.layers[:]
        self.offsets.clear()

    def play(self, period):
        for i in range(int(period / self.refresh)):
            self.tick()


# Loop functions
def loop(func, interval, *args):
    global interrupt
    while not interrupt:
        func(*list(args))
        strip.show()
        time.sleep(interval)
    interrupt = False


def pew_pew(period=0.125, pew_factory=lambda: Pew(rand_hue(), random.randrange(2, 3)), bg=None, cycles=8 * 60, refresh=0.01666):
    executor = Executor(refresh)
    if bg is not None:
        executor.add(bg)
    for i in range(int(cycles)):
        executor.add(pew_factory())
        executor.play(period)


def xmas_pew(period=0.5, pew_factory=lambda: Pew(0xFF0000, 4), bg=Wash(0x085500), cycles=2 * 60, refresh=0.01666):
    pew_pew(period, pew_factory, bg, cycles, refresh=refresh)


def starfall(duration=60, check_period=0.1, chance=0.75, refresh=0.008333):
    executor = Executor(refresh)
    for i in range(int(float(duration)/check_period)):
        if random.random() < chance:
            executor.add(Pew(hsv(random.random(), random.random()/2.0, random.random()), random.randint(1, 4)/2.0, up=False))
        executor.play(check_period)


def moving_gradient(period=0.25, cycle_duration = 2.0, refresh=0.01666):
    pass


def random_fades(duration=1.25, cycles=24):
    executor = Executor(0.01666)
    last_hue = rand_hue()
    for i in range(cycles):
        next_hue = rand_hue()
        executor.add(RandFade(last_hue, next_hue, duration))
        last_hue = next_hue
        executor.play(duration)


def random_booms(duration=60, boom_length=2.5):
    executor = Executor(0.01666)
    for i in range(int(float(duration)/boom_length)):
        executor.add(Boom(rand_hue(), boom_length), random.randint(0, length-1))
        executor.play(duration)


def random_wipes(duration=2.0, cycles=30, segs=lambda:random.randint(1, 6), refresh=0.01666):
    executor = Executor(refresh)

    def cleanup(clear_list):
        for anim in clear_list:
            executor.remove(anim)
        del clear_list[:]
    step = duration/4.0
    to_clear = []
    for i in range(cycles):
        new_clear = []
        new_color = rand_hue()
        if callable(segs):
            segments=segs()
        else:
            segments = segs
        for j in range(segments):
            wipe = Wipe(new_color, step, length/segments)
            new_clear.append(wipe)
            executor.add(wipe, j * (length / segments))
        executor.play(step)
        cleanup(to_clear)
        to_clear = new_clear
        time.sleep(step)

        new_clear = []
        new_color = rand_hue()
        for j in range(segments):
            wipe = Wipe(new_color, step, length/segments, False)
            new_clear.append(wipe)
            executor.add(wipe, j * (length / segments))
        executor.play(step)
        cleanup(to_clear)
        to_clear = new_clear
        time.sleep(step)


def color_walk(duration=60, cycle=4, strength=4, start=0, refresh=0.01666):
    executor = Executor(refresh)
    executor.add(ColorWalk(cycle, strength, start))
    executor.play(duration)


def morph_pew(period=0.25, cycle_duration = 4000.0, color_ratio=0.5, pew_time=4.0, up=random.choice([True, False]), refresh=0.0333):
    pew_pew(period, pew_factory=lambda: Pew(lambda: hsv((int(round(time.time() * 1000)) % cycle_duration) /
            cycle_duration, 1.0, 1.0), pew_time, up=up),
            bg=Wash(lambda: hsv(((int(round(time.time() * 1000)) + (cycle_duration * color_ratio)) % cycle_duration)
                                / cycle_duration, 1.0, 0.2)), refresh=refresh)


def animate(func, frame_length, frame):
    while True:
        print(frame)
        func(frame)
        strip.show()
        frame += 1
        time.sleep(frame_length)


### ETK FUNCTIONS

# Color functions:
# -- random color
# /brightness


# Picks a random color function
# out of the possible color functions
def meta_rand_color():
    options = [
        rand_festive,
        rand_color,
        rand_hue,
        rand_fixcolor
    ]

    choice =  options[random.randrange(len(options))]
    # special case : reset the fixcolor if we're picking it again
    if choice == rand_fixcolor:
        rand_fixcolor(reset=True)
    return choice 
    # random rgb (often pastel)
    # random hsv (very bright)
    #     
    pass


    # random r g w
def rand_festive():
    rgb = [0xffffff, 0xff0000, 0x00ff00]
    return rgb[random.randrange(3)]


def rand_fixcolor(reset=False):
    if reset:
        rand_fixcolor.mycolor=rand_hue()
    try:
        return rand_fixcolor.mycolor
    except AttributeError:
        rand_fixcolor.mycolor=rand_hue()
        return rand_fixcolor.mycolor
        

# offset is how far apart you want the lights to be
# 1 is a good offset. It will set the lights spaced out at offset,
# and then slide them aloing the range of offset. Or something.
def festive_blinkenlights(offset, colorfunction=rand_festive):
    for i in range(offset+1):
        strip.clear()
        spaced_lights(offset+1, colorfunction, i)
        strip.show()
        time.sleep(0.5)


# Run 10 iterations of blinkenlights. 
# switch the color scheme each time.
def festive_blinkenlights_loop():
    for i in range(10):
        my_colorfunc = meta_rand_color()
        for i in range(3):
            festive_blinkenlights(1, my_colorfunc)


def main_loop():
    # executor = Executor(0.01666) # not sure this is doing anything right here?
    strip.clear()
    while True:

        # Lights
        festive_blinkenlights_loop()# Some blinkenlights
        for i in range(30):
            strip.clear()
            random_lights(4)
            time.sleep(2)
        # Pews
        random.choice([xmas_pew, starfall])()
        random.choice([pew_pew, morph_pew])()
        random.choice([random_fades, random_wipes])()

time.sleep(5)# Reboot shenanigans
strip.begin()
strip.setBrightness(64)  # Limit brightness to ~1/4 duty cycle
GPIO.setmode(GPIO.BCM)
GPIO.setup(switch, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


# pew = Pew(0xFFFFFF)
# loop(pew.tick, 0.05, 0.05)
# morph(60)
# loop(random_gradient, 0.5)
# loop(random_all, 5, rand_hue)
# loop(random_wash, 0.1)
# loop(random_lights, 2, 3)
# random_wash(0.5)
# pew_pew()
# morph_pew()
# pew_pew(0.25, pew_factory=lambda: Pew(lambda: hsv((int(round(time.time() * 1000)) % 2000.0)/2000.0, 1.0, 1.0), 4.0),
#         bg=Wash(lambda: hsv(((int(round(time.time() * 1000)) + 1000) % 2000.0)/2000.0, 1.0, 0.2)), refresh=0.0333)
# xmas_pew()
#moving_gradient()
# random_fades()
# random_wipes(segments=4)
# starfall(refresh=0.0083333)
# random_booms()
# color_walk()
