from result import Result, ResultType

class Parser:
    def __init__(self, db):
        self.db = db
        self.builtinCommands = {
            '1'              : self.getUserVarCommand1,
            'channel'        : self.getChannelCommand,
            'command'        : self.builtInCommand,
            'if'             : self.ifCommand,
            'join'           : self.joinCommand,
            'part'           : self.partCommand,
            'quote'          : self.quoteCommand,
            'sender'         : self.senderCommand,
            'user'           : self.userCommand,
            'var'            : self.varCommand
        }

        self.subCommands = {
            'get':     self.getCommand,
            'set':     self.setCommand,
            'add':     self.setCommand,
            'edit':    self.setCommand,
            'delete':  self.deleteCommand,
            'unset':   self.deleteCommand,
            'remove':  self.deleteCommand,
            'exists':  self.existsCommand
            }

    async def process(self, bot, message, script=None):
        self.bot = bot
        self.message = message
        
        if script is None:
            return self.message
        
        processed_script = script
        subcommand = self.findSubcommand(processed_script)
        while (not subcommand.isError()) and (subcommand.getResult() is not None):
            # Ssend to the script to the appropriate command function to resolve
            #   Remove the surrounding brackets first
            start, end = subcommand.getResult()
            result = await self.processCommand(processed_script[start+1:end])
            if result.isError():
                return f'Error: {result.getError()}'
            if start == 0:
                processed_script = result.getResult() + processed_script[end+1:]
            else:
                processed_script = processed_script[:start] + result.getResult() + processed_script[end+1:]
            subcommand = self.findSubcommand(processed_script)

        print(f'subcommand: {str(subcommand)}')
        if subcommand.isOk():
            print(f'parser.process successful: {processed_script}')
            message.response = processed_script
            message.send_to_server = True
        else:
            message.response = f'Error: {subcommand.getError()}'
        return message


    # Finds first subcommand in script and returns start and end.  This does not process the subcommand at all.
    #   If there are no subcommands, return None
    def findSubcommand(self, script):
        # If there are no subcommands, return Okay, but none.
        if script.find('{') == -1:
            return Result(ResultType.Ok, None)

        start = script.find('{')
        nextstart = start
        nextend = script.find('}', nextstart + 1)
        end = nextend
        depth = 0

        #Cycle through until we have found the full depth.  Return breaks the loop.
        while True:
            # nextend should never = -1 until depth = 1 again, which point we return, so it should never = 1
            #    at the point this if statement is evaluated
            if nextend == -1:
                return Result(ResultType.Error, "# opening brackets does not match # closing brackets")
            # if nextstart > nextend, we have completed a subcommnand.  Decrease depth by 1
            elif nextstart > nextend or nextstart == -1:
                end = nextend
                nextstart = script.find('{', nextend)
                nextend   = script.find('}', nextend+1)
                depth    -= 1
                # If we're back to depth == 1, we have found a full subcommand.
                if depth == 0:
                    return Result(ResultType.Ok, (start, end))
            # if nextstart < nextend, we have a subcommand within a subcommand.  Increase depth by 1
            elif nextstart < nextend:
                nextend   = script.find('}', nextstart)
                nextstart = script.find('{', nextstart+1)
                depth    += 1

            if depth > 10:
                return Result(ResultType.Error, "depth is wrong")

    
    async def processSubcommand(self, script):
        command = script
        while True:
            subcommand = self.findSubcommand(command)
            if subcommand.isError():
                return subcommand
            if subcommand.getResult() is None:
                return Result(ResultType.Ok, command)
            start, end = subcommand.getResult()
            result = await self.processCommand(command[start+1:end])
            if result.isError():
                return result
            command = command[:start] + result.getResult() + command[end+1:]
            command = command.strip()
            return Result(ResultType.Ok, command)


    async def processCommand(self, script):
        command = script.split()[0]
        if command not in self.builtinCommands.keys():
            return Result(ResultType.Error, f'{command} is not a valid command.')
        result = await self.builtinCommands[command](script)
        return result
    

    async def parseCommand(self, script):
        pass


    # up to first pipe = condition to process
    # between first & second pipe = command if condition is true
    # after second pipe = command if condition is false
    async def ifCommand(self, script):
        result = script
        variables = []

        variables = script.split('|')
        # Remove if statement from condition
        variables[0] = variables[0][3:]
        
        # clean up any leading/trailing whitespaces
        for variable in variables:
            variable = variable.strip()

        condition = await self.processSubcommand(variables[0])
        if condition.isError():
            return condition

        if condition.getResult() == 'True':
            command = variables[1]
        elif condition.getResult() == 'False':
            command = variables[2]
        else:
            return Result(ResultType.Error, f'condition {condition.getResult()} is neither True nor False')

        result = await self.processSubcommand(command)
        return result


    async def getUserVarCommand1(self, message):
        variables = message.originaltext.split()
        return variables[1]


    # This function is when a person uses the 'var' command
    async def varCommand(self, script):
        dbType = self.db.getType('variables')
        if dbType.isError():
            return dbType
        # Check to see if second word is a db subCommand, e.g. add, remove, exists, etc.
        #    If so, call the appropriate function
        if script.split()[1] in self.subCommands.keys():
            subcommand = script.split()[1]
            result = await self.subCommands.get(subcommand)(dbType.getResult(), script)

        # Otherwise, assume the second word is the varName that the user is attempting to get.
        else:
            result = await self.getCommand(dbType.getResult(), script)
        return result


    # This function is when a person uses the 'command' command
    async def builtInCommand(self, script):
        #return await self.getsetCommand(self.db.getType('commands'), script)
        dbType = self.db.getType('commands')
        if dbType.isError:
            return dbType
        return await self.getsetCommand(dbType.getResult(), script)


    # This function is when a person uses the 'quote' command
    async def quoteCommand(self, script):
        #return await self.getsetCommand(self.db.getType('quotes'), script)
        dbType = self.db.getType('quotes')
        if dbType.isError:
            return dbType
        return await self.getsetCommand(dbType.getResult(), script)



    async def getVarName(self, script):
        # Check to see if there are any subcommands.  if so, process them.
        command = script
        subcommands = self.findSubcommand(command)
        if subcommands.isError():
            return subcommands
        if subcommands.getResult() is not None:
            start, end = subcommands.getResult()
            result = await self.processSubcommand(command)
            if result.isError():
                return result
            command = result.getResult()
        
        command_parts = command.split()
        if len(command_parts) < 2:
            return Result(ResultType.Error, f'Missing variable name.')

        if len(command_parts) == 2:
            command = command_parts[1]
        elif len(command_parts) >= 3:
            command = command_parts[2]
        return Result(ResultType.Ok, command)


    async def getCommand(self, varType, script):
        varNameResult = await self.getVarName(script)
        if varNameResult.isError():
            return varName

        varName = varNameResult.getResult().lower()
        if self.db.exists(varType, varName):
            return self.db.get(varType, varName)
        return Result(ResultType.Error, f'{varType} {varName} not found!')
        

    async def setCommand(self, varType, script):
        varName = await self.getVarName(script)
        if varName.isError():
            return varName
        self.db.set(varType, varName, ' '.join(parts[3:]))
        check = self.db.get(varType, varName)
        if check.isOk():
            if check.getValue() == ' '.join(parts[3:]):
                return Result(ResultType.Ok, varType + ' ' + varName + ' succesfully set.')
        return Result(ResultType.Error, f'{varType} {varName} was not successfully set.')


    async def deleteCommand(self, varType, script):
        pass


    async def existsCommand(self, varType, script):
        varName = await self.getVarName(script)
        if varName.isError():
            return varName
        return self.db.exists(varType, varName.getResult())


    async def getsetCommand(self, varType, script):
        parts = script.split()

        # For the variable name, we need to process any { }
        #varName = await self.parseCommand(script, ' '.join(parts[2]))
        #varName = varName.lower()

        if varType is None:
            return Result(ResultType.Error, f'Variable Type {varType} is not recognized.') 
        
        # Subcommand = get, set, add, edit, delete, etc.
        # Set varName to parts[2], since most of the following use parts[2].  If not there, then
        #     try parts[1] as varName
        if len(parts) == 2:
            subcommand = None
            varName = parts[1]
        else:
            subcommand = parts[1]
            varName = parts[2]

        # Check to see if user made a command w/o a subcommand, e.g. {var greeting}.
        #    If so, assume the user is attempting to get the variable/command/etc.
        if subcommand is None:
            if self.db.exists(varType, varName):
                result = self.db.get(varType, varName)
                return result
            return Result(ResultType.Error, f'Cannot retrieve {varName} from database')

        if subcommand == 'get':
            if self.db.exists(varType, varName):
                return self.db.get(varType, varName)
            return Result(ResultType.Error, f'{varType} {varName} not found!')

        # For setting a variable, we don't want to process any { }.  We want to store those
        if subcommand == 'set' or parts[1] == 'add' or parts[1] == 'edit':
            self.db.set(varType, varName, ' '.join(parts[3:]))
            check = self.db.get(varType, varName)
            if check.isOk():
                if check.getValue() == ' '.join(parts[3:]):
                    return Result(ResultType.Ok, varType + ' ' + varName + ' succesfully set.')
            return Result(ResultType.Error, f'{varType} {varName} was not successfully set.')

        if subcommand == 'delete' or parts[1] == 'unset' or parts[1] == 'remove':
            self.db.delete(varType, varName)

        if subcommand == 'exists':
            return self.db.exists(varType, varName)



    #def getCommand(self, commands, varName):
    #    for row in commands:
    #        if row.name == varName:
    #            return Result(ResultType.Ok, row.script)
    #    return Result(ResultType.Error, f'Command {varName} not found.')


    # script sent only to match the same parameters as the others in the dictionary (see __init__)
    #   It is not actually used.
    async def userCommand(self, script):
        if self.message.to_user is not None:
            user = self.message.to_user
            if user[0] == '@':
                response = user[1:]
            else:
                response = user
        else:
            response = self.message.author
        return Result(ResultType.Ok, response)


    async def senderCommand(self, message):
        return message.author
        


    async def getChannelCommand(self, script):
        user = await self.userCommand(script)
        if user.isError():
            return user
        return Result(ResultType.Ok, 'https://twitch.tv/' + user.getResult())


    async def joinCommand(self, message):
        parts = message.text.split()
        if(len(parts) > 1):
            await self.bot.join_channels(parts[1:])
            channels = ' '.join(parts[1:])
            return Result(ResultType.Ok, f'Successfully joined channels {channels}')
        return Result(ResultType.Error, 'Please include channel name(s) in !join command')


    async def partCommand(self, message):
        parts = message.text.split()
        if(len(parts) > 1):
            await self.bot.part_channels(parts[1:])
            channels = ' '.join(parts[1:])
            return Result(ResultType.Ok, f'Successfully parted channels {channels}')
        return Result(ResultType.Error, 'Please include channel name(s) in !part command')
