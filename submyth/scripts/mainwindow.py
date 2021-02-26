import sys
import os
import re
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import QImage
from scripts.file import Srt, SubMythProject, Media
from scripts import tools
import pandas as pd


mainwindow_ui_file = "gui/mainwindow.ui"
Ui_MainWindow, QtBaseClass = uic.loadUiType(mainwindow_ui_file)
colors = tools.load_colors()
icons = tools.load_icons()
strings = tools.load_strings('en')


class SubtitleTableModel(QtCore.QAbstractTableModel):

    def __init__(self, data):
        super(SubtitleTableModel, self).__init__()
        self._data = data


    def data(self, index, role):
        if role == Qt.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            if index.column() < 2:
                return value.strftime('%H:%M:%S,%f')[:-3]
            return value


    def rowCount(self, index):
        return self._data.shape[0]


    def columnCount(self, index):
        return self._data.shape[1]


    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            
            if orientation == Qt.Vertical:
                return str(self._data.index[section])


    def flags(self, index):  # Qt was imported from PyQt4.QtCore
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable


class FileListModel(QtCore.QAbstractListModel):

    def __init__(self, *args, files, **kwargs):
        super(FileListModel, self).__init__(*args, **kwargs)
        self.files = files

    
    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self.files[index.row()].file_name
        
        if role == Qt.DecorationRole:
            file_name = self.files[index.row()].file_name
            file_format = tools.get_file_format(file_name)
            if file_format == "srt":
                return icons["Subtitle"]
            elif file_format == "wav":
                return icons["Sound"]
            elif file_format == "media":
                return icons["Video"]

        if role == Qt.TextColorRole:
            f = self.files[index.row()]
            if not f.is_online():
                return colors["OfflineFile"]
            elif f.is_changed:
                return colors["ChangedFile"]
            else:
                return colors["NormalFile"]


    def rowCount(self, index):
        return len(self.files)


class SubtitleWorkerSignals(QObject):
    finished = pyqtSignal(Srt)


class SubtitleWorker(QRunnable):

    def __init__(self, srt):
        super(SubtitleWorker, self).__init__()

        self.srt = srt
        self.signals = SubtitleWorkerSignals()


    @pyqtSlot()
    def run(self):
        self.srt.parse()
        self.signals.finished.emit(self.srt)


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)

        self.setWindowTitle(strings["Title"])
        self.textEdit.setEnabled(False)
        
        # Project menu actions
        self.actionNewProject.triggered.connect(self.actionNewProjectButtonClick)
        self.actionOpenProject.triggered.connect(self.actionOpenProjectButtonClick)
        self.actionSaveProject.triggered.connect(self.actionSaveProjectButtonClick)
        self.actionClose.triggered.connect(self.actionCloseButtonClick)
        
        # File menu actions
        self.actionNewFile.triggered.connect(self.actionNewFileButtonClick)
        self.actionOpenFile.triggered.connect(self.actionOpenFileButtonClick)
        self.actionSaveFile.triggered.connect(self.actionSaveFileButtonClick)
        self.actionSaveAsFile.triggered.connect(self.actionSaveAsFileButtonClick)
        self.actionRemove.triggered.connect(self.actionRemoveButtonClick)


        self.soundPlot.showAxis('left', False)
        self.soundPlot.showAxis('bottom', False)
        self.mainSoundPlot.showAxis('left', False)
        self.mainSoundPlot.showAxis('bottom', False)

        self.comboBox.currentIndexChanged.connect(self.currentProjectChange)
        self.listView.doubleClicked.connect(self.listViewDoubleClick)
        self.tableView.clicked.connect(self.subTableClick)
        self.textEdit.textChanged.connect(self.textEditTextChange)

        self.projects = {}

        self.currentProjectChange(-1)

        self.threadpool = QThreadPool()
        self.openedSrt = None
        self.openedMedia = None


    def actionNewProjectButtonClick(self, s):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,"New File", "","SubMyth Project (*.smpr)", options=options)
        if fileName:
            fileName = tools.add_file_format(fileName, "smpr")
            path, fileName = os.path.split(fileName)
            project = SubMythProject(fileName, path)
            self.projects[fileName] = project
            project.save()
            self.comboBox.addItem(fileName)
            self.comboBox.setCurrentText(fileName)


    def actionOpenProjectButtonClick(self, s):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self,"Open Project", "","All Files (*);;SubMyth Project (*.smpr)", options=options)
        if fileName:
            file_format = tools.get_file_format(fileName)
            if file_format == "smpr":
                project = SubMythProject.load(fileName)
                self.projects[project.file_name] = project
                self.comboBox.addItem(project.file_name)
                self.comboBox.setCurrentText(project.file_name)
            else:
                print("Invalid File Format")


    def actionSaveProjectButtonClick(self, s):
        self.selectedProject.save()
        self.currentProjectChange(self.comboBox.currentIndex())


    def actionCloseButtonClick(self, s):
        print(s)


    def actionNewFileButtonClick(self, s):
        print(s)


    def actionOpenFileButtonClick(self, s):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self,"Open File", "","All Files (*);;Subtitle (*.srt);;Media (*.wav)", options=options)
        if fileName:
            file_format = tools.get_file_format(fileName)
            if file_format == "srt":
                path, file_name = os.path.split(fileName)
                f = Srt(file_name, path)
                self.selectedProject.add_file(f)
                self.currentProjectChange(self.comboBox.currentIndex())
            elif file_format == "smpr":
                project = SubMythProject.load(fileName)
                self.projects[project.file_name] = project
                self.comboBox.addItem(project.file_name)
                self.comboBox.setCurrentText(project.file_name)
            elif file_format == "wav":
                path, file_name = os.path.split(fileName)
                f = Media(file_name, path)
                self.selectedProject.add_file(f)
                self.currentProjectChange(self.comboBox.currentIndex())


    def actionSaveFileButtonClick(self, s):
        print(s)
    

    def actionSaveAsFileButtonClick(self, s):
        print(s)

    
    def actionRemoveButtonClick(self, s):
        print(s)

    
    def currentProjectChange(self, index):
        not_empty = index != -1
        for action in [self.actionNewFile, self.actionOpenFile, self.actionSaveFile,
                       self.actionSaveAsFile, self.actionSaveProject, self.menuRecentFile, 
                       self.actionRemove, self.actionClose]:
            action.setEnabled(not_empty)
        if not_empty:
            self.selectedProject = self.projects[self.comboBox.currentText()]
            self.actionSaveProject.setEnabled(self.selectedProject.is_changed)
            self.fileListModel = FileListModel(files = self.selectedProject.files)
            self.listView.setModel(self.fileListModel)


    def listViewDoubleClick(self, item) :
        indexes = self.listView.selectedIndexes()
        for index in indexes :
            f = self.fileListModel.files[index.row()]
            if type(f) == Srt:
                self.openedSrt = f
                if f.parsed() :
                    self.subTableModel = SubtitleTableModel(f.parts)
                    self.tableView.setModel(self.subTableModel)
                    
                    hheader = self.tableView.horizontalHeader()       
                    hheader.setResizeMode(QtWidgets.QHeaderView.ResizeToContents)
                else :
                    date = pd.to_datetime("00:00:00,000", format='%H:%M:%S,%f')
                    df = pd.DataFrame({'start':[date], 'end':[date], 'text':['Loading ...']})
                    self.subTableModel = SubtitleTableModel(df)
                    self.tableView.setModel(self.subTableModel)
                    worker = SubtitleWorker(f)
                    worker.signals.finished.connect(self.subtitleParsed)
                    self.threadpool.start(worker)


    def subtitleParsed(self, srt):
        self.subTableModel = SubtitleTableModel(srt.parts)
        self.tableView.setModel(self.subTableModel)
        
        hheader = self.tableView.horizontalHeader()       
        hheader.setResizeMode(QtWidgets.QHeaderView.ResizeToContents)


    def subTableClick(self, item):
        self.textEdit.setEnabled(True)
        self.subTableSelectedItem = item
        data = self.subTableModel._data.iloc[item.row(), item.column()]
        if item.column() < 2:
            data = data.strftime('%H:%M:%S,%f')[:-3]
        self.textEdit.setText(data)


    def textEditTextChange(self):
        item = self.subTableSelectedItem
        if item.column() < 2:
            text = self.textEdit.toPlainText()
            original = self.openedSrt.parts.iloc[item.row(), item.column()]
            # TODO Check Regex
            matches = re.findall(r"(\d{1,2}):(\d{1,2}):(\d{1,2}),(\d{1,3})", text)
            if len(matches) == 1 :
                if 0 <= int(matches[0][1]) <= 59 and 0 <= int(matches[0][2]) <= 59 :
                    self.textEdit.setStyleSheet("color: black")
                    date = pd.to_datetime(text, format='%H:%M:%S,%f')
                    if date != original:
                        self.openedSrt.parts.iloc[item.row(), item.column()] = date
                        self.subTableModel._data.iloc[item.row(), item.column()] = date
                        self.openedSrt.is_changed = True
                else:
                    self.textEdit.setStyleSheet("color: red")
            else:
                self.textEdit.setStyleSheet("color: red")
        else:
            text = self.textEdit.toPlainText()
            original = self.openedSrt.parts.iloc[item.row(), item.column()]
            if text != original:
                self.openedSrt.parts.iloc[item.row(), item.column()] = text
                self.subTableModel._data.iloc[item.row(), item.column()] = text
                self.openedSrt.is_changed = True
        