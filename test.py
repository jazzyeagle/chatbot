#!/usr/bin/env python

from datetime import datetime
import unittest

from parser import Parser
from plugin import Message
from db import Database, Variables
from chatbot import ChatBot

class TestChatBot(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = Database()
        self.parser = Parser(self.db)


    def containsRandomString(self, random_strings, result_string):
        for random_string in random_strings:
            # This cannot process subcommands, so compare up to the first subcommand, assuming there is one.
            subcommand = random_string.value.find('{')
            if subcommand > -1:
                test_string = random_string.value[:subcommand]
            else:
                test_string = random_string.value
            print(f'test_string: {test_string}')
            if test_string in result_string:
                return True
        return False


    async def test_hello_no_user(self):
        result = await self.hello()


    async def test_hello_with_user(self):
        result = await self.hello('@stylerun09')


    async def hello(self, user=None):
        get_greetings = self.db.getAllResults(Variables, 'greeting')
        if get_greetings.isError():
            return
        get_howareyou = self.db.getAllResults(Variables, 'howareyou')
        if get_howareyou.isError():
            return
        commands = self.db.getCommands()
        for command in commands:
            if command.name == 'hello':
                hello_script = command.script
                break
        message = Message(platform='test',
                          author='jazzyeagle',
                          channel='#jazzyeagle',
                          timestamp=datetime.now(),
                          command='hello',
                          text=hello_script,
                          to_user=user)
        result = await self.parser.process(self, message, hello_script)
        # Assert that any of the greetings strings are in the result
        self.assertTrue(self.containsRandomString(get_greetings.getResult(), result))
        # Assert that username is in the result but not the @ symbol
        if user is None:
            self.assertIn('jazzyeagle', result)
        elif user[0] == '@':
            self.assertIn(user[1:], result)
        else:
            self.assertIn(user, result)
        self.assertNotIn('@', result)
        # Assert that any of the howareyou strings are in the result
        self.assertTrue(self.containsRandomString(get_howareyou.getResult(), result))


    async def test_so(self):
        get_shoutouts = self.db.getAllResults(Variables, 'joshtaerkmusic')
        if get_shoutouts.isError():
            return
        commands = self.db.getCommands()
        for command in commands:
            if command.name == 'so':
                so_script = command.script
                break
        message = Message(platform='test',
                          author='jazzyeagle',
                          channel='#jazzyeagle',
                          timestamp=datetime.now(),
                          command='so joshtaerkmusic',
                          text=so_script,
                          to_user='joshtaerkmusic')

        result = await self.parser.process(self, message, so_script)
        # Assert that any of the shoutout strings are in the result
        self.assertTrue(self.containsRandomString(get_shoutouts.getResult(), result))


if __name__ == '__main__':
    unittest.main()
