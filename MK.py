import easy_pygame as epg
from easy_pygame import UP, DOWN, LEFT, RIGHT
import pygame as pg
from fighter import *
import connection
import os
import time
import threading
import inspect
import logging as mainlog

epg.AUTO_UPDATE = False
SCREEN_HEIGHT = epg.HEIGHT = 600
SCREEN_WIDTH = epg.WIDTH = 800
SPRITE_WIDTH = 130
SPRITE_HEIGHT = 130

FPS = 30
BALL_IMAGE_PATH = 'photos/ball.png'
EARTH_IMAGE_PATH = 'photos/earth.png'
BACK_IMAGE_PATH = 'photos/back.png'

HEIGHT_HALF = int(SCREEN_HEIGHT/2)
WIDTH_HALF = int(SCREEN_WIDTH/2)
epg.AUTO_UPDATE = False

GRAVITY = 2
#EARTH = 716

PROJECT_DIR = os.getcwd()
FIGHTER_IMAGE_PATHES = (os.path.join(PROJECT_DIR, 'photos', 'stay.png'),
                        os.path.join(PROJECT_DIR, 'photos', 'go.png'),
                        os.path.join(PROJECT_DIR, 'photos', 'jump.png'),
                        os.path.join(PROJECT_DIR, 'photos', 'attack.png'),
                        os.path.join(PROJECT_DIR, 'photos', 'hitted.png'),
                        os.path.join(PROJECT_DIR, 'photos', 'dead.png'),
                        )

BUTTON_RELEASED_IMAGE_PATH = 'photos/released.jpeg'
BUTTON_PRESSED_IMAGE_PATH = 'photos/pressed.jpeg'
BUTTON_DISABLED_IMAGE_PATH = 'photos/disabled.jpeg'

URL = 'localhost'
PORT = 5555


class WebMenu():
    def __init__(self, server, 
                 screen,
                 menu_background_img_path, 
                 button_img_paths, 
                 button_size, 
                 button_titles=(),
                 button_order='v', 
                 button_margin=100,
                ):
        self.active = False
        self.server = server
        self.background_path = menu_background_img_path
        self.screen = screen
        self.button_order = button_order
        self.button_size = button_size
        self.button_margin = button_margin
        self.button_img_paths = button_img_paths
        self.reset_last_button_pos()
        self.buttons = []
        self.add_buttons(button_titles)
        
    def reset_last_button_pos(self,):
        if self.button_order == 'v':
            self.last_button_x = int(SCREEN_WIDTH / 2)
            self.last_button_y = self.button_margin + int(self.button_size[1] / 2)
        else:
            self.last_button_x = self.button_margin + int(self.button_size[0] / 2)
            self.last_button_y = int(SCREEN_HEIGHT / 2)
                
    def add_buttons(self, button_titles, insert_before_existing=False):
        for title in button_titles:
            button_pos = (self.last_button_x, self.last_button_y)
            button = Button(self.button_img_paths, 
                                       title,
                                       button_pos,
                                       w=self.button_size[0],
                                       h=self.button_size[1],
                                       )
            if insert_before_existing:
                print('WebMenu: добавляю кнопку перед существующими')
                self.reset_last_button_pos()
                button.move_to((self.last_button_x, self.last_button_y))
                for exist_button in self.buttons:
                    if self.button_order == 'v':
                        print(f'Двигаю кнопку {exist_button.text} из позиции {exist_button.pos} вертикально')
                        new_pos = (exist_button.pos[0], exist_button.pos[1] + self.button_size[1] + self.button_margin)
                    else:
                        print(f'Двигаю кнопку {exist_button.text} из позиции {exist_button.pos} горизонтально')
                        new_pos = (exist_button.pos[0] + self.button_size[0] + self.button_margin, exist_button.pos[1])
                    exist_button.move_to(new_pos)
                self.buttons.insert(0, button)
            else:
                print('WebMenu: добавляю кнопку после существующих')
                self.buttons.append(button)
                if self.button_order == 'v':
                    self.last_button_y += self.button_size[1] + self.button_margin
                else:
                    self.last_button_x += self.button_size[0] + self.button_margin
                
    def get_choice (self, labels=[]):
        self.active = True
        choice = ''
        self.screen.set_background(self.background_path)
        if labels:
            label_y = SCREEN_HEIGHT / (len(labels) + 1)
            label_height = label_y
            for label in labels:
                label.place_to((CENTER_X, label_y), center=True)
                label.show()
                label_y += label_height
        for button in self.buttons:
            button.show()
        buttons_updater = threading.Thread(target=self.update_buttons, daemon=True).start()
        while self.active:
            update()
            for button in self.buttons:
                if button.get_pressed():
                    choice = button.text
                    update()
                    time.sleep(0.5)
                    self.active = False
                    button.set_skin(button.RELEASED)
        for button in self.buttons:
            button.hide()
        for label in labels:
            label.hide()
        return choice
        
    def update_buttons(self):
        print('WebMenu: buttons updater started')
        while not self.server.serv_socket_available:
            print('WebMenu: Ожидаю доступность сервисного сокета...')
            time.sleep(0.5)
        while self.active:
            print('WebMenu: Ожидаю обновления статуса кнопок...')
            buttons_state = self.server.recv(self.server.serv_socket)
            print(f'WebMenu: RECIEVED MENU BUTTONS STATE: {buttons_state}')
            for button, state in zip(self.buttons[1:], buttons_state):
                button.enable(state)
            
        print('WebMenu: buttons updater stopped')
        
    def enable_button(self, button_name, enable=True):
        for button in self.buttons:
            if button.text == button_name:
                button.enable(enable)


class Button(epg.Sprite, epg.Label):
    RELEASED = 0
    PRESSED = 1
    DISABLED = 2
    def __init__(self, button_image_paths, text, pos, w=50, h=50, savescale=False):
        epg.Sprite.__init__(self, button_image_paths[0], pos, w=w, h=h, savescale=savescale)
        epg.Label.__init__(self, text=text, x=pos[0], y=pos[1], center=True)
        self.skin_index = self.RELEASED
        self.animation_list = []
        self.animation_list.append(self.load_img(img=button_image_paths[self.RELEASED]))
        self.animation_list.append(self.load_img(img=button_image_paths[self.PRESSED]))
        self.animation_list.append(self.load_img(img=button_image_paths[self.DISABLED]))

    
    def set_skin(self, skin_index):
        self.image = self.orig_image = self.animation_list[skin_index]
        self.skin_index = skin_index
    
    def get_pressed(self,):
        if not self.skin_index == self.DISABLED:
            if self.taped(epg.MOUSE) and pg.mouse.get_pressed()[0]:
                self.set_skin(self.PRESSED)
                return True
     #   else:
      #      self.set_skin(self.RELEASED)
      #      return False
    
    def hide(self):
        epg.Sprite.hide(self)
        epg.Label.hide(self)
    
    def show(self):
        epg.Sprite.show(self)
        epg.Label.show(self)
        
    def enable(self, enable=True):
        if enable:
            self.set_skin(self.RELEASED)
        else:
            self.set_skin(self.DISABLED)
            
    def move_to(self, position):
        super().move_to(position)
        super().place_to(position, center=True)


def update():
    epg.update()
    if epg.close_window():
        exit()
    epg.tick(FPS)
    

screen = epg.Screen(EARTH_IMAGE_PATH, width=SCREEN_WIDTH, height=SCREEN_HEIGHT)

server = connection.Conection(URL, PORT)

fighters = []

current_fighter_id = 0

ground_level = SCREEN_HEIGHT - 254

@to_log
def start_game():
    start_game_state = server.get_start()
    print(f'start_game: start game state:{start_game_state}')
    global current_fighter_id
    current_fighter_id = start_game_state.pop('current_player_id')
    ring_nums = start_game_state.pop('rings')
    ring_names = [f'Ринг на {num}' for num in ring_nums]
    ring_names.reverse()
    menu.add_buttons(ring_names, insert_before_existing=True)
    print(f'start_game: В меню добавлены кнопки рингов: {ring_names}')
    while not server.set_service_socket(current_fighter_id):
        log.error('start_game: Попытка повторного создания сервисного сокета через 1 с...')
        time.sleep(1)
    create_fighters(start_game_state, show=False)

def get_str_time(int_time):
    seconds = int_time % 60
    minutes = int_time // 60
    str_time = f'{minutes} : {seconds}'
    return str_time

@to_log
def create_fighters(game_state, show=True):
    global fighters
    for id, player_pos in game_state.items():
        print(f'fighter {id} created')
        direction, x_pos, y_pos = player_pos
        fighters.append(Fighter(animation_pathes=FIGHTER_IMAGE_PATHES,
                        x_pos=x_pos,
                        y_pos=y_pos,
                        flip=direction,
                        wigth=SPRITE_WIDTH, 
                        height=SPRITE_HEIGHT,
                        ground_level=ground_level,
                        gravity=GRAVITY,
                        id=int(id),
                        show=show,
                        ))
 #   return fighters

@to_log
def fight():
    print('Старт игры! Количество игроков', len(fighters))
    while True:
        print()
        game_state = {}
        for fighter in fighters:
            if fighter.id == current_fighter_id:
                options = fighter.check_options()
                game_state = server.get_game_state(options)
                log.info(f'Новый кадр: {game_state}')
        if game_state == 'finish':
            print('получена команда окончания игры!')
            print(f'скрываю следующих файтеров: {fighters}')
            for fighter in fighters:
                fighter.hide()
            print('подтверждаю окончание игры...')
            server.send('OK')
            print('Раунд окончен.')
            return None
        for fighter in fighters:
            fighter_state = game_state.get(str(fighter.id))
            print('FIGHTER STATE', fighter_state)
            if not fighter_state:
                print('Потеряно соеденение. fighter_state отсутствует.')
                print(f'game_state: {game_state}')
                continue
            fighter.apply_game_state(fighter_state)
        timer = game_state.pop('timer')
        if not timer == None:
            label_timer.set_value(get_str_time(timer))
        log.info(f'Timer:{timer}')
        if len(game_state) > len(fighters):
            print('new fighters on server')
            new_fighters = {}
            for fighter_id in game_state.keys():
                print('id существующих игроков:')
                for f in fighters:
                    print(f'{f.id} type:{type(f.id)}')
                if not fighter_id in tuple(str(fighter.id) for fighter in fighters):
                    new_fighter_state = game_state.get(fighter_id)
                    new_fighter_state = (new_fighter_state[4],
                                         new_fighter_state[0],
                                         new_fighter_state[1],
                                        )
                    print('new_fighter_state:', new_fighter_state)
                    new_fighters[fighter_id] = new_fighter_state
            create_fighters(new_fighters)
        update()
    print('end')
    
label_game_over = epg.Label(text='GAME OVER',
                        x=WIDTH_HALF,
                        y=HEIGHT_HALF,
                        size=50,
                        center=True,
                        show=False,
                        )
    
label_timer = epg.Label(text='',
                        val=0,
                        x=WIDTH_HALF,
                        y=100,
                        center=True,
                        size=50,
                        show=False,
                        )
    
menu = WebMenu(server,
            screen,
            BACK_IMAGE_PATH,
            (BUTTON_RELEASED_IMAGE_PATH, BUTTON_PRESSED_IMAGE_PATH, BUTTON_DISABLED_IMAGE_PATH),
            (100, 100),
            button_titles=('выйти', ),
            button_order='h',
            button_margin=80,
            )

while True:
    threading.Thread(target=start_game).start()
    
    print(f'start menu')
    choice = menu.get_choice()

    if choice == 'выйти':
        break
    else:
        choice = int(choice[-1])
        server.send(choice)
        #server.send('Игра началась!')
        screen.set_background(EARTH_IMAGE_PATH)
        label_timer.show()
        fight()
        label_timer.hide()
        fighters = []
        label_game_over.show()
        update()
        time.sleep(5)
        label_game_over.hide()
exit()
