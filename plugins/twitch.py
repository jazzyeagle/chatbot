import asyncio
import socket

import plugin

twitch_irc_url  = 'irc.chat.twitch.tv'
twitch_irc_port = '6697'

twitch_ws_url   = 'wss://irc-ws.chat.twitch.tv'
twitch_ws_port  = '443'


class Plugin(plugin.Plugin):
    def __init__(self, bot, settings):
        self.inbox = asyncio.Queue()
        self.irc = TwitchIRCBot(bot, settings)
        
    async def run(self):
        await self.irc.run()
    
    
class TwitchIRCBot:
    def __init__(self, bot, settings):
        self.inbox        = None
        self.outbox       = None
        self.bot          = bot
        self.settings     = settings
        self.socket       = socket.socket()
        self.workers      = []
        self.keep_looping = True
        
        
    async def run(self):
        await self.start()
        await self.loop()
        await self.stop()
        
        
    async def start(self):
        print('Connecting to Twitch...')
        
        self.input, self.output = await asyncio.open_connection(twitch_irc_url,
                                                                twitch_irc_port,
                                                                ssl=True)
        username    = self.settings['botnick']
        oauth_token = self.settings['oauth-token']
        channels    = self.settings['channels'].split(',')
        self.send_server(f'PASS {oauth_token}')
        self.send_server(f'NICK {username}')
        print('Connected.')
        for channel in channels:
            print(f'  Joining #{channel}')
            self.send_server(f'JOIN #{channel}')
            self.send_to_channel(channel, 'The eagle has landed.')
        
        
    async def stop(self):
        self.socket.close()
        

    async def loop(self):
        self.inbox   = asyncio.Queue(maxsize=1)
        self.outbox  = asyncio.Queue(maxsize=1)
        read_task    = asyncio.create_task(self.read(),    name='read')
        process_task = asyncio.create_task(self.process(), name='process')
        write_task   = asyncio.create_task(self.write(),   name='write')
        await asyncio.gather(read_task, process_task, write_task)


    # This looks for anything that comes in from the server and puts it into the inbox
    async def read(self):
        while self.keep_looping:
            try:
                message = await self.input.readuntil(b'\r\n')
                if message:
                    await self.inbox.put(message)
                else:
                    self.keep_looking = False
            except asyncio.exceptions.CancelledError:
                pass
            message = None


    # This looks for messages in the inbox (from any source) and processes them
    #    then puts them in the outbox for write.
    async def process(self):
        while self.keep_looping:
            try:
                # Get bytestring info
                unprocessed_message = await self.inbox.get()
                # decode from bytestring to string
                unprocessed_message = unprocessed_message.decode()
                # remove '\r\n'
                unprocessed_message = unprocessed_message[:len(unprocessed_message)-2]
                if unprocessed_message:
                    await self.outbox.put(unprocessed_message)   
                self.inbox.task_done()
            except asyncio.exceptions.CancelledError:
                pass
            unprocessed_message = None


    # This looks for messages in the outbox and prints/sends them as appropriate.
    async def write(self):
        while self.keep_looping:
            message = await self.outbox.get()
            if message:
                print(f'> {str(message)}')
            if message == 'PING :tmi.twitch.tv':
                print('PONG :tmi.twitch.tv')
                self.send_server('PONG :tmi.twitch.tv')
        self.outbox.task_done()
        

    def send_server(self, message):
        if 'PASS' in message:
            print('< PASS ********')
        else:
            print(f'< {message}')
        self.output.write(f'{message}\r\n'.encode())
        
    
    def send_to_user(self, user, message):
        self.send_server(f'PRIVMSG {user} {message}')
        
    
    def send_to_channel(self, channel, message):
        self.send_server(f'PRIVMSG #{channel} {message}')

    def create_message(self, message):
        pass
