from pyftdi.ftdi import Ftdi
import time
import os
os.environ["BLINKA_FT232H"] = '1'
import board
import neopixel_spi as neopixel

class LED_Stripe():
    def __init__(self, num=1, order=neopixel.GRB, auto=False, bright=1.0):
        self.num_pixels = num
        self.pixel_order = order
        self.auto_write = auto
        self.brightness = bright
        self.spi = board.SPI()
        #while not self.spi.try_lock():
        #    pass
        #self.spi.configure(baudrate=3000000, phase=0, polarity=0)
        print(self.spi.frequency)
        self.enable = True

        self.pixels = neopixel.NeoPixel_SPI(self.spi,
                                            self.num_pixels,
                                            pixel_order=self.pixel_order,
                                            auto_write=self.auto_write,
                                            brightness=self.brightness)
        # manche LEDs starten leuchtend - alle ausschalten:
        self._set_all_pixel(0x00)
        self.set_brightness(self.brightness)
        self._show()

    def _show(self):
        self.pixels.show()

    def _set_pixel(self, index, color):
        #print('set led', index, 'to', color)
        self.pixels[index] = color

    def _set_all_pixel(self, color):
        self.pixels.fill(color)

    def _reset_pixels(self):
        self.pixels.fill(0x00)

    def testrun(self, color=0xff):
        self._set_all_pixel(color)
        self._set_pixel(0, 0xffffff)
        self._show()
        time.sleep(.5)
        self._reset_pixels()
        self._show()

    def set_brightness(self, bright=0.6):
        self.brightness = bright
        self.pixels.brightness = self.brightness
        self._show()

    def show_picture(self, picture):
        #print('show picture ', picture)
        self._reset_pixels()
        for led in picture:
            self._set_pixel(index=led[0], color=int(led[1],16))
        self._show()

    def show_movie(self, movie):
        for picture in movie:
            self._reset_pixels()
            if not self.enable:
                self._show()
                break
            self.show_picture(picture['picture'])
            time.sleep(picture['delay'])

    def close(self):
        self._reset_pixels()
        self._show()
        self.pixels.deinit()


