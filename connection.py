import socket
import json

class Conection :
    def __init__(self, url, port):
        self.main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.main_socket.connect((url, port))
        self.send('main')
        self.serv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serv_socket.connect((url, port))
        self.send('service', self.serv_socket)

    def get_start(self):
        return self.recv()
    
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
    
    