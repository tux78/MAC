import base64
import json
import threading
from utils import IntegrationHandler

class ESM():

    def __init__(self, get_details=False):

        self.session = IntegrationHandler().esm.Session
        self.get_details = get_details

    def dsGetDataSourceListOnce(self):

        # Get all devices from ESM
        self.device_id = []
        payload = {'types' : ['RECEIVER'] }
        response = self.session.call_API('devGetDeviceList?filterByRights=false', payload)
        for erc in response:
            self.device_id.append(erc['id'])

        for erc in self.device_id:
            dslist = []
            payload = {'receiverId' : erc}
            retVal = self.session.call_API('dsGetDataSourceList', payload)

            if (self.get_details):
                for ds in retVal:
                    payload = {'datasourceId' : str(ds['id'])}
                    parent = self.session.call_API('dsGetDataSourceDetail', payload)
                    parent['id'] = str(ds['id'])
                    dslist.append (parent)
            else:
                dslist = retVal

            # Create and send message
            payload = json.dumps(dslist)
            yield payload

    def dsGetDataSourceList(self):
        self.sentinel = threading.Event()
        self.intervall = 300

        # Get all devices from ESM
        self.device_id = []
        payload = {'types' : ['RECEIVER'] }
        response = self.session.call_API('devGetDeviceList?filterByRights=false', payload)
        for erc in response:
            self.device_id.append(erc['id'])

        while not self.sentinel.is_set():
            for erc in self.device_id:
                dslist = []
                payload = {'receiverId' : erc}
                retVal = self.session.call_API('dsGetDataSourceList', payload)     

                if (self.get_details):
                    for ds in retVal:
                        payload = {'datasourceId' : str(ds['id'])}
                        parent = self.session.call_API('dsGetDataSourceDetail', payload)
                        parent['id'] = str(ds['id'])
                        dslist.append (parent)
                else:
                    dslist = retVal

                # Create and send message
                payload = json.dumps(dslist)
                yield payload
            self.sentinel.wait(self.interval)
