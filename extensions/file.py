class file:

    def __init__(self, filename):
        print('(FILE class) creating file output: ' + filename)
        self.filename = filename

    def appendFile(self, payload):
        with open(self.filename, 'a') as file:
            file.write(payload)
        print('(FILE class) payload appended to file ' + self.filename + ': ' + str(payload)[:40])
