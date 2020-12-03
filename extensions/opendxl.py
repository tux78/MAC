import logging
import queue
import json
from typing import TypedDict
from utils import IntegrationHandler

from dxlclient.callbacks import EventCallback
from dxlclient.message import Event

from dxltieclient import TieClient
from dxltieclient.constants import HashType, TrustLevel, FileType, FileProvider, ReputationProp

class OpenDXL:

    def __init__(self, topic):
        self.client = IntegrationHandler().dxl.Client
        self.topic = topic
        self.queue = queue.Queue()
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

    def setTieReputation(self, payload):
        tie_client = TieClient(self.client)

        hashes = {
            HashType.MD5: payload['fileMD5'],
            HashType.SHA1: payload['fileSHA1'],
            HashType.SHA256: payload['fileSHA256']
        }
        reputations_dict = tie_client.get_file_reputation(hashes)

        has_definitive_reputation = \
            any([rep[ReputationProp.TRUST_LEVEL] != TrustLevel.NOT_SET
                 and rep[ReputationProp.TRUST_LEVEL] != TrustLevel.UNKNOWN
                 and rep[ReputationProp.PROVIDER_ID] != FileProvider.EXTERNAL
                 for rep in reputations_dict.values()])

        if not has_definitive_reputation:
            try:
                tie_client.set_external_file_reputation(
                    TrustLevel.MIGHT_BE_TRUSTED,
                    hashes,
                    file_type=payload['filetype'],
                    filename=payload['filename'],
                    comment=payload['comment']
                )
            except ValueError as e:
                pass
