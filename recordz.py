import numpy as np
import time

class Record:
 
    def __init__(self):
        self.recordTimeStmp = time.time()
        self.dataDictionary = None

    def toDateStr(self, timeStmp):
        return time.strftime("%m/%d/%Y", time.localtime(timeStmp))

    def toTimeStr(self, timeStmp):
        return time.strftime("%H:%M:%S", time.localtime(timeStmp))

class LiveRecord:
    def __init__(self):
        super.__init__(self)

test = Record()
print(test.toDateStr(test.recordTimeStmp), test.toTimeStr(test.recordTimeStmp))
