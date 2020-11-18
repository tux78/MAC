import threading

class test:

    def __init__(self, username, ip):
        self.username = username
        self.ip = ip
        # initialize any required internal variables
        # such as credentials, IP addresses etc

    def getDataOnce(self, **kwargs):
        yield 'some data'

    def getDataAsStream(self, sentinel : threading.Event = threading.Event(), interval : int = 3600):
        while not sentinel.is_set():
            # enter code here
            # for continuous processing, have interval = 0
            # the interval can be configured from within the App configuration
            yield 'some data'
            sentinel.wait(interval)

    def sendData(self, payload):
        # send payload to desired destination
        # file output, consumer
        pass
