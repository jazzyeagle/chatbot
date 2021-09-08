import asyncio
import logging
import sys

from twitchio.ext import commands
import plugin


class PluginCommand(commands.Command):
    def __init__(self, name, func, script):
        super().__init__(name=name, func=func)
        self.msg = script


class Plugin(commands.Bot, plugin.Plugin):
    def __init__(self, bot, config):
        self.bot = bot
        self.db = bot.db

        file_handler = logging.FileHandler(filename='twitch.log')
        file_handler.setLevel(logging.DEBUG)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        handlers = [file_handler, stream_handler]
        logging.basicConfig(encoding='utf-8', level=logging.DEBUG, handlers=handlers)
        print('\t\tInitializing TwitchBot...')
        self.loop = asyncio.get_event_loop()

        super().__init__(
            token            = config['oauth-token'],
            prefix           = '!',
            client_secret    = config['client-id'],
            initial_channels = config['channels'],
        )
        self.load_commands()


    def __str__(self):
        return 'Twitch Bot plugin'


    @commands.command()
    async def yo(self, ctx):
        await ctx.send(f'Yo yourself, {ctx.message.author}')


    async def listener(self, ctx: commands.Context):
        words = ctx.message.content.split(' ')
        if len(words) > 1:
            to_user = words[1]
        else:
            to_user = None
        message = plugin.Message(
                                  platform = 'Twitch',
                                  author=ctx.author.name,
                                  channel=ctx.channel.name,
                                  command=ctx.command,
                                  text=ctx.message.content,
                                  to_user=to_user
                                )
        response = await self.bot.parser.process(self, message, script)
        await ctx.send(response)


    def load_commands(self):
        print('\t\tCreating Twitch event listeners...')
        bot_commands = self.bot.db.getCommands()
        for bot_command in bot_commands:
            print(f'Creating listener for {bot_command.name} command...')
            command_func = self.listener
            command = PluginCommand(bot_command.name, command_func, bot_command.script)
            print(f'{command._name}: {command._callback}')
            self.add_command(command)


    async def event_ready(self):
        print(f'ChatBot online and logged into Twitch as {self.nick}.')
