import asyncio
import logging
import socket

import plugin
from plugin import Message, MessageType

twitch_irc_url  = 'irc.chat.twitch.tv'
twitch_irc_port = '6697'

twitch_ws_url   = 'wss://irc-ws.chat.twitch.tv'
twitch_ws_port  = '443'


class Plugin(plugin.Plugin):
    def __init__(self, bot, settings):
        logging.debug('twitch.Plugin.__init__')
        self.inbox = asyncio.Queue()
        self.irc = TwitchIRCBot(bot, settings)
        
    async def run(self):
        logging.debug('twitch.Plugin.run')
        await self.irc.run()
    
    
class TwitchIRCBot:
    def __init__(self, bot, settings):
        logging.debug('TwitchIRCBot.__init__')
        self.inbox        = None
        self.outbox       = None
        self.bot          = bot
        self.settings     = settings
        self.socket       = socket.socket()
        self.workers      = []
        self.keep_looping = True
        
        
    async def run(self):
        logging.debug('TwitchIRCBot.run')
        await self.start()
        await self.loop()
        await self.stop()
        
        
    async def start(self):
        logging.debug('TwitchIRCBot.start')
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
        logging.debug('TwitchIRCBot.start')
        self.socket.close()
        

    async def loop(self):
        logging.debug('TwitchIRCBot.loop')
        self.inbox   = asyncio.Queue(maxsize=1)
        self.outbox  = asyncio.Queue(maxsize=1)
        read_task    = asyncio.create_task(self.read(),    name='read')
        process_task = asyncio.create_task(self.process(), name='process')
        #write_task   = asyncio.create_task(self.write(),   name='write')
        await asyncio.gather(read_task, process_task, write_task)


    # This looks for anything that comes in from the server and puts it into the inbox
    async def read(self):
        logging.debug('TwitchIRCBot.read started')
        while self.keep_looping:
            try:
                logging.debug('TwitchIRCBot.read - waiting for message')
                message = await self.input.readuntil(b'\r\n')
                if message:
                    logging.debug('TwitchIRCBot.read - Message received from Twitch.  Adding to Inbox')
                    await self.inbox.put(message)
                    #new_message = asyncio.create_task(self.process(), name='process')
                else:
                    self.keep_looking = False
            except asyncio.exceptions.CancelledError:
                pass
            message = None
        logging.debug('TwitchIRCBot.read shutting down')


    # This looks for messages in the inbox (from any source) and processes them
    #    then calls for them to be written.
    async def process(self):
        logging.debug('TwitchIRCBot.process started.')
        while self.keep_looping:
            try:
                unprocessed_message = await self.inbox.get()
                logging.debug('TwitchIRCBot.process - Message received from Inbox')
                if unprocessed_message:
                    processed_message = await self.create_message(unprocessed_message)
                    logging.debug('TwitchIRCBot.process - Message processed; time to write!')
                    await self.write(processed_message)
                    #await self.outbox.put(processed_message)
                self.inbox.task_done()
            except asyncio.exceptions.CancelledError:
                pass
            unprocessed_message = None
        logging.debug('TwitchIRCBot.process shutting down')


    # This looks for messages in the outbox and prints/sends them as appropriate.
    async def write(self, message):
        if message is not None:
            logging.debug(f'TwitchIRCBot.write "{message.text}"')
            if 'PASS' in message.text:
                print('< PASS ********')
            else:
                print(f'> {message.text}')

            if message.text == 'PING :tmi.twitch.tv':
                print('< PONG :tmi.twitch.tv')
                await self.send_server('PONG :tmi.twitch.tv')
            else:
                if message.response:
                    print(f'< {str(message.response)}')
                if message.send_to_server:
                    if message.message_type == MessageType.Server:
                        await self.send_server(message.response)
                    elif message.message_type == MessageType.Channel:
                        await self.send_to_channel(message)
                    elif message.message_type == MessageType.Private:
                        await self.send_to_user(message)
                    else:
                        print(f'Invalid MessageType: {message.message_type}')
        #self.outbox.task_done()
            

    async def send_server(self, message):
        logging.debug('TwitchIRCBot.send_server')
        self.output.write(f'{message}\r\n'.encode())
        
    
    async def send_to_user(self, message):
        logging.debug('TwitchIRCBot.send_to_user')
        await self.send_server(f'PRIVMSG {message.author} :{message.response}')
        
    
    async def send_to_channel(self, message):
        logging.debug('TwitchIRCBot.send_to_channel')
        await self.send_server(f'PRIVMSG #{message.channel} :{message.response}')
        

    async def create_message(self, unprocessed_message):
        logging.debug('TwitchIRCBot.create_message')
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
        logging.debug('TwitchIRCBot.process_PRIVMSG')
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
        
        if text[0] == '!':
            command_end  = text.find(' ')
            command = text[1:].strip() if command_end == -1 else text[1:command_end].strip()
            script       = self.bot.db.getScript(command).getResultOrError()
        else:
            script       = None
        message = Message (
                            message_type = message_type,
                            platform     = 'Twitch',
                            author       = author,
                            channel      = channel,
                            text         = text,
                          )
        processed_message = await self.bot.parser.process(self.bot, message, script)
        return processed_message
