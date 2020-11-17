import logging
import queue

from dxlclient.callbacks import EventCallback
from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig
from dxlclient.message import Event

class opendxl:

    def __init__(self, configFile, topic):
        self.topic = topic
        self.config = DxlClientConfig.create_dxl_config_from_file(configFile)
        self.queue = queue.Queue()
        self.client = DxlClient(self.config)
        self.client.connect()
        self._listenerStarted = False

    def __del__(self):
        self.client.destroy()

    def _startDxlListener(self):
        self._listenerStarted = True

        class MyEventCallback(EventCallback):

            def __init__(self, queue: queue):
                self.queue = queue

            def on_event(self, event):
                self.queue.put(event.payload.decode())

        self.client.add_event_callback(self.topic, MyEventCallback(self.queue))

    def getMessage(self, sentinel, interval):
        if not self._listenerStarted:
            self._startDxlListener()
        while not sentinel.is_set():
            if not self.queue.empty():
                yield self.queue.get()

    def sendMessage(self, payload):
        event = Event(self.topic)
        event.payload = str(payload).encode()
        self.client.send_event(event)

