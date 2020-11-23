from pykafka import KafkaClient, exceptions

import queue
import json

class messageBrokerFactory_kafka:

    def __init__(self, appID, topicOut=[], debug=False):

        self.appID = appID
        self.debug = debug

        if self.debug:
            print(self.appID + ': ' + 'class created')
        try:
            self.client = KafkaClient(hosts="kafka:9092")
            self.producers = []
            self.consumer = ''
            for topic in topicOut:
                self.producers.append(self._create_topicOut(topic))
        except Exception as err:
            raise appError(self.appID, 'Message sub-system not available (' + str(err) + ')')

    def consume(self, sentinel, **kwargs):
        if not self.consumer:
            self._create_topicIn()
        while not sentinel.is_set():
            message = self.consumer.consume(block=False)
            if message:
                yield message.value.decode()

    def produce(self, payload):
        if self.debug:
            print(self.appID + ': ' + 'Producing message')
        for producer in self.producers:
            producer.produce(payload.encode())

    def _create_topicIn(self):
        if self.debug:
            print(self.appID + ': ' + 'Creating inbound topic: ' + self.appID)
        topic_read = self.client.topics[self.appID]
        self.consumer = topic_read.get_balanced_consumer(
            consumer_group = self.appID.encode(),
            auto_commit_enable = True,
            zookeeper_connect = "zookeeper:2181")

    def _create_topicOut(self, topic):
        if self.debug:
            print(self.appID + ': ' + 'Creating outbound topic: ' + topic)
        topic_write = self.client.topics[topic]
        return topic_write.get_producer()

class messageBrokerFactory:

    brokerList : { str : queue.Queue } = {}

    def __init__(self, appID, topicOut=[], debug=False):

        self.topicIn = appID.replace(' ', '_')
        self.debug = debug
        self.topicOut = [topic.replace(' ', '_') for topic in topicOut]

        messageBrokerFactory.brokerList[self.topicIn] = queue.Queue()
        self.queue = ''

        if self.debug:
            print(self.topicIn + ': ' + 'queue created')

    def consume(self, sentinel, **kwargs):
        if not self.queue:
            self.queue = messageBrokerFactory.brokerList[self.topicIn]
        while not sentinel.is_set():
            if not self.queue.empty():
                if self.debug:
                    print(self.topicIn + ': ' + 'Consuming message')
                message = self.queue.get()
                yield message

    def produce(self, payload):
        if self.debug:
            print(self.topicIn + ': ' + 'Producing message')
        for topic in self.topicOut:
            messageBrokerFactory.brokerList[topic].put(payload)

class appError(Exception):

    def __init__(self, appID, message):
        self.appID = appID
        self.message = message

    def logLine(self):
        return self.appID + ': ' + self.message
