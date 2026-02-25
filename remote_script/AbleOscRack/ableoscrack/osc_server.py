from typing import Tuple, Any, Callable
from .constants import OSC_LISTEN_PORT, OSC_RESPONSE_PORT
from ..pythonosc.osc_message import OscMessage, ParseError
from ..pythonosc.osc_bundle import OscBundle
from ..pythonosc.osc_message_builder import OscMessageBuilder, BuildError

import re
import errno
import socket
import logging
import traceback

class OSCServer:
    def __init__(self,
                 local_addr: Tuple[str, int] = ('0.0.0.0', OSC_LISTEN_PORT),
                 remote_addr: Tuple[str, int] = ('127.0.0.1', OSC_RESPONSE_PORT)):
        self._local_addr = local_addr
        self._remote_addr = remote_addr
        self._response_port = remote_addr[1]

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setblocking(0)
        self._socket.bind(self._local_addr)
        self._callbacks = {}

        self.logger = logging.getLogger("ableoscrack")
        self.logger.info("Starting OSC server (local %s, response port %d)",
                         str(self._local_addr), self._response_port)

    def add_handler(self, address: str, handler: Callable) -> None:
        self._callbacks[address] = handler

    def clear_handlers(self) -> None:
        self._callbacks = {}

    def send(self,
             address: str,
             params: Tuple = (),
             remote_addr: Tuple[str, int] = None) -> None:
        msg_builder = OscMessageBuilder(address)
        for param in params:
            msg_builder.add_arg(param)

        try:
            msg = msg_builder.build()
            if remote_addr is None:
                remote_addr = self._remote_addr
            self._socket.sendto(msg.dgram, remote_addr)
        except BuildError:
            self.logger.error("AbleOscRack: OSC build error: %s" % (traceback.format_exc()))

    def process_message(self, message, remote_addr):
        if message.address in self._callbacks:
            callback = self._callbacks[message.address]
            rv = callback(message.params)

            if rv is not None:
                assert isinstance(rv, tuple)
                remote_hostname, _ = remote_addr
                response_addr = (remote_hostname, self._response_port)
                self.send(address=message.address,
                          params=rv,
                          remote_addr=response_addr)
        elif "*" in message.address:
            regex = message.address.replace("*", "[^/]+")
            for callback_address, callback in self._callbacks.items():
                if re.match(regex, callback_address):
                    try:
                        rv = callback(message.params)
                    except ValueError:
                        continue
                    except AttributeError:
                        continue
                    if rv is not None:
                        assert isinstance(rv, tuple)
                        remote_hostname, _ = remote_addr
                        response_addr = (remote_hostname, self._response_port)
                        self.send(address=callback_address,
                                  params=rv,
                                  remote_addr=response_addr)
        else:
            self.logger.error("AbleOscRack: Unknown OSC address: %s" % message.address)

    def process_bundle(self, bundle, remote_addr):
        for i in bundle:
            if OscBundle.dgram_is_bundle(i.dgram):
                self.process_bundle(i, remote_addr)
            else:
                self.process_message(i, remote_addr)

    def parse_bundle(self, data, remote_addr):
        if OscBundle.dgram_is_bundle(data):
            try:
                bundle = OscBundle(data)
                self.process_bundle(bundle, remote_addr)
            except ParseError:
                self.logger.error("AbleOscRack: Error parsing OSC bundle: %s" % (traceback.format_exc()))
        else:
            try:
                message = OscMessage(data)
                self.process_message(message, remote_addr)
            except ParseError:
                self.logger.error("AbleOscRack: Error parsing OSC message: %s" % (traceback.format_exc()))

    def process(self) -> None:
        try:
            while True:
                data, remote_addr = self._socket.recvfrom(65536)
                self._remote_addr = (remote_addr[0], OSC_RESPONSE_PORT)
                self.parse_bundle(data, remote_addr)

        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                self.logger.warning("AbleOscRack: Non-fatal socket error: %s" % (traceback.format_exc()))
            elif e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                pass
            else:
                self.logger.error("AbleOscRack: Socket error: %s" % (traceback.format_exc()))

        except Exception as e:
            self.logger.error("AbleOscRack: Error handling OSC message: %s" % e)
            self.logger.warning("AbleOscRack: %s" % traceback.format_exc())

    def shutdown(self) -> None:
        self._socket.close()
