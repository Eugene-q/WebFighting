import socket
import json


class Conection :
    def __init__(self, url, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((url, port))

    def get_start(self):
        return self.recv()
    
    def get_game_state(self, options):
        self.send(options)
        game_state = self.recv()
        return game_state
    
    def recv(self, ):
        data = {}
        try:
            response = self.server.recv(1024)
       #     print('recv bytes', response)
            str_data = response.decode()
            data = json.loads(str_data) 
        except Exception as err:
            print('connection error : ', err)
        return data

    
    def send(self, data):
        try:
            str_options = json.dumps(data)
            byte_options = str_options.encode()
            self.server.send(byte_options)
#            response = self.server.recv(1024)
        except Exception as err:
            print('connection error : ', err)
    
    