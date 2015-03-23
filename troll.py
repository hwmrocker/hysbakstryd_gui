""" gui.py

a bomberman clone server.

Usage:

    gui.py
"""
import sys
import trollius as asyncio
from trollius import From, Return
import time
import pygameui as ui
# from docopt import docopt
from gui.scenes import LoadingScene, MapScene
import yaml
import logging
import logging.config
import traceback
import msgpack


class NetworkClient(object):

    sockname = None

    def __init__(self, host='127.0.0.1', port=8001, **kw):
        super(NetworkClient, self).__init__()
        self.host = host
        self.port = int(port)

        self.reader = None
        self.writer = None

    def send_msg(self, msg):
        logging.info("send: {}".format(msg))
        pack = msgpack.packb(msg)
        self.writer.write(pack)

    def close(self):
        if self.writer:
            self.writer.write_eof()

    def inform(self, *msg):
        logging.info(msg)

    @asyncio.coroutine
    def connect(self, username, password, **kw):
        logging.info('Connecting...')
        try:
            reader, writer = yield From(asyncio.open_connection(self.host, self.port))
            self.reader = reader
            self.writer = writer
            self.send_msg(dict(type="connect", username=username, password=password, observe=True))
            self.sockname = writer.get_extra_info('sockname')
            unpacker = msgpack.Unpacker(encoding='utf-8')
            logging.info("reader eof? {}".format(repr(reader.at_eof())))
            while not reader.at_eof():
                pack = yield From(reader.read(1024))
                unpacker.feed(pack)
                for msg in unpacker:
                    self.inform(*msg)
            logging.info('The server closed the connection')
            self.writer = None
        except ConnectionRefusedError as e:
            logging.info('Connection refused: {}'.format(e))
        except Exception as e:
            logging.error("WTF did just happend?")
            logging.error(traceback.format_exception())
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
        logging.info("{} send: {} {}".format(from_id, msg_type, data))
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
        print("welcome", repr(data))
        # import time
        # time.sleep(1)
        # self.send_msg(dict(type="set_level", level=5))
        # self.send_msg(dict(type="set_direction", direction="up"))
        # time.sleep(2)
        # self.send_msg(dict(type="set_level", level=1))
        # self.send_msg(dict(type="set_level", level=4))

    def handle_LEVELS(self, data):
        pass


@asyncio.coroutine
def main_loop(loop):
    now = last = time.time()
    time_per_frame = 1 / 30

    while True:
        # 30 frames per second, considering computation/drawing time
        yield From(asyncio.sleep(last + time_per_frame - now))
        last, now = now, time.time()
        dt = now - last
        if ui.single_loop_run(dt*1000):
            raise Return()


def main(arguments):
    # init async and pygame
    loop = asyncio.get_event_loop()
    ui.init("hysbakstryd", (900, 700))

    # show loading scene
    ui.scene.push(LoadingScene())
    map_scene = MapScene()
    ui.scene.insert(0, map_scene)

    # from bomber.network import ClientStub
    # loop.call_soon(map_scene.map.player_register, ClientStub(None, None, map_scene.map))
    client = Observer(**arguments)
    asyncio.async(client.connect(**arguments))
    # show game ui
    ui.scene.pop()
    try:
        loop.run_until_complete(main_loop(loop))
    finally:
        loop.close()


def setup_logging():
    with open("logger.conf.yaml") as fh:
        config = yaml.load(fh)
    logging.config.dictConfig(config)


def load_config():
    import yaml
    try:
        with open("config.yaml") as fh:
            return yaml.load(fh.read())
    except FileNotFoundError:
        logging.info("Meh, keine config.yaml gefunden")
        return {}
    except:
        logging.info("Meh, config.yaml gefunden, kann aber nicht geladen werden, wird ignoriert.")
        return {}


if __name__ == "__main__":
    # arguments = docopt(__doc__, version='bomber 0.1')
    setup_logging()
    default_args = {
        "host": "localhost",
        "port": "8001",
    }
    default_args.update(load_config())
    if len(sys.argv) >= 2:
        default_args["username"] = sys.argv[1]
    if len(sys.argv) >= 3:
        default_args["password"] = sys.argv[2]

    main(default_args)
