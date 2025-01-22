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
FIGHTER_IMAGE_PATHES = (os.path.join(PROJECT_DIR, 'photos\\stay.png'),
                        os.path.join(PROJECT_DIR, 'photos\\go.png'),
                        os.path.join(PROJECT_DIR, 'photos\\jump.png'),
                        os.path.join(PROJECT_DIR, 'photos\\attack.png'),
                        os.path.join(PROJECT_DIR, 'photos\\hitted.png'),
                        os.path.join(PROJECT_DIR, 'photos\\dead.png'),
                        )

BUTTON_RELEASED_IMAGE_PATH = 'photos/released.jpeg'
BUTTON_PRESSED_IMAGE_PATH = 'photos/pressed.jpeg'
BUTTON_DISABLED_IMAGE_PATH = 'photos/disabled.jpeg'

SERVER = 'localhost'
PORT = 5555


@log_class
class Menu():
    def __init__(self, screen,
                 menu_background_img_path, 
                 button_titles, 
                 button_img_paths, 
                 button_size, 
                 button_order='v', 
                 button_margin=100,
                ):
        self.background_path = menu_background_img_path
        self.screen = screen
        if button_order == 'v':
            button_x = int(SCREEN_WIDTH / 2)
            button_y = button_margin + int(button_size[1] / 2)
        else:
            button_x = button_margin + int(button_size[0] / 2)
            button_y = int(SCREEN_HEIGHT / 2)
        self.buttons = []
        for title in button_titles:
            button_pos = (button_x, button_y)
            self.buttons.append(Button(button_img_paths, 
                                       title,
                                       button_pos,
                                       w=button_size[0],
                                       h=button_size[1],
                                       ))
            if button_order == 'v':
                button_y += button_size[1] + button_margin
            else:
                button_x += button_size[0] + button_margin
                
    def get_choice (self, labels=[]):
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
        menu = True
        while menu:
            update()
            for button in self.buttons:
                if button.get_pressed():
                    choice = button.text
                    update()
                    time.sleep(0.5)
                    menu = False
                    button.set_skin(button.RELEASED)
        for button in self.buttons:
            button.hide()
        for label in labels:
            label.hide()
        return choice
        
    def enable_button(self, button_name, enable=True):
        for button in self.buttons:
            if button.text == button_name:
                button.enable(enable)


@log_class
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


def update():
    epg.update()
    if epg.close_window():
        exit()
    epg.tick(FPS)
    

screen = epg.Screen(EARTH_IMAGE_PATH, width=SCREEN_WIDTH, height=SCREEN_HEIGHT)

server = connection.Conection(SERVER, PORT)

fighters = []

current_fighter_id = 0

ground_level = SCREEN_HEIGHT - 254

@to_log
def start_game():
    start_game_state = server.get_start()
    print(f'start game state:{start_game_state}')
    global current_fighter_id
    current_fighter_id = start_game_state.pop('current_player_id')
    create_fighters(start_game_state, show=False)
    menu.enable_button('играть')

def get_str_time(int_time):
    seconds = int_time % 60
    minutes = int_time // 60
    str_time = f'{minutes} : {seconds}'
    return str_time

@to_log
def create_fighters(game_state, show=True):
    global fighters
#    fighters = []
    for id, player_pos in game_state.items():
        print(f'fighter {id} created')
        dir, x_pos, y_pos, wigth, height = player_pos
        fighters.append(Fighter(animation_pathes=FIGHTER_IMAGE_PATHES,
                        x_pos=x_pos,
                        y_pos=y_pos,
                        flip=dir,
                        wigth=wigth, 
                        height=height,
                        ground_level=ground_level,
                        gravity=GRAVITY,
                        id=int(id),
                        show=show,
                        ))
 #   return fighters
@to_log
def fight():
    print('файтеры', len(fighters))
    while True:
        game_state = {}
        for fighter in fighters:
            if fighter.id == current_fighter_id:
                options = fighter.check_options()
                game_state = server.get_game_state(options)
            fighter.show()
        if game_state == 'finish':
            for fighter in fighters:
                fighter.hide()
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
                for fighter in fighters:
                    print('fighter_id:', fighter_id, 'fighter.id:', fighter.id)
                    if fighter_id != str(fighter.id):
                        new_fighter_state = game_state.get(fighter_id)
                        new_fighter_state = (new_fighter_state[4],
                                             new_fighter_state[0],
                                             new_fighter_state[1],
                                             SPRITE_WIDTH,
                                             SPRITE_HEIGHT,
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
    
menu = Menu(screen,
            BACK_IMAGE_PATH, 
            ('играть', 'выйти', 'Ринг на 2', 'Ринг на 3', 'Ринг на 4'),
            (BUTTON_RELEASED_IMAGE_PATH, BUTTON_PRESSED_IMAGE_PATH, BUTTON_DISABLED_IMAGE_PATH),
            (100, 100),
            button_order='h',
            button_margin=80,
            )

while True:
    menu.enable_button('играть', False)

    threading.Thread(target=start_game).start()
    
    print(f'start menu')
    choice = menu.get_choice()

    if choice == 'выйти':
        break

    if choice == 'играть':
        server.send('Игра началась!')
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
