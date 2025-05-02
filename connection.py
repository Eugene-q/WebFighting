import socket
import json
import time

class Conection :
    def __init__(self, url, port):
        self.address = (url, port)
        print('Открываю главный сокет...')
        self.main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Открываю сервисный сокет...')
        self.serv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.main_socket_available = False
        self.serv_socket_available = False

    def get_start(self):
        return self.recv()
    
    def serv_socket_connect(self, fighter_id):
        if not self.serv_socket_available:
            print('Connection: подключаю сервисный сокет...')
            self.connect_socket(self.serv_socket, fighter_id)
            self.serv_socket_available = True
        
    def main_socket_connect(self):
        if not self.main_socket_available:
            print('Connection: подключаю главный сокет...')
            self.connect_socket(self.main_socket, 'main')
            self.main_socket_available = True

    def connect_socket(self, socket, handshake):
        socket_connected = False
        while not socket_connected:
            try:
                print('Connection: подключаю...')
                socket.connect(self.address)
                print(f'Отправляю handshake {handshake}...')
                self.send(handshake, socket)
                print('Ожидаю прдтверждения handshake...')
                confirm = self.recv(socket)
                if confirm == 'OK':
                    print(f'сокет {handshake} подтверждён.')
                    socket_connected = True
                else:
                    print(f'Ошибка подтверждения сокета! handshake: {handshake}')
                    print(f'Ответ: {confirm}')
                    print('Сокет будет закрыт.')
                    self.socket.close()
                    time.sleep(0.5)
            except Exception as e:
                print('Ошибка подключения сокета:', e)
                print('Пробую ещё раз...')
                time.sleep(0.5)
        print('Connection: сокет подключён!')
        return socket_connected
    
    def get_game_state(self, options):
        self.send(options)
        game_state = self.recv()
        return game_state
    
    def recv(self, socket=None):
        socket = socket or self.main_socket
        data = {}
        try:
            response = socket.recv(1024)
       #     print('recv bytes', response)
            str_data = response.decode()
            data = json.loads(str_data) 
        except Exception as err:
            print('connection error : ', err)
        return data

    
    def send(self, data, socket=None):
        socket = socket or self.main_socket
        try:
            str_data = json.dumps(data)
            byte_data = str_data.encode()
            socket.send(byte_data)
            print(f'sended: {data}')
#            response = self.server.recv(1024)
        except Exception as err:
            print('connection error : ', err)
    
    