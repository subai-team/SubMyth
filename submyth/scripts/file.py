import re
import string
from datetime import datetime
import pandas as pd
import pickle
import os


class File:

    def __init__(self, file_name, path, is_changed) :
        self.file_name = file_name
        self.path = path
        self.index = 0
        self.is_changed = is_changed
    

    def is_online(self):
        return os.path.exists(os.path.join(self.path, self.file_name))
        

    def get_name(self):
        if self.index == 0:
            return self.file_name
        else:
            return "{0} ({1})".format(self.file_name, self.index)


class Srt(File):

    def __init__(self, file_name, path, is_changed = False):
        super().__init__(file_name, path, is_changed)
        self.parts = pd.DataFrame({'start': pd.Series([], dtype='float'),
                                   'end': pd.Series([], dtype='float'),
                                   'text': pd.Series([], dtype='str')})


    def __eq__(self, obj):
        return self.file_name == obj.file_name and self.path == obj.path


    def parse(self):
        with open(os.path.join(self.path, self.file_name)) as srt_file:
            lines = []
            for line in srt_file:
                if line == "\n":
                    if len(lines) > 0:
                        index, part = self.__lines_to_part(lines)
                        self.parts.loc[index] = part
                        lines = []
                else:
                    lines.append(line)
    
    def parsed(self):
        return len(self.parts) > 0

    
    def save(self):
        lines = []
        for index, row in self.parts.iterrows():
            lines.append(str(index) + "\n")
            lines.append(row['start'].strftime('%H:%M:%S,%f')[:-3] + " --> " + row['end'].strftime('%H:%M:%S,%f')[:-3] + "\n")
            lines.append(row['text'] + "\n")
            lines.append('\n')
        with open(os.path.join(self.path, self.file_name), "w") as f:
            f.writelines(lines)
        self.is_changed = False


    def __lines_to_part(self, lines):
        part = [0, 0, '']
        index = self.__str_to_index(lines[0])
        start, end = re.findall(r"\d{2}:\d{2}:\d{2},\d{3}", lines[1])
        part[0] = self.__time_to_number(start)
        part[1] = self.__time_to_number(end)
        part[2] = "".join(lines[2:])[:-1]
        return index, part


    def __str_to_index(self, index):
        for ch in index:
            if ch > '9' or ch < '0':
                index = index.replace(ch, '')
        return int(index)


    def __time_to_number(self, time):
        return pd.to_datetime(time, format="%H:%M:%S,%f")


class Media(File):

    def __init__(self, file_name, path, is_changed = False):
        super().__init__(file_name, path, is_changed)


    def sth(self):
        pass


class SubMythProject:
    
    def __init__(self, file_name, path, files = [], is_changed = False):
        self.file_name = file_name
        self.path = path
        self.files = files
        self.is_changed = is_changed

    
    def add_file(self, file):
        for f in self.files:
            if file.file_name == f.file_name:
                if file == f:
                    return None
                else:
                    file.index = max(file.index, f.index + 1)
        self.files.append(file)
        self.is_changed = True

    
    def save(self):
        with open(os.path.join(self.path, self.file_name), "wb") as f :
            pickler = pickle.Pickler(f)
            self.is_changed = False
            pickler.dump(self)


    @staticmethod
    def load(fileName):
        with open(fileName, "rb") as f :
            unpickler = pickle.Unpickler(f)
            project = unpickler.load()
            path, file_name = os.path.split(fileName)
            project.path = path
            project.file_name = file_name
            return project
