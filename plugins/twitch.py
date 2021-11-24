import asyncio
import socket

import plugin
from plugin import Message, MessageType

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
        await self.send_server(f'PASS {oauth_token}')
        await self.send_server(f'NICK {username}')
        print('Connected.')
        for channel in channels:
            print(f'  Joining #{channel}')
            await self.send_server(f'JOIN #{channel}')
            await self.send_to_channel(Message( channel        = channel,
                                                response       = 'The eagle has landed.',
                                                send_to_server = True
                                              )
                                      )
        
        
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
                unprocessed_message = await self.inbox.get()
                if unprocessed_message:
                    processed_message = await self.create_message(unprocessed_message)
                    await self.outbox.put(processed_message)   
                self.inbox.task_done()
            except asyncio.exceptions.CancelledError:
                pass
            unprocessed_message = None


    # This looks for messages in the outbox and prints/sends them as appropriate.
    async def write(self):
        while self.keep_looping:
            message = await self.outbox.get()
            if 'PASS' in message.text:
                print('< PASS ********')
            else:
                print(f'> {message.text}')
            if message is not None:
                if message == 'PING :tmi.twitch.tv':
                    print('PONG :tmi.twitch.tv')
                    await self.send_server('PONG :tmi.twitch.tv')
                else:
                    if message.response:
                        print(f'< {str(message.response)}')
                    if message.send_to_server:
                        if message.message_type == MessageType.Server:
                            print('Sending directly to server')
                            await self.send_server(message.response)
                        elif message.message_type == MessageType.Channel:
                            print(f'Sending to channel #{message.channel}')
                            await self.send_to_channel(message)
                        elif message.message_type == MessageType.Private:
                            print(f'Sending to user {message.author}')
                            await self.send_to_user(message)
                        else:
                            print(f'Invalid MessageType: {message.message_type}')
            self.outbox.task_done()
            

    async def send_server(self, message):
        print(f'send_server: {message}')
        self.output.write(f'{message}\r\n'.encode())
        
    
    async def send_to_user(self, message):
        print('send_to_user')
        await self.send_server(f'PRIVMSG {message.author} :{message.response}')
        
    
    async def send_to_channel(self, message):
        print('send_to_channel')
        await self.send_server(f'PRIVMSG #{message.channel} :{message.response}')
        

    async def create_message(self, unprocessed_message):
        # decode from bytestring to string
        unprocessed_message = unprocessed_message.decode()
        # remove '\r\n'
        unprocessed_message = unprocessed_message[:len(unprocessed_message)-2]
        

        # For now, only process messages sent to a channel or via whisper by looking for PRIVMSG
        if 'PRIVMSG' in unprocessed_message:
            processed_message = await self.process_PRIVMSG(unprocessed_message)
        else:
            processed_message = Message(
                                         message_type = MessageType.Server,
                                         text         = unprocessed_message,
                                       )
        return processed_message
    
        
    async def process_PRIVMSG(self, unprocessed_message):
        if '#' in unprocessed_message:
            message_type  = MessageType.Channel
            channel_start = unprocessed_message.find('#') + 1
            channel_end   = unprocessed_message.find(' ', channel_start)
            channel       = unprocessed_message[channel_start:channel_end].strip()
        else:
            message_type = MessageType.Private
            channel      = ''
        author_start     = 1
        author_end       = unprocessed_message.find('!', author_start)
        author           = unprocessed_message[author_start:author_end].strip()
        
        text_start       = unprocessed_message.find(':', channel_end) + 1
        text             = unprocessed_message[text_start:]
        
        print(f'text: {text}')
        if text[0] == '!':
            command_end  = text.find(' ')
            if command_end == -1:
                command = text[1:].strip()
                to_user = None
            else:
                command      = text[1:command_end].strip()
                user_end     = text.find(' ', command_end + 1)
                if user_end == -1:
                    to_user  = text[command_end+1:].strip()
                else:
                    to_user  = text[command_end+1:user_end].strip()
            print(f'command: {command}')
            script       = self.bot.db.getScript(command).getResultOrError()
            print(script)
        else:
            command      = ''
            script       = None
        message = Message(
                                  message_type = message_type,
                                  platform     = 'Twitch',
                                  author       = author,
                                  channel      = channel,
                                  command      = command,
                                  text         = text,
                                )
        processed_message = await self.bot.parser.process(self.bot, message, script)
        return processed_message
