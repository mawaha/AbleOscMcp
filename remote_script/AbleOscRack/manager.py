from ableton.v2.control_surface import ControlSurface

from . import ableoscrack

import importlib
import traceback
import logging
import os

logger = logging.getLogger("ableoscrack")


class Manager(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)

        self.handlers = []

        try:
            self.osc_server = ableoscrack.OSCServer()
            self.schedule_message(0, self.tick)

            self.start_logging()
            self.init_api()

            self.show_message("AbleOscRack: Listening on port %d" % ableoscrack.OSC_LISTEN_PORT)
            logger.info("Started AbleOscRack on %s" % str(self.osc_server._local_addr))
        except OSError as msg:
            self.show_message("AbleOscRack: Couldn't bind to port %d (%s)" % (ableoscrack.OSC_LISTEN_PORT, msg))
            logger.error("Couldn't bind to port %d (%s)" % (ableoscrack.OSC_LISTEN_PORT, msg))

    def start_logging(self):
        module_path = os.path.dirname(os.path.realpath(__file__))
        log_dir = os.path.join(module_path, "logs")
        if not os.path.exists(log_dir):
            os.mkdir(log_dir, 0o755)
        log_path = os.path.join(log_dir, "ableoscrack.log")
        self.log_file_handler = logging.FileHandler(log_path)
        self.log_file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('(%(asctime)s) [%(levelname)s] %(message)s')
        self.log_file_handler.setFormatter(formatter)
        logger.addHandler(self.log_file_handler)

        class LiveOSCErrorLogHandler(logging.StreamHandler):
            def emit(handler, record):
                message = record.getMessage()
                try:
                    message = message[message.index(":") + 2:]
                except ValueError:
                    pass
                try:
                    self.osc_server.send("/live/error", (message,))
                except OSError:
                    pass

        self.live_osc_error_handler = LiveOSCErrorLogHandler()
        self.live_osc_error_handler.setLevel(logging.ERROR)
        logger.addHandler(self.live_osc_error_handler)

    def stop_logging(self):
        logger.removeHandler(self.log_file_handler)
        logger.removeHandler(self.live_osc_error_handler)

    def init_api(self):
        def test_callback(params):
            self.show_message("AbleOscRack: OSC OK")
            self.osc_server.send("/live/test", ("ok",))

        def reload_callback(params):
            self.reload_imports()

        self.osc_server.add_handler("/live/test", test_callback)
        self.osc_server.add_handler("/live/api/reload", reload_callback)

        with self.component_guard():
            self.handlers = [
                ableoscrack.RackHandler(self),
            ]

    def clear_api(self):
        self.osc_server.clear_handlers()
        for handler in self.handlers:
            handler.clear_api()

    def tick(self):
        self.osc_server.process()
        self.schedule_message(1, self.tick)

    def reload_imports(self):
        try:
            importlib.reload(ableoscrack.osc_server)
            importlib.reload(ableoscrack.handler)
            importlib.reload(ableoscrack.rack)
            importlib.reload(ableoscrack)
        except Exception:
            logging.warning(traceback.format_exc())

        self.clear_api()
        self.init_api()
        logger.info("Reloaded AbleOscRack code")

    def disconnect(self):
        self.show_message("AbleOscRack: Disconnecting...")
        logger.info("Disconnecting...")
        self.stop_logging()
        self.osc_server.shutdown()
        super().disconnect()
