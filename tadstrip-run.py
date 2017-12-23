import TadStrip as TadStrip

try:
    TadStrip.main_loop()
finally:
    TadStrip.strip.clear()
    TadStrip.strip.show()
