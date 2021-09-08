# result.py:  Used instead of raises to identify if any errors occurred.
#             A result is either Okay [result of function] or Error [error string]

from enum import Enum


class ResultType(Enum):
    Ok = 1
    Error = 2


class Result:
    # result will either be result of function or error string, depending on resultType
    def __init__(self, resultType, result):
        self.resultType = resultType
        self.result = result

    def __str__(self):
        if self.isOk():
            return f'Ok: {self.getResult()}'
        return f'Error: {self.getError()}'

    def isOk(self):
        return self.resultType == ResultType.Ok

    def isError(self):
        return self.resultType == ResultType.Error

    # In this context, result = result of function.  If error, return None
    def getResult(self):
        if self.isError():
            return None
        return self.result

    # This will return the error string if this is an erro.  Otherwise, return None
    def getError(self):
        if self.isOk():
            return None
        return self.result
