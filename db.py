from sqlalchemy import create_engine, select, text
from sqlalchemy import Table, Column, DateTime, Integer, String
from sqlalchemy.orm import Session, Query, declarative_base, relationship
from sqlalchemy.pool import QueuePool

from datetime import datetime
import logging
from random import randint

from result import Result, ResultType

BaseClass = declarative_base()


class Commands(BaseClass):
    __tablename__ = 'Commands'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    script = Column(String, nullable=False)
    frequency = Column(Integer, nullable=False, default=0)
    user_level = Column(String)


class ConnectionSettings(BaseClass):
    __tablename__ = 'ConnectionSettings'
    id = Column(Integer, primary_key=True)
    platform = Column(String, nullable=False)
    field = Column(String, nullable=False)
    value = Column(String)


class Variables(BaseClass):
    __tablename__ = 'Variables'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    value = Column(String, nullable=False)
    on_date = Column(DateTime, default=datetime.now())
    added_by = Column(String)


class Quotes(BaseClass):
    __tablename__ = 'Quotes'
    id = Column(Integer, primary_key=True)
    quote = Column(String, nullable=False)
    on_date = Column(DateTime, nullable=False, default=datetime.now())
    said_by = Column(String, nullable=False)
    recorded_by = Column(String, nullable=False)


dbTableTypes = {
    'commands':  Commands,
    'settings':  ConnectionSettings,
    'variables': Variables,
    'quotes':    Quotes
}


class Database:
    def __init__(self, path_to_db='chatbot.db'):
        logging.debug("sqlite+pysqlite:///" + path_to_db)
        self.engine = create_engine("sqlite+pysqlite:///" + path_to_db, future=True, poolclass=QueuePool)

        BaseClass.metadata.create_all(self.engine)


    # Returns the connection settings for a particular plugin
    def getConnectionSettings(self, plugin):
        print(plugin)
        settings = {}
        settings['channels'] = []
        with Session(self.engine) as session:
            results = session.query(ConnectionSettings.field,
                                     ConnectionSettings.value).all()
            #.filter(ConnectionSettings.platform == plugin)
            print(results)
            for result in results:
                if result.field == 'channel':
                    settings['channels'].append(result.value)
                else:
                    settings[result.field] = result.value
            print(settings)
            return settings
        

    # Returns the list of commands and the corresponding scripts
    def getCommands(self):
        with Session(self.engine) as session:
            return session.execute(select(Commands.name, Commands.script))


    def getType(self, t):
        if t in dbTableTypes.keys():
            return Result(ResultType.Ok, dbTableTypes[t])
        return Result(ResultType.Error, f'Type {t} not a valid dbTableType')


    def exists(self, varType, varName):
        with Session(self.engine) as session:
            q = session.query(varType.id).filter(varType.name == varName.lower())
            #session.query(q.exists())
            (isFound, ), = session.query(q.exists().where(varType.name == varName.lower()))
            return Result(ResultType.Ok, f'{isFound}')


    # This function is used within get, but it is also called directly via tests
    def getAllResults(self, varType, varName):
        with Session(self.engine) as session:
            results = session.execute(select(Variables.value).where(Variables.name == varName)).all()
            if len(results) == 0:
                # Safety net, but this should never happen, as we check to see if it exists before
                #    executing this function.
                print('Safety net hit in error!!')
                return Result(ResultType.Error, f'{varType.__name__} error:  {varName} not found in db.')
            return Result(ResultType.Ok, results)


    def get(self, varType, varName):
        results = self.getAllResults(varType, varName)
        if results.isError():
            return results
        results = results.getResult()
        if len(results) == 1:
            randomResult = 0
        else:
            randomResult = randint(0, len(results)-1)

        result = results[randomResult][0]
        return Result(ResultType.Ok, result)


    def set(self, varType, varName, value):
        pass


    def delete(self, varType, varName):
        pass


if __name__ == '__main__':
    db = Database()
