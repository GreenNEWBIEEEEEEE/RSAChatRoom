import socket
import threading
import json
import rsa
import base64
import struct
from rsa import PublicKey, PrivateKey
from cmd import Cmd


class Client(Cmd):
    """
    客户端
    """
    prompt = ''
    intro = '[Welcome] 简易聊天室客户端(Cli版)\n' + '[Welcome] 输入help来获取帮助\n'

    def __init__(self):
        """
        构造
        """
        super().__init__()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__id = None
        self.__nickname = None
        self.__isLogin = False
        self.__pubKey, self.__privKey = rsa.newkeys(1024)
        self.__usersPubKey = list()
        #print(self.__pubKey['n'])
        #print(self.__pubKey['e'])

    def __turnPubKeyToList(self, pubk):
        n = pubk['n']
        e = pubk['e']
        return [n, e]


    def __receive_message_thread(self):
        """
        接受消息线程
        """
        while self.__isLogin:
        # noinspection PyBroadException
            try:
                buffer = self.__recv_one_message(self.__socket).decode()
                obj = json.loads(buffer)
                if (obj['type'] == 'login' or obj['type'] == 'logout'):
                    self.__usersPubKey = obj['otherUsersPubKey']
                else:
                    print('[' + str(obj['sender_nickname']) + '(' + str(obj['sender_id']) + ')' + ']', self.__decryptMessage(obj['message']))
            except Exception:
                print('[Client] 无法从服务器获取数据')

    def __send_one_message(self, sock, data): # input bytes
        length = len(data)
        sock.sendall(struct.pack('!I', length))
        sock.sendall(data)

    def __recvall(self, sock, count):
        buf = b''
        while count:
            newbuf = sock.recv(count)
            if not newbuf: return None
            buf += newbuf
            count -= len(newbuf)
        return buf

    def __recv_one_message(self, sock):  #return jsonObject
        lengthbuf = self.__recvall(sock, 4)
        length, = struct.unpack('!I', lengthbuf)
        return self.__recvall(sock, length)


    def __encryptMessage(self, receiver_id, message):
        n, e = self.__usersPubKey[receiver_id][0], self.__usersPubKey[receiver_id][1]
        #print(n)
        #print(e)
        message = message.encode('UTF-8')
        message = rsa.encrypt(message, PublicKey(n, e))
        message = base64.b64encode(message)
        message = message.decode('UTF-8')
        #print(message)
        return message

    def __decryptMessage(self, message):
        #print(message)
        message = message.encode('UTF-8')
        message = base64.b64decode(message)
        message = rsa.decrypt(message, self.__privKey)
        message = message.decode('UTF-8')
        return message


    def __send_message_thread(self, message):
        """
        发送消息线程
        :param message: 消息内容
        """
        for receiver_id in range(len(self.__usersPubKey)):
            if (receiver_id != self.__id and self.__usersPubKey[receiver_id] != None):
                mesg = ''
                mesg = self.__encryptMessage(receiver_id, message)
                jsonByte = json.dumps({
                    'type': 'sendMessage',
                    'sender_id': self.__id,
                    'receiver_id': receiver_id,
                    'message': mesg
                }).encode()

                self.__send_one_message(self.__socket, jsonByte)

    def start(self):
        """
        启动客户端
        """
        self.__socket.connect(('127.0.0.1', 8888))
        self.cmdloop()

    def do_login(self, args):
        """
        登录聊天室
        :param args: 参数
        """
        nickname = args.split(' ')[0]

        # 将昵称发送给服务器，获取用户id
        jsonByte = json.dumps({
            'type': 'login',
            'nickname': nickname,
            'pubkey': self.__turnPubKeyToList(self.__pubKey)
        }).encode()

        self.__send_one_message(self.__socket, jsonByte)

        # 尝试接受数据
        # noinspection PyBroadException
        try:
            buffer = self.__recv_one_message(self.__socket).decode()
            obj = json.loads(buffer)

            if obj['id']:
                self.__nickname = nickname
                self.__id = obj['id']
                self.__isLogin = True
                print('[Client] 成功登录到聊天室')

                # 开启子线程用于接受数据
                thread = threading.Thread(target=self.__receive_message_thread)
                thread.setDaemon(True)
                thread.start()
            else:
                print('[Client] 无法登录到聊天室')
        except Exception:
            print('[Client] 无法从服务器获取数据')

    def do_send(self, args):
        """
        发送消息
        :param args: 参数
        """
        message = args
        # 显示自己发送的消息
        print('[' + str(self.__nickname) + '(' + str(self.__id) + ')' + ']', message)
        # 开启子线程用于发送数据
        thread = threading.Thread(target=self.__send_message_thread, args=(message,))
        thread.setDaemon(True)
        thread.start()

    def do_logout(self, args=None):
        """
        登出
        :param args: 参数
        """
        jsonByte = json.dumps({
            'type': 'logout',
            'sender_id': self.__id
        }).encode()
        self.__send_one_message(self.__socket, jsonByte)
        self.__isLogin = False
        return True

    def do_help(self, arg):
        """
        帮助
        :param arg: 参数
        """
        command = arg.split(' ')[0]
        if command == '':
            print('[Help] login nickname - 登录到聊天室，nickname是你选择的昵称')
            print('[Help] send message - 发送消息，message是你输入的消息')
            print('[Help] logout - 退出聊天室')
        elif command == 'login':
            print('[Help] login nickname - 登录到聊天室，nickname是你选择的昵称')
        elif command == 'send':
            print('[Help] send message - 发送消息，message是你输入的消息')
        elif command == 'logout':
            print('[Help] logout - 退出聊天室')
        else:
            print('[Help] 没有查询到你想要了解的指令')
