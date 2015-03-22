#!/usr/bin/env python2.7
""" gui.py

A GUI client for hysbakstryd.

Usage:

    gui.py
"""
import gevent
import time
import pygameui as ui
# from docopt import docopt
from gui.scenes import LoadingScene, MapScene
import msgpack
import logging
import sys


class NetworkClient(object):

    sockname = None

    def __init__(self, host='127.0.0.1', port=8001, **kw):
        self.host = host
        self.port = int(port)
        self.socket = None

    def send_msg(self, msg):
        logging.info("send: {}".format(msg))
        pack = msgpack.packb(msg)
        self.socket.send(pack)

    def close(self):
        pass

    def inform(self, *msg):
        logging.info(msg)

    def connect(self, username, password, **kw):
        logging.info('Connecting...')
        try:
            self._socket = socket.create_connection((self.host, self.port))
        except socket.error as e:
            logging.error('Connection refused: {}'.format(e))
        except:
            logging.error('Connection error:')
            logging.error(traceback.format_exception())

        try:
            self.send_msg(dict(type="connect", username=username, password=password, observe=True))
            self.sockname = "{}".format(self._socket.getsockname()[1])
            unpacker = msgpack.Unpacker(encoding='utf-8')
            pack = True  # We set this value just to jump into the while loop
            while pack:
                pack = self._socket.recv(1024)
                unpacker.feed(pack)
                for msg in unpacker:
                    self.inform(*msg)
            logging.info('The server closed the connection')
        finally:
            logging.info("close ...")
            self.close()

    def keyboardinput(self, input_message):
        pass


class Observer(NetworkClient):

    def __init__(self, *args, **kw):
        super(Observer, self).__init__(*args, **kw)
        self.map = []
        self.ignore_list = []

    def inform(self, msg_type, from_id, data):
        try:
            handler = getattr(self, "handle_{}".format(msg_type))
            ret = handler(data)
            logging.info("{}: {}, {}".format(from_id, msg_type, ret))

        except AttributeError:
            logging.error("{}({}): {}".format(from_id, msg_type, data))
            if msg_type not in self.ignore_list:
                self.ignore_list.append(msg_type)
                logging.warning("No handler for '{}'".format(msg_type))

    def handle_ERR(self, data):
        logging.error(data)

    def handle_TRACEBACK(self, data):
        logging.error(data)

    def handle_RESHOUT(self, data):
        logging.info(data)

    def handle_WELCOME(self, data):
        print("Juhu, ready for take off")
        # import time
        # time.sleep(1)
        # self.send_msg(dict(type="set_level", level=5))
        # self.send_msg(dict(type="set_direction", direction="up"))
        # time.sleep(2)
        # self.send_msg(dict(type="set_level", level=1))
        # self.send_msg(dict(type="set_level", level=4))
        pass

    def handle_LEVELS(self, data):
        pass


def main_loop():
    logging.info("main_loop")
    now = last = time.time()
    time_per_frame = 1 / 30

    while True:
        # 30 frames per second, considering computation/drawing time
        gevent.sleep(last + time_per_frame - now)
        last, now = now, time.time()
        dt = now - last
        if ui.single_loop_run(dt*1000):
            print("main_loop end")
            return


def main(arguments):
    # init async and pygame
    ui.init("hysbakstryd", (900, 700))

    # show loading scene
    ui.scene.push(LoadingScene())
    map_scene = MapScene()
    ui.scene.insert(0, map_scene)

    # from bomber.network import ClientStub
    # loop.call_soon(map_scene.map.player_register, ClientStub(None, None, map_scene.map))
    client = Observer(**arguments)

    # show game ui
    ui.scene.pop()
    try:
        main_loop_g = gevent.spawn(main_loop)
        client_g = gevent.spawn(client.connect, **arguments)
        gevent.joinall([main_loop_g, client_g])
    finally:
        logging.info("... BYE ...")


def load_config():
    import yaml
    try:
        with open("config.yaml") as fh:
            return yaml.load(fh.read())
    except IOError:
        logging.info("Meh, keine config.yaml gefunden")
        return {}
    except:
        logging.info("Meh, config.yaml gefunden, kann aber nicht geladen werden, wird ignoriert.")
        return {}


if __name__ == "__main__":
    # arguments = docopt(__doc__, version='bomber 0.1')
    default_args = {
        "host": "localhost",
        "port": "8001",
    }
    default_args.update(load_config())
    if len(sys.argv) >= 2:
        default_args["username"] = sys.argv[1]
    if len(sys.argv) >= 3:
        default_args["password"] = sys.argv[2]

    main({})
