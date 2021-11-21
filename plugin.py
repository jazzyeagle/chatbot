from datetime import datetime
from enum import Enum


class MessageType(Enum):
    Server  = 'Server'
    Channel = 'Channel'
    Private = 'Private'


class Message:
    def __init__(self,
                 message_type = MessageType.Channel, 
                 platform     = '',
                 author       = '',
                 channel      = '',
                 timestamp    = datetime.now(),
                 command      = '',
                 text         = '',
                 to_user      = None
                ):
        self.message_type = message_type
        self.platform = platform
        self.author = author
        self.channel = channel
        self.timestamp = timestamp
        self.command = command
        self.text = text
        self.to_user = to_user


class Inbox:
    def __init__(self, bot):
        raise NotImplementedError
    
    def read(self):
        raise NotImplementedError

    def write(self, message):
        raise NotImplementedError


class Plugin:
    prefix = '!'
    inbox  = None

    def __init__(self, bot, config):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def say(self, response):
        raise NotImplementedError
