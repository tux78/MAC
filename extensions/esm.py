import base64
import json
import threading

try:
    import requests
    requests.packages.urllib3.disable_warnings()
except ImportError:
    print('Failure during import')
    requests = None

class esm():

    def __init__(self, host, username, password):

        self.esm_user = username
        self.esm_password = password
        self.esm_ip = host

        self.hide_disabled = True
        self.get_details = True

        super().__init__()

        if requests is None:
            raise ValueError("Could not import 'requests'. Please install it.")

        # Login parameters
        self.enc_user = base64.b64encode (self.esm_user.encode('utf-8')).decode()
        self.enc_password = base64.b64encode (self.esm_password.encode('utf-8')).decode()
        self.url = 'https://' + self.esm_ip + '/rs/esm/v2/'
        self.auth_header = {'Content-Type': 'application/json'}

        # Test Login
        if not(self._heartbeat()):
            raise ValueError('Cannot login.')

        # Get all devices from ESM
        self.device_id = []
        payload = {'types' : ['RECEIVER'] }
        response = self._call_API('devGetDeviceList?filterByRights=false', payload)
        for erc in response.json():
            self.device_id.append(erc['id'])

    def dsGetDataSourceListOnce(self, **kwargs):

        if not(self._heartbeat()):
            raise ValueError('Cannot login.')

        for erc in self.device_id:
            dslist = []
            payload = {'receiverId' : erc}
            retVal = self._call_API('dsGetDataSourceList', payload)

            if (self.get_details):
                for ds in retVal.json():
                    payload = {'datasourceId' : str(ds['id'])}
                    parent = self._call_API('dsGetDataSourceDetail', payload).json()
                    parent['id'] = str(ds['id'])
                    dslist.append (parent)
            else:
                dslist = retVal.json()

            # Create and send message
            payload = json.dumps(dslist)
            yield payload

    def dsGetDataSourceList(self, sentinel : threading.Event = threading.Event(), interval : int = 3600):

        while not sentinel.is_set():
            if not(self._heartbeat()):
                raise ValueError('Cannot login.')

            for erc in self.device_id:
                dslist = []
                payload = {'receiverId' : erc}
                retVal = self._call_API('dsGetDataSourceList', payload)     

                if (self.get_details):
                    for ds in retVal.json():
                        payload = {'datasourceId' : str(ds['id'])}
                        parent = self._call_API('dsGetDataSourceDetail', payload).json()
                        parent['id'] = str(ds['id'])
                        dslist.append (parent)
                else:
                    dslist = retVal.json()

                # Create and send message
                payload = json.dumps(dslist)
                yield payload
            sentinel.wait(interval)

    def _login (self):
        self.auth_header = {'Content-Type': 'application/json'}
        data = {
            'username' : self.enc_user,
            'password' : self.enc_password,
            'locale' : 'en_US',
            'os' : 'Win32'
        }

        try:
            response = requests.post(
                self.url + 'login',
                data = json.dumps (data),
                headers = self.auth_header,
                verify = False
            )
        except requests.exceptions.ConnectionError:
            raise ValueError('Error connecting to ESM.')

        if response.status_code in [400, 401]:
            raise ValueError('Invalid username or password.')
            return False
        elif 402 <= response.status_code <= 600:
            raise ValueError('ESM login error: ' + response.text)
            return False

        # Store XSRF Token for subsequent use
        self.auth_header['Cookie'] = response.headers.get('Set-Cookie')
        self.auth_header['X-Xsrf-Token'] = response.headers.get('Xsrf-Token')
        self.auth_header['SID'] = response.headers.get('Location')

        print('ESM: Login successful.')
        return True

    def _heartbeat (self):

        response = requests.post(
            self.url + 'miscKeepAlive',
            headers = self.auth_header,
            verify = False
        )
        if response.status_code in [200, 204]:
            return True
        else:
            print('ESM: Heartbeat failed with ' + str(response.status_code) + '. Trying login.')
            return self._login()

    def _call_API (self, method, payload):

        response = requests.post (
            self.url + method,
            data = json.dumps (payload),
            headers = self.auth_header,
            verify = False
        )
        return response
