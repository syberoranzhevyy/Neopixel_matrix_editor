#Neopixel Matrix Editor
#v 0.1
import kivy
kivy.require('1.10.0')
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.properties import DictProperty, BooleanProperty, NumericProperty

from collections import deque
from matplotlib.colors import to_hex, to_rgb, to_rgba
import threading
import queue
import os
import json
import time

class LedPlayer(threading.Thread):
    def __init__(self, led_stripe, input_queue):
        threading.Thread.__init__(self)
        self.led_stripe = led_stripe
        self.input_queue = input_queue
        self.__running = True
        self.__movie_repeat = False

    def stop(self):
        self.__running == False
        self.stop_movie()
        while not self.input_queue.empty():
            dump = self.input_queue.get()
        self.input_queue.put_nowait(('stop', None))

    def stop_movie(self):
        self.__movie_repeat = False
        self.led_stripe.enable = False

    def run(self):
        while self.__running:
            command, data = self.input_queue.get()

            if command == 'stop':
                break
            elif command == 'picture':
                self.led_stripe.show_picture(data)
            elif command == 'movie_once':
                self.led_stripe.show_movie(data)
            elif command == 'movie_repeat':
                self.__movie_repeat = True
                while self.__movie_repeat:
                    self.led_stripe.show_movie(data)
                self.led_stripe.enable = True


class LED(CheckBox):
    locked = BooleanProperty(False)
    index = NumericProperty()
    def __init__(self, callback, *args, **kwargs):
        super(LED, self).__init__(*args, **kwargs)
        self.background_checkbox_normal = './picture/circle_normal.png'#self.background_radio_normal
        self.background_checkbox_down = './picture/circle_down.png'#self.background_radio_down
        self.background_checkbox_disabled_down = './picture/circle_disabled.png'
        self.background_checkbox_disabled_normal = './picture/circle_disabled.png'
        self.color = (1,1,1,.3)
        self.callback = callback
        self.bind(on_release=self.click_action)

    def click_action(self, *args):
        self.callback(self)
        if self.locked:
            self.color = (1,1,1,.3)
            self.state = 'normal'
            self.background_checkbox_normal = self.background_checkbox_disabled_normal
        else:
            self.background_checkbox_normal = './picture/circle_normal.png'

class LEDGrid(GridLayout):
    def __init__(self, matrix, *args, **kwargs):
        super(LEDGrid, self).__init__(*args, **kwargs)
        self.spacing = 5
        self.padding = 5
        self.row_force_default = True
        self.row_default_height = 50
        self.col_force_default = True
        self.col_default_width = 50
        self.bind(size=self._update_size)

    def _update_size(self, *args):
        self.row_default_height = args[-1][1] / 25
        self.col_default_width = self.row_default_height #args[-1][0] / 25

class DialogBox(BoxLayout):
    data = DictProperty({})
    def __init__(self, *args, **kwargs):
        super(DialogBox, self).__init__(*args, **kwargs)
        self.data = {'dialog_type':'save?'}

    def set_text(self, text):
        self.ids.dialog_text_label.text = text

    def set_dialog_type(self, dtype):
        self.data.update({'dialog_type':dtype})

class FileChooseBox(BoxLayout):
    data = DictProperty({})
    def __init__(self, *args, **kwargs):
        super(FileChooseBox, self).__init__(*args, **kwargs)
        self.data = {'filename': '', 'mode':'open'}

    def set_mode(self, mode):
        self.data.update({'mode':mode})

    def set_next_command(self, command):
        #print('set next command:', command)
        self.data.update({'next_command':command})

    def update_data(self, filename):
        if filename:
            if filename.split('.')[-1] == 'led':
                self.data['filename'] = filename
            else:
                self.data['filename'] = filename + '.led'

    def update_files(self):
        self.ids.file_icon_view._update_files()

class DefineBox(BoxLayout):
    data = DictProperty({})
    def __init__(self, *args, **kwargs):
        super(DefineBox, self).__init__(*args, **kwargs)
        self.matrix_size = [5,5]
        self.max_matrix_size = [50,50]
        self.data = {'matrix': self.matrix_size}

    def set_matrix(self, text, direction, text_input):
        try:
            val = int(text)
            text_input.background_color = (1, 1, 1, 1)
        except Exception as ex:
            val = None
            print('Fehler DefineBox: ', str(ex))
            text_input.background_color = (1,0,0,.5)

        if val:
            if direction == 'x':
                index = 0
            elif direction == 'y':
                index = 1
            else:
                index = None

            if val > self.max_matrix_size[index]:
                self.matrix_size[index] = self.max_matrix_size[index]
            else:
                self.matrix_size[index] = val

            self.data['matrix'] = self.matrix_size

class PopupBox(BoxLayout):
    def __init__(self, callback, popup=None, *args, **kwargs):
        super(PopupBox, self).__init__(*args, **kwargs)
        self.__callback = callback #NeoEditorApp.close_popup
        self.data_dict = {'choice':'cancel'}
        self.__content = None
        self.__parent_popup = popup

    def set_parent_popup(self, popup):
        self.__parent_popup = popup

    #def dismiss_popup(self):
    #    if self.__parent_popup:
    #        self.__parent_popup.dismiss()

    def choice_done(self, choice):
        self.data_dict.update({'choice':choice})
        self.__callback(self.data_dict)

    def set_content(self, content=None):
        if self.__content != content:
            if self.__content:
                #print('content ', self.__content)
                self.__content.unbind(data=self._update_data)
                #self.unbind()
                self.__content = None
            if self.ids.content_box.children:
                self.ids.content_box.clear_widgets()
            if content:
                self.__content = content
                self.ids.content_box.add_widget(content)
                self.__content.bind(data=self._update_data)
                self.data_dict = content.data.copy() # falls die Voreinstellungen übernommen werden wird update nicht getriggert

    def _update_data(self, *args):
        self.data_dict.update(args[-1])

class RooWi(BoxLayout):
    def __init__(self, *args, **kwargs):
        super(RooWi, self).__init__(*args, **kwargs)

class NeoEditorApp(App):

    def build(self):
        self.roowi = RooWi()
        return self.roowi

    def on_start(self):
        self.__popup_active = False
        self.popup_box = PopupBox(callback=self.close_popup)
        self.popup = Popup(content=self.popup_box, size_hint=(0.8,0.8), auto_dismiss=False)
        self.popup_box.set_parent_popup(self.popup)
        self.def_box = DefineBox()
        self.filechoose_box = FileChooseBox()
        self.dialog_box = DialogBox()
        self.matrix = deque([])
        self.num_leds = 0
        self.led_stripe = None # Schnittstelle zu FT232H-Board mit CircuitPython-NeoPixel
        self.led_grid = None
        self._act_col = (0,0,0,0)
        self._act_command = 'col' # col / reset / disable
        self._matrix_collection = [] #Hier werden alle Einzelbilder abgelegt
        self._auto_scroll = False
        self.led_player_thread = None
        self.led_queue = queue.Queue()
        self._act_set_name = ''
        self.savepath = './ledfile/'

    def on_stop(self):
        self.stop_led_player()
        if self.led_stripe:
            self.led_stripe.close()

    def stop_led_player(self):
        if self.led_player_thread and self.led_player_thread.is_alive():
            self.led_player_thread.stop()
            self.led_player_thread.join()
        self.led_player_thread = None

    def start_led_player(self):
        if not self.led_player_thread and self.led_stripe:
            self.led_player_thread = LedPlayer(led_stripe=self.led_stripe, input_queue=self.led_queue)
            self.led_player_thread.daemon = True
            self.led_player_thread.start()

    def move_set(self, direction):
        if self.matrix and self.led_grid:
            if self._auto_scroll:
                self.scroll_collection('up', self.roowi.ids.set_no_label, self.roowi.ids.set_max_label)

            if direction == 'left':
                for line in self.matrix:
                    line.rotate(-1)
            elif direction == 'right':
                for line in self.matrix:
                    line.rotate(1)
            elif direction == 'up':
                self.matrix.rotate(-1)
            elif direction == 'down':
                self.matrix.rotate(1)
            self.update_led_grid()


    def open_popup(self, command, override=False):
        #print('open popup', command, override)
        open_popup = False
        if len(self._matrix_collection) and not override:
            self.filechoose_box.set_next_command(command=command)
            self.open_popup(command='save?', override=True)
        else:
            if command == 'new':
                self.popup.title = 'Neu erstellen'
                self.popup_box.set_content(self.def_box)
                open_popup = True
            elif command == 'open':
                self.filechoose_box.set_mode('open')
                self.popup.title = 'Datei Öffnen'
                self.filechoose_box.update_files()
                self.popup_box.set_content(self.filechoose_box)
                open_popup = True
            elif command == 'save?':
                self.dialog_box.set_dialog_type('save?')
                self.popup.title = 'INFO'
                self.dialog_box.set_text('Willst du deine Arbeit\nvorher speichern?')
                self.popup_box.set_content(self.dialog_box)
                open_popup = True
            elif command == 'file?':
                self.dialog_box.set_dialog_type('file?')
                self.popup.title = 'Fehler - kein Dateiname'
                self.dialog_box.set_text('Du hast keine Datei angegeben!\nWillst du wiederholen?')
                self.popup_box.set_content(self.dialog_box)
                open_popup = True
            elif command == 'save':
                if self.matrix:
                    self.filechoose_box.set_mode('save')
                    self.popup.title = 'Datei Speichern'
                    self.filechoose_box.update_files()
                    self.popup_box.set_content(self.filechoose_box)
                    open_popup = True
            elif command == 'reset':
                self.reset_matrix()
                open_popup = False

            if open_popup and not self.__popup_active:
                self.popup.open()
                self.__popup_active = True
            if not open_popup and self.__popup_active:
                self.popup.dismiss()
                self.__popup_active = False

    def close_popup(self, data_dict):
        #print('close_popup', data_dict)
        if 'matrix' in data_dict.keys():
            self.popup.dismiss()
            self.__popup_active = False
            if data_dict['choice'] == 'ok':
                self.reset_matrix()
                matrix = data_dict['matrix']
                self.generate_matrix(matrix)

        elif 'mode' in data_dict.keys():
            if data_dict['choice'] == 'ok':
                if data_dict['filename']:
                    if data_dict['mode'] == 'open':
                        self._load_led_file(filename=data_dict['filename'])
                        self.popup.dismiss()
                        self.__popup_active = False
                    elif data_dict['mode'] == 'save':
                        self._save_led_file(data_dict['filename'])
                        if 'next_command' in data_dict.keys() and data_dict['next_command']:
                            self.open_popup(command=data_dict['next_command'], override=True)
                        else:
                            self.popup.dismiss()
                            self.__popup_active = False
                else:
                    next_cmd = data_dict['mode']
                    self.filechoose_box.set_next_command(command=next_cmd)
                    self.open_popup(command='file?', override=True)

            else:
                self.popup.dismiss()
                self.__popup_active = False

        elif 'dialog_type' in data_dict.keys():
            if data_dict['dialog_type'] == 'save?' and data_dict['choice'] == 'ok':
                self.open_popup(command='save', override=True)
            elif data_dict['dialog_type'] == 'save?' and data_dict['choice'] == 'cancel':
                next_cmd = self.filechoose_box.data['next_command']
                self.filechoose_box.set_next_command(command='')
                #print('next_cmd:',next_cmd)
                self.open_popup(command=next_cmd, override=True)
            elif data_dict['dialog_type'] == 'file?' and data_dict['choice'] == 'ok':
                next_cmd = self.filechoose_box.data['next_command']
                self.filechoose_box.set_next_command(command='')
                self.open_popup(command=next_cmd, override=True)
            elif data_dict['dialog_type'] == 'file?' and data_dict['choice'] == 'cancel':
                self.filechoose_box.set_next_command(command='')
                self.popup.dismiss()
                self.__popup_active = False

    def set_command(self, command):
        self._act_command = command

    def set_auto_scroll(self, state):
        if state == 'down':
            self._auto_scroll = True
        else:
            self._auto_scroll = False

    def set_live_test(self, button):
        if button.state == 'down':
            if self.matrix and self.led_grid:
                try:
                    from neo_blinka import LED_Stripe
                    self.led_stripe = LED_Stripe(num=self.num_leds,
                                                 bright=self.roowi.ids.bright_slider.value / 100)
                    self.led_stripe.testrun()
                    self.start_led_player()
                except Exception as ex:
                    print('Error loading LED_Stripe: ', str(ex))
                    self.led_stripe = None
                    button.state = 'normal'
            else:
                button.state = 'normal'
        else:
            if self.led_stripe:
                self.stop_led_player()
                self.led_stripe.testrun(color=0x00FF00)
                self.led_stripe.close()
                self.led_stripe = None

    def live_test(self):
        if self.led_stripe:
            picture = self.generate_led_picture(self.matrix)
            #print('live_test - picture:', picture)
            self.led_queue.put_nowait(('picture', picture))
            #self.led_stripe.show_picture(picture)

    def set_color(self, rgba_col):
        #print('set col to ', rgba_col)
        self._act_col = rgba_col

    def reset_matrix(self, command=None):
        print('reset matrix')
        #if len(self._matrix_collection) and not command:
        #    self.open_popup(command='save?', override=True)
        #elif not len(self._matrix_collection) or command == 'reset':
        if self.led_stripe:
            self.roowi.ids.live_toggle.state = 'normal'
            self.stop_led_player()
            self.led_stripe.close()
        self.roowi.ids.led_box.clear_widgets()
        self.matrix = deque([])
        self._matrix_collection = []
        self.led_grid = None
        self.roowi.ids.set_no_label.text = '1'
        self.roowi.ids.set_max_label.text = '1'
        self.num_leds = 0

    def generate_matrix(self, matrix):
        #print('generate matrix', matrix)
        self.matrix = deque([])
        led_index = 0
        for n in range(matrix[1]):
            line = deque([])
            for i in range(matrix[0]):
                led = LED(callback=self.led_action, index=led_index)
                led_index += 1
                line.append({'ref':led,'color':(1,1,1,.3), 'state':'normal'})
            self.matrix.append(line)
        self.led_grid = LEDGrid(matrix, cols=matrix[0])
        for line in self.matrix:
            for led_data in line:
                self.led_grid.add_widget(led_data['ref'])
        self.roowi.ids.led_box.add_widget(self.led_grid)
        self.num_leds = matrix[0] * matrix[1]
        #print('matrix:\n', self.matrix)
        #print('children:\n', self.led_grid.children)

    def led_action(self, led):
        #print('act command', self._act_command)
        if self._act_command == 'col':
            if not led.disabled:
                if led.state == 'down':
                    led.color = self._act_col
                else:
                    led.color = (1,1,1,.3)
            self.update_matrix()
        elif self._act_command == 'disable':
            led.state = 'normal'
            led.color = (1,1,1,.3)
            if led.locked:
                led.locked = False
            else:
                led.locked = True

    def set_bright(self, value):
        if self.led_stripe:
            self.led_stripe.set_brightness(value/100)

    def reset_leds(self):
        if self.matrix and self.led_grid:
            for led_data, led_widget in zip([line[i] for line in self.matrix for i in range(len(line))], self.led_grid.children):
                led_data.update({'ref':led_widget, 'color':(1,1,1,.3), 'state':'normal'})
                led_widget.color = (1,1,1,.3)
                led_widget.state = 'normal'
            self.live_test()

    def update_matrix(self):
        if self.matrix and self.led_grid:
            for led_data, led_widget in zip([line[i] for line in self.matrix for i in range(len(line))] , reversed(self.led_grid.children)):
                led_data['ref'] = led_widget
                if not led_widget.locked:
                    led_data['state'] = led_widget.state
                    led_data['color'] = led_widget.color
            self.live_test()


    def update_led_grid(self):
        if self.matrix and self.led_grid:
            for led_data, led_widget in zip([line[i] for line in self.matrix for i in range(len(line))], reversed(self.led_grid.children)):
                led_data['ref'] = led_widget
                if not led_widget.locked:
                    led_widget.state = led_data['state']
                    led_widget.color = led_data['color']
            self.live_test()

    def copy_deque(self, target_deque):
        matrix_copy = deque([])
        for line in target_deque:
            line_copy = deque([])
            for led in line:
                line_copy.append(led.copy())
            matrix_copy.append(line_copy)
        return matrix_copy

    def update_collection(self, index, max_label=None):
        if len(self._matrix_collection):
            last_index = len(self._matrix_collection) - 1
        else:
            last_index = 0
        if self.roowi.ids.delay_label.text:
            delay = int(self.roowi.ids.delay_label.text) / 1000
        else:
            delay = 0.01
        if index >= last_index :
            self._matrix_collection.append({'matrix':self.copy_deque(self.matrix),'delay':delay})
        else:
            #print(self.matrix)
            self._matrix_collection[index] = {'matrix':self.copy_deque(self.matrix),'delay':delay}
        if max_label:
            max_label.text = str(len(self._matrix_collection))
        #for i, m in enumerate(self._matrix_collection):
        #    print(i, [x[n]['color'] for x in m['matrix'] for n in range(len(m['matrix']))])

    def load_collection(self, index, index_label=None, max_label=None):
        #print('load collection ', str(index))
        self.matrix = self.copy_deque(self._matrix_collection[index]['matrix'])
        self.roowi.ids.delay_label.text = str(int(self._matrix_collection[index]['delay'] * 1000))
        self.update_led_grid()
        if max_label:
            max_label.text = str(len(self._matrix_collection))
        if index_label:
            index_label.text = str(index + 1)

    def scroll_collection(self, direction, index_label, max_label):
        if self.matrix and self.led_grid:
            act_index = int(index_label.text) - 1
            if len(self._matrix_collection):
                last_index = len(self._matrix_collection) - 1
            else:
                last_index = 0
            self.update_matrix()
            if direction == 'down':
                #print('direction ' + direction + ', act_index ' + str(act_index))
                if act_index < last_index and self._matrix_collection[act_index] != self.matrix:
                    self.update_collection(act_index)
                if act_index > 0:
                    index = act_index - 1
                    index_label.text = str(index + 1)
                    self.load_collection(index, None, max_label)
            elif direction == 'up':
                #print('direction ' + direction + ', act_index ' + str(act_index) + ', last_index ' + str(last_index))
                if act_index >= last_index:
                    index = act_index + 1
                    self.update_collection(index, max_label)
                else:
                    if self._matrix_collection[act_index] != self.matrix:
                        self.update_collection(act_index)
                    self.load_collection(act_index + 1, None, max_label)
                index_label.text = str(act_index + 2)

    def del_act_set(self, index_label, max_label):
        if len(self._matrix_collection) > 1:
            act_index = int(index_label.text) - 1
            self._matrix_collection.pop(act_index)
            if act_index > 0:
                load_index = act_index -1
            else:
                load_index = 0
            self.load_collection(load_index, index_label, max_label)

    def convert_rgb_to_hex(self, rgb_col):
        hex_col = hex(int(to_hex(rgb_col, keep_alpha=False).replace('#','0x'),16))
        #print('convert rgb to hex ', rgb_col, ' >> ', hex_col)
        return hex_col

    def convert_hex_to_rgba(self, hex_col):
        rgba_col = list(to_rgba(hex_col.replace('0x', '#')))
        #print('hex to rgb ', hex_col, ' >> ', rgba_col)
        return rgba_col

    def generate_led_picture(self, matrix):
        picture = []
        index = 0
        for line in matrix:
            for led in line:
                if not led['ref'].locked:
                    if led['state'] == 'down':
                        #picture.append([index, self.convert_rgb_to_hex(led['color'])])
                        picture.append([index, led['color']])
                    index += 1
        return picture

    def generate_led_movie(self):
        movie = [] #[{picture:[[led_index, color], [], ... ], delay:time}, ...]
        for matrix in self._matrix_collection:
            picture = self.generate_led_picture(matrix['matrix'])
            movie.append({'picture':picture, 'delay':matrix['delay']})

        print('gen led_movie')
        #for pic in movie:
        #    print(pic)

        return movie

    def run_movie(self, button):
        if self._matrix_collection and self.led_grid and self.led_stripe:

            if button.state == 'down':
                movie = self.generate_led_movie()
                self.led_queue.put_nowait(('movie_repeat', movie))
            else:
                self.led_player_thread.stop_movie()

        else:
            button.state = 'normal'

    def generate_led_file(self):
        movie = self.generate_led_movie()
        return movie

    def _save_led_file(self, filename):
        picture_data = self.generate_led_file()
        locked_leds = []
        for i, widget in enumerate(self.led_grid.children):
            if widget.locked:
                locked_leds.append(i)
        matrix_size = [len(self.matrix[0]), len(self.matrix)]

        data = {'picture_list': picture_data,
                'matrix': matrix_size,
                'num_leds': self.num_leds,
                'locked_leds': locked_leds,
                'bright': self.roowi.ids.bright_slider.value / 100}

        print('saving')
        num = 1
        old_filename = filename
        while os.path.isfile(self.savepath + filename):
            iter_string = '(' + str(num) + ')'
            if iter_string in old_filename:
                filename = old_filename.replace(iter_string, '(' + str(num+1) + ')')
            else:
                filename = old_filename.split('.')[0] + '(' +str(num) + ').led'
            num += 1

        with open(self.savepath + filename, 'w') as ledfile:
            json.dump(data, ledfile)

    def _load_led_file(self, filename):
        print('load file ', filename)
        self.reset_matrix()
        if os.path.isfile(self.savepath + filename):
            try:
                with open(self.savepath + filename, 'r') as ledfile:
                    data = json.load(ledfile)
            except Exception as ex:
                print('error loading led-file: ', ex)

            if data:
                # Matrix neu erstellen
                self.generate_matrix(data['matrix'])
                # LEDs sperren
                for lock_index in data['locked_leds']:
                    self.led_grid.children[lock_index].locked = True
                    self.led_grid.children[lock_index].click_action()
                # neue Indexliste aufbauen
                index_dict = {}
                abs_index = 0 # Absoluter Index inklusive gesperrter LEDs
                rel_index = 0 # Relativer Index ohne gesperrte LEDs
                for line in self.matrix:
                    for led in line:
                        if not led['ref'].locked:
                            index_dict.update({rel_index: abs_index})
                            rel_index += 1
                        abs_index += 1
                # matrix_collection befüllen
                for picture in data['picture_list']:
                    matrix_set = self.copy_deque(self.matrix)
                    for led in picture['picture']:
                        index = led[0]
                        if isinstance(led[1], str):
                            color = self.convert_hex_to_rgba(led[1])
                        elif isinstance(led[1], list):
                            color = led[1]
                        target_led_index = index_dict[index]
                        x,y = target_led_index//len(matrix_set[0]), target_led_index%len(matrix_set[0])
                        #print('target coordinate', x, y)
                        target_led = matrix_set[x][y]
                        target_led['state'] = 'down'
                        target_led['color'] = color
                    self._matrix_collection.append({'matrix':matrix_set, 'delay':picture['delay']})
                # letztes Bild in matrix_collection laden
                index_label = self.roowi.ids.set_no_label
                max_label = self.roowi.ids.set_max_label
                if 'bright' in data.keys():
                    brightness = data['bright'] * 100
                else:
                    brightness = 100
                self.roowi.ids.bright_slider.value = brightness
                self.load_collection(index=len(self._matrix_collection)-1, index_label=index_label, max_label=max_label)





if __name__ == '__main__':
    if not os.path.isdir('./ledfile/'):
        os.mkdir('./ledfile/')
    editor = NeoEditorApp()
    editor.run()

