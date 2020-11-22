import base64
import json
import configparser
import urllib

import requests

class ESMConfig(configparser.ConfigParser):

    def __init__(self, confDir, *arg, **kwarg):
        super().__init__(*arg, **kwarg)

        files = self.read(confDir + 'esmclient.config')
        if len(files) == 0:
            raise RuntimeError

    def write(self):
        with open(self._path, "w") as file:
            super().write(file)

    @property
    def user(self):
        return self.get("esm", "user")

    @property
    def host(self):
        return self.get("esm", "host")

    @property
    def passwd(self):
        return self.get("esm", "passwd")

    @property
    def timeout(self):
        return self.getint("general", "timeout")

    @property
    def ssl_verify(self):
        return self.getboolean("general", "ssl_verify")


class ESMCore:

    def __init__(self, confDir):

        self.config = ESMConfig(confDir)
        self.session = requests.Session()
        self.url = 'https://' + self.config.host + '/rs/esm/v2/'

        try:
            requests.packages.urllib3.disable_warnings(
                requests.packages.urllib3.exceptions.InsecureRequestWarning
            )
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except:
            pass

        # Test Login
        if not(self.loggedIn):
            raise RuntimeError('ESMCore: Cannot login.')

    def _login (self):

        # Login parameters
        enc_user = base64.b64encode (self.config.user.encode('utf-8')).decode()
        enc_password = self.config.passwd
        self.session.headers = {'Content-Type': 'application/json'}

        payload = {
            'username' : enc_user,
            'password' : self.config.passwd,
            'locale' : 'en_US',
            'os' : 'Win32'
        }

        response = self.call_API('login', payload, raw=True)
        if not response:
            return false

        # Store XSRF Token for subsequent use
        self.session.headers['Cookie'] = response.headers.get('Set-Cookie')
        self.session.headers['X-Xsrf-Token'] = response.headers.get('Xsrf-Token')
        self.session.headers['SID'] = response.headers.get('Location')

        print('ESM: Login successful.')
        return True

    @property
    def loggedIn (self):

        response = requests.post(
            self.url + 'miscKeepAlive',
            headers = self.session.headers,
            verify = False
        )
        if response.status_code in [200, 204]:
            return True
        else:
            return self._login()

    def call_API (self, method, payload, http='POST', raw=False, retry=1):

        try:
            response = self.session.request(
                http,
                urllib.parse.urljoin(self.url, method),
                data=json.dumps(payload),
                verify=self.config.ssl_verify,
                timeout=self.config.timeout,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:

            if retry > 0:
                time.sleep(1)
                return self.call_api(
                    method, payload, http, retry=retry - 1
                )
            else:
                raise RuntimeError('ESMCore: multiple calls to API failed.')

        except requests.exceptions.TooManyRedirects:
            raise

        if raw:
            return response
        return json.loads(response.content)
