#!/usr/bin/env python

"""
tooby.py: This is the main engine of the bot, which communicates with the various plugins.
"""

import importlib
import logging
import pkgutil

from db     import Database
from parser import Parser


"""
Main Bot Class
"""
class ChatBot:
    def __init__(self):
        print('Initializing core modules...')
        self.db = Database()
        self.parser = Parser(self.db)

        print('Initializing plugin modules...')
        self.plugins = {}
        modules = pkgutil.iter_modules(path=['plugins'])
        for module in modules:
            print(f'\tLoading Module {module.name}')
            settings = self.db.getConnectionSettings(module.name)
            self.plugins[module.name] = importlib.import_module('plugins.'+module.name).Plugin(self, settings)
            print(f'\tModule {module.name} loaded')

        print(f'\n# of plugins loaded: {len(self.plugins)}')

    """
    Runs the bot
    """
    def run(self):
        print('Starting application...')
        for plugin in self.plugins.values():
            plugin.run()
        print('Chatbot shutting down.')


    def join_channels(self, channels):
        pass

    def part_channels(self, channels):
        pass


if __name__ == "__main__":
    chatty = ChatBot()
    chatty.run()
