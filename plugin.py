from datetime import datetime #only used for testing.  Will remove later


class Message:
    def __init__(self, platform='', author='', channel='', timestamp=datetime.now(), command='', text='', to_user=None):
        self.platform = platform
        self.author = author
        self.channel = channel
        self.timestamp = timestamp
        self.command = command
        self.text = text
        self.to_user = to_user


class Plugin:
    prefix = '!'

    def __init__(self, bot, config):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def say(self, response):
        raise NotImplementedError
