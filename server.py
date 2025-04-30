import logging as mainlog
import socket
import threading
import time
import json
import inspect
import random

ERROR = -1

SCREEN_HEIGHT = 600
SCREEN_WIDTH = 800
GROUND_LEVEL = SCREEN_HEIGHT - 150              #716
START_POSITIONS = (int(SCREEN_WIDTH / 5), 
                   int(SCREEN_WIDTH - SCREEN_WIDTH / 5),
                   int(SCREEN_WIDTH / 5 * 2),
                   int(SCREEN_WIDTH / 5 * 3)
                   )

SERVER = 'localhost'
PORT = 5555

FIGHT_TIME = 60

STAY = 0
GO = 1
JUMP = 2
ATTACK = 3
HITTED = 4
DEAD = 5

CONNECTED = 3 #в меню
WAITING = 2   #ждет от остальных игроков
READY = 1
IN_GAME = 0

LOGGING_LEVEL = mainlog.DEBUG
NOT_LOGGING_FUNCTION = ('apply_options', 'send_data', 'recieve', 'update', 'get_self_state', 'sub_func', 'say')

mainlog.basicConfig(level=LOGGING_LEVEL,
                format='%(levelname)s %(message)s')
log = mainlog.getLogger('log_to_file')
fhandler = mainlog.FileHandler(filename='log.txt', mode='a')
formatter = mainlog.Formatter('%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)s, %(filename)s')

fhandler.setFormatter(formatter)
log.addHandler(fhandler)

ATTACK_DELAY = 5
HITTED_DELAY = 5

PLAYER_SIZE = (130, 130)

GRAVITY = 2

start_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
start_socket.bind((SERVER, PORT))
start_socket.listen(2)
log.info('Сервер запущен')

players = {num:None for num in range(20)}

game_started = False

max_players_num = 0
connected_players_num = 0
alive_players_num = 0

def to_log(func):
    def sub_func(*args, **kwargs):
        if not func.__name__ in NOT_LOGGING_FUNCTION:
            log.info(f"** {func.__name__} **")
        result = func(*args, **kwargs)
        return result
    return sub_func

def log_class(class_to_log, ):
    class_name = class_to_log.__name__
    for name, method in inspect.getmembers(class_to_log):
        if inspect.isfunction(method):
            setattr(class_to_log, name, to_log(method))
    return class_to_log


@log_class
class Player(threading.Thread):
    SERV_SOCKET_TIMEOUT = 10
    def __init__(self, id, socket, gravity):
        super().__init__(daemon=True)
        self.immortal = True
        self.attack_delay = 0
        self.hitted_delay = HITTED_DELAY
        self.action = STAY     # 0 = stay, 1 = go, 2 = jump, 3 = attack, 4 hitted, 5 = dead
        self.id = id
        self.name = f'Игрок {self.id}'
        self.dir = bool(self.id % 2) or False            # True влево, False вправо
        self.health = 100
        self.y_pos = int(GROUND_LEVEL - PLAYER_SIZE[1] / 2)
        self.rect = Rect(PLAYER_SIZE, 
                         START_POSITIONS[self.id], 
                         self.y_pos
                        )
        self.socket = socket
        self.serv_socket = None
        self.fall_speed = 0
        self.jumping = False
        self.gravity = gravity
        self.mode = READY
        
    def wait_for_serv_socket(self):
        self.say('Ожидаю назначения сервисного сокета...')
        timer = 0
        while (not self.serv_socket) and (timer < self.SERV_SOCKET_TIMEOUT):
            time.sleep(0.25)
            timer += 0.25
        return bool(self.serv_socket)

    def set_serv_socket(self, socket):
        self.serv_socket = socket
        send('OK', self.serv_socket)
        self.say('Ответил ОК в сервисный сокет')

    def set_start(self,):
        self.rect.update(START_POSITIONS[self.id], self.y_pos)
        self.health = 100
        self.action = STAY
        self.mode = READY
    
    def attack(self,):
        self.attack_delay = ATTACK_DELAY
        attack_dist = self.rect.width
        if self.dir:
            hit_x = self.rect.center_x - attack_dist / 2
        else:
            hit_x = self.rect.center_x + attack_dist / 2
        hit = Rect(PLAYER_SIZE,
                     hit_x,
                     self.y_pos,
                     )
        for hitted_enemy in hit.get_hitted(self.id): 
            hitted_enemy.hitted()
    
    def hitted(self):
        if self.mode == IN_GAME and not self.immortal:
            if self.health > 0:
                self.health -= 5
                self.action = HITTED
            if self.health < 1 and self.action != DEAD:
                self.action = DEAD
                print(f'player: {self.id} dead!')
    #    print('hitted:health', self.health)
    
    def apply_options(self, options):
        dx = 0
        dy = 0
        # gravitation
        self.fall_speed += self.gravity
        dy = self.fall_speed
        
        # удержание спрайта в пределах экрана
        if (self.rect.left + dx) < 0:       #левая граница экрана
            dx = -self.rect.left
        elif self.rect.right + dx > SCREEN_WIDTH:   #правая граница
            dx = SCREEN_WIDTH - self.rect.right
        if (self.rect.bottom + dy) > GROUND_LEVEL:
            dy = (GROUND_LEVEL - self.rect.bottom)
            self.fall_speed = 0
            self.jumping = False
        
        # controling
        if self.action != DEAD:
            if self.hitted_delay:
                self.action = HITTED
                self.hitted_delay -= 1
            else:
                self.action = STAY
                if options.get('move'):
                    self.action = GO
                if options.get('jump') and not self.jumping:
                    self.fall_speed = -30
                    self.jumping = True
                    self.action = JUMP
                if options.get('hit') and not self.attack_delay:
             #       print('call attack')
                    self.action = ATTACK
                    self.attack()
                dx += options.get('move')
                self.dir = options.get('direction')

        pos_x = self.rect.center_x + dx
        pos_y = self.rect.center_y + dy
        if self.attack_delay:
            self.attack_delay -= 1
        self.rect.update(pos_x, pos_y)
        
    def get_self_state(self):
        return (self.rect.center_x, self.rect.center_y, self.health, self.action, self.dir, self.mode)
    
    def say(self, mes):
        log.info(f'Player {self.id}: {mes}')
    
    def watch_rings(self,):
        prev_rings_state = []
        while self.mode != IN_GAME:
            rings_state = [not ring.game_started for ring in rings.values()]
            if rings_state != prev_rings_state:
                prev_rings_state = rings_state
                self.say(f'состояние рингов поменялось! {rings_state} Отправляю клиенту новое состояние.')
                send(rings_state, self.serv_socket)
            time.sleep(0.1)
        self.say('Наблюдение за рингами остановлено.')
    
    def run(self):
        self.say('Игрок создан!')
        ###
        self.set_start()
        self.say('Формирую стартовое сообщение...')
        initial_data = {'current_player_id': self.id,
                        'rings': tuple(rings.keys()),
                        self.id: (self.dir, self.rect.center_x, self.rect.center_y) 
                        }
        send(initial_data, self.socket)
        self.say(f'start state: {initial_data}')
        client_connected = self.wait_for_serv_socket()
        if client_connected:
            self.say('Сервисный сокет получен')
        else:
            self.say('Слишком долгое ожидание сервисного сокета! Отключаюсь...')
        ###
        while client_connected:
            self.say('Устанавливаю стартовое состояние')
            self.set_start()
            # отсюда перенесено перед циклом
            self.say('Запускаю поток наблюдения за доступностью рингов...')
            threading.Thread(target=self.watch_rings).start()
            self.say('Ожидаю выбор ринга...')
            ring_name = recieve(self.socket)
            if ring_name == ERROR:
                log.error(f'Потерянно соеденение с : {self.name} ')
                client_connected = False
                continue
            self.say(f'Выбран ринг {ring_name}')
            self.say(f'Захожу на ринг')
            ring = rings.get(ring_name)
            ring.add_player(self)
            self.mode = IN_GAME
            while client_connected:                                                    #главный цикл игры
                options = recieve(self.socket)
                if options == ERROR:
                    log.error(f'Потерянно соеденение с : {self.name} игрок отключился')
                    client_connected = False
                    continue
                self.apply_options(options)
                send(ring.get_game_state(), self.socket)
                if not ring.players_on_ring:
                    self.say('GAME OVER')
                    self.say('Вычитываю сокет...')
                    recieve(self.socket)
                    self.say('Отправляю finish...')
                    send('finish', self.socket)
                    self.say('Жду подтверждения конца игры от клиента...')
                    confirm = recieve(self.socket)
                    self.say(f'подтверждение получено: {confirm}. Останавливаю главный цикл.')
                    break
        pl_id = self.id            
        remove_player(self.id)
        log.info(f'player {pl_id}: thread stoped')

class Rect:
    def __init__(self, size, center_x, center_y, ):
        self.width, self.height = size
        self.center_x = center_x
        self.center_y = center_y
        self.update(center_x, center_y)
    
    def update(self, center_x, center_y):
        self.top = int(center_y - self.height / 2)
        self.bottom = int(center_y + self.height / 2)
        self.right = int(center_x + self.width / 2)
        self.left = int(center_x - self.width / 2)
        self.center_x = center_x
        self.center_y = center_y    
    
    def get_hitted(self, my_player_id):
        enemies = []
        for id, player in players.items():
            if player and not id == my_player_id:
                if (player.rect.right >= self.left and
                        player.rect.left <= self.right and
                        player.rect.top <= self.bottom and
                        player.rect.bottom >= self.top):
         #           print('enemys append')
                    enemies.append(player)
        return enemies


class Ring(threading.Thread):
    def __init__(self, players_num, playing_time=10):
        super().__init__(daemon=True)
        self.timer = 0
        self.playing_time = playing_time
        self.players_num = players_num
        self.players = {}
        self.players_on_ring = False
        self.game_started = False
        self.last_winner = None
    
    def say(self, mes):
        log.info(f'Ринг на {self.players_num}: {mes}')
    
    def is_available(self):
        return (self.players_num > len(self.players))
    
    def add_player(self, player):
        self.players[player.id] = player
        self.players_on_ring = True
        self.say(f'Новый игрок! His name is {player.name}') 
        
    def remove_player(self, id):
        player_to_delete = self.players.get(id)
        if player_to_delete:
            self.say(f'Игрок {player_to_delete.name} будет удалён с ринга')
            del self.players[id]
            return True                   
    
    def waiting_for_players(self):
        self.say(f'Жду, когда придёт {self.players_num} игроков...')
        len_players = prev_len_players = len(self.players)
        while len_players > 0 and len_players < self.players_num:
            time.sleep(1)
            len_players = len(self.players)
            if prev_len_players != len_players:
                self.say(f'теперь уже {len_players} игроков!')
                prev_len_players = len_players
    
    def set_immortal(self, immortal=True):
        for player in self.players.values():
            self.say(f'бессмертие для {player.name} - {immortal}')
            player.immortal = immortal
    
    def get_game_state(self):
        game_state = {}
        recent_time = None
        for id, player in self.players.items():
            game_state[id] = player.get_self_state()
        if self.timer != recent_time:
            game_state['timer'] = self.timer
            recent_time = self.timer
        else:
            game_state['timer'] = None
        return game_state
    
    def get_winner(self):
        alive_players = 0
        winner = None
        for player in self.players.values():
            if player.action != DEAD:
                alive_players += 1
                winner = player
        if alive_players == 1:
            return winner
        
    def run(self):
        self.say('Рефери запущен!')
        while threading.active_count() > 1: #???
            if self.players:
                self.waiting_for_players()
                if not self.players:
                    self.say('Все игроки ушли, не дождавшись матча! Перезапускаюсь...')
                    continue
                self.last_winner = None
                log.info(f'Referee: game started!')
                self.set_immortal(False)
                self.game_started = True
                self.timer = FIGHT_TIME
                while self.timer > 0:
                    winner = self.get_winner()
                    if winner:
                        log.info(f'{winner.name} выиграл!')
                        self.last_winner = winner
                        break
                    time.sleep(1)
                    self.timer -= 1
                self.game_started = False
                log.info(f'Referee: game over!')
                self.set_immortal()
                self.players.clear()
                self.players_on_ring = False
                print()
            else:
                time.sleep(0.25)
        log.info(f'Ринг на {self.players_num} остановлен!')
        

@to_log
def remove_player(id):
    global connected_players_num
    players[id].socket.close()
    players[id] = None
    for ring in rings.values():
        if ring.remove_player(id):
            break
    log.debug(f'игрок закончился с id : {id}')
    connected_players_num -= 1

def send(data, client_socket):
    try:
        str_data = json.dumps(data)
        byte_data = str_data.encode()
        client_socket.send(byte_data)
    except Exception as err:
        log.error(f'connection error : {err}')

def recieve(client_socket,):
    try:
        raw_data = client_socket.recv(1024)
        str_data = raw_data.decode()
        data = json.loads(str_data)
    except Exception as err:
        log.error(f'{err}')
        data = ERROR
    finally:
        return data

@to_log
def choice_waiting(current_player):
    log.debug('new choice waiting thread created')
    initial_data = {'current_player_id': current_player.id,
                    'rings': tuple(rings.keys()), 
                    }
    for id, player in players.items():
        if player:
            initial_data[id] = (player.dir,
                               player.rect.center_x, 
                               player.rect.center_y, 
                               player.rect.width,
                               player.rect.height,
                               )
    send(initial_data, current_player.socket)
    menu_updater()
    ring_num = recieve(current_player.socket)
    if ring_num == ERROR:
        log.error(f'Потерянно соеденение с : {current_player.id} ')
        remove_player(current_player.id)
        return
    log.info(f'player {current_player.id} chose to ring {ring_num}')       
    rings.get(ring_num).add_player(current_player)
    menu_updater()

@to_log
def menu_updater():
    rings_state = {ring_name: ring.is_available() for ring_name, ring in rings.items()}
    for player in players.values():
        if player:
            while not player.serv_socket:
                time.sleep(0.3)
                log.debug(f'wait for serv_socket on player {player.id}')
            send(rings_state, player.serv_socket)

ring2 = Ring(2)
ring3 = Ring(3)
ring4 = Ring(4)
ring2.start()
ring3.start()
ring4.start()
#threading.Thread(target=threaded_referee, daemon=True).start()
#создать объект ринга и админа

rings = {2 : ring2,
         3 : ring3,
         4 : ring4,
        }

while True:
    player_socket, adress = start_socket.accept()
    log.info(f'Подключение с адреса : {adress}')
    socket_status = recieve(player_socket)
    log.debug(f'socket status: {socket_status}')
    if type(socket_status) == int:
        if socket_status in players.keys():
            player = players.get(socket_status)
            player.set_serv_socket(player_socket)
            log.debug(f'service socket setted to player {player.id}')
        else:
            log.error(f'Cant add socket! invalid player id.')
    else:
        for id, player_in_slot in players.items():
            if not player_in_slot:
                if socket_status == 'main':
                    player = Player(id, player_socket, GRAVITY)
                    players[id] = player
                    connected_players_num += 1
                    player.start()
                    #threading.Thread(target=threaded_player, args=(player,), daemon=True).start()
                    #threading.Thread(target=choice_waiting, args=(player,), daemon=True).start()
                    break
        else:
            print('Сокет закрыт. Ошибка или максимальное количество игроков')
            player_socket.close()
        