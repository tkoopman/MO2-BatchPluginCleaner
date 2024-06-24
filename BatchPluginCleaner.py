# by bluebuiy
# for mo 2.5.0+
# use at your own risk

import mobase
import re
from PyQt6.QtCore import Qt, QCoreApplication, pyqtSlot, pyqtSignal, QAbstractItemModel, QModelIndex
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QWidget, QCheckBox, QPushButton, QScrollArea, QListView

class PluginSelectionLine(QWidget):
    enableChange = pyqtSignal(bool, str)

    def __init__(self, pluginName, parent=None):
        super(PluginSelectionLine, self).__init__(parent)
        self.__pluginName = pluginName
        self.__checkbox = QCheckBox(pluginName, self)
        self.__checkbox.stateChanged.connect(self.__checkboxChange)

        layout = QVBoxLayout(self)
        layout.addWidget(self.__checkbox)

    def __checkboxChange(self, state):
        self.enableChange.emit(self.__checkbox.isChecked(), self.__pluginName)

    def setState(self, state):
        if (state == True):
            self.__checkbox.setCheckState(2)    # 2
        else:
            self.__checkbox.setCheckState(0)  # 0

class PluginListModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super(PluginListModel, self).__init__(parent)
        self.__data = []

    def flags(self, index):
        if index.isValid():
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable

    def index(self, row, col, parent):
        if col == 0:
            return self.createIndex(row, col, self.__data[row][1])
        return QModelIndex()

    def parent(self, childIndex):
        return QModelIndex()

    def rowCount(self, index):
        return len(self.__data)
    
    def columnCount(self, index):
        return 1

    def data(self, index, role):
        row = index.row()
        if role == Qt.ItemDataRole.CheckStateRole:
            if self.__data[row][0] == True:
                return Qt.CheckState.Checked
            else:
                return Qt.CheckState.Unchecked

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return self.__data[row][1]
        
        return None

    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.CheckStateRole and index.isValid():
            inState = None
            # I have no idea how these are supposed to be referenced. Qt.CheckState.Checked and Qt.CheckState.Unchecked are not working.
            if value == 2:
                inState = True
            elif value == 0:
                inState = False
            
            if (inState != None):
                self.__data[index.row()] = (inState, self.__data[index.row()][1], self.__data[index.row()][2])
                self.dataChanged.emit(index, index, [role])
        
            return True
        
        return False

    def addPlugin(self, pluginName, priority, state):
        self.__data.append((state, pluginName, priority))

    def getEnabledPlugins(self) -> set:
        ret = set()
        for item in self.__data:
            if item[0] == True:
                ret.add(item[1])
        return ret

    def deselectAll(self):
        self.beginResetModel()
        for i, val in enumerate(self.__data):
            self.__data[i] = (False, val[1], val[2])
        self.endResetModel()

    def selectAll(self):
        self.beginResetModel()
        for i, val in enumerate(self.__data):
            self.__data[i] = (True, val[1], val[2])
        self.endResetModel()
        
    def sortData(self, key):
        self.beginResetModel()
        self.__data.sort(key=key)
        self.endResetModel()

class PluginSelectWindow(QDialog):
    startAction = pyqtSignal()
    cancelAction = pyqtSignal()

    def __init__(self, parent=None):
        super(PluginSelectWindow, self).__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.__listModel = PluginListModel()
        self.__layout = QHBoxLayout()
        self.__listView = QListView()
        self.__listView.setModel(self.__listModel)

        selectAllButton = QPushButton("Select All")
        selectNoneButton = QPushButton("Select None")
        startButton = QPushButton("Clean")
        #cancelButton = QPushButton("Cancel")

        self.__layout.addWidget(self.__listView)

        buttonHolder = QWidget()
        buttonLayout = QVBoxLayout(buttonHolder)

        buttonLayout.addWidget(selectAllButton)
        buttonLayout.addWidget(selectNoneButton)
        buttonLayout.addWidget(startButton)


        self.__layout.addWidget(buttonHolder)
        #self.__layout.addWidget(cancelButton)

        self.setLayout(self.__layout)

        selectAllButton.clicked.connect(self.__selectAll)
        selectNoneButton.clicked.connect(self.__selectNone)
        startButton.clicked.connect(self.__startPressed)
        #cancelButton.clicked.connect(self.__cancel)

    def addPlugin(self, pluginName, priority, defaultState):
        self.__listModel.addPlugin(pluginName, priority, defaultState)


    def getPluginList(self):
        return self.__listModel.getEnabledPlugins()

    def sortPlugins(self, key):
        self.__listModel.sortData(key)
        #self.__listModel.dataChanged.emit(0, len(__listModel.__data) - 1, Qt.ItemDataRole.EditRole)

    def __startPressed(self):
        self.startAction.emit()

    def __cancel(self):
        self.cancelAction.emit()

    def __selectNone(self):
        self.__listModel.deselectAll()

    def __selectAll(self):
        self.__listModel.selectAll()

class CleanerPlugin(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self.__canceled = False
        self.__cleaning = False

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self.__organizer = organizer
        return True

    def name(self):
        return "Batch Plugin Cleaner"
        
    def author(self):
        return "bluebuiy"

    def displayName(self):
        return "Clean Plugins"

    def description(self):
        return "Clean all plugins with one button. Requres SSEEdit."

    def version(self):
        return mobase.VersionInfo(0, 7, 0, mobase.ReleaseType.CANDIDATE)

    def isActive(self):
        return self.__organizer.pluginSetting(self.name(), "enabled")

    def tooltip(self):
        return "Clean all plugins at once"

    def settings(self):
        return [
            mobase.PluginSetting("enabled", "enable this plugin", True),
            mobase.PluginSetting("clean_cc", "Clean Creation Club plugins", True),
            mobase.PluginSetting("clean_beth", "Clean base game plugins", False),
            mobase.PluginSetting("clean_else", "Clean mod plugins", True),
            mobase.PluginSetting("sort_by_priority", "If plugins should be ordered by priority instead of alphabetically", True),
            mobase.PluginSetting("explicit_data_path", "If the data directory should be explicitly provided.  May need to be enabled if you get errors from xEdit.", False),
            mobase.PluginSetting("explicit_ini_path", "If the ini path should be explicitly provided.  May need to be enabled if you get errors from xEdit.", False),
            mobase.PluginSetting("explicit_game_arg", "Adds -<game> as an argument to xEdit. Options: sse tes5vr fo4vr test4 tes5 enderal fo3 fnv fo4 fo76", ""),
            mobase.PluginSetting("exe_name_xedit", "Invoke xEdit as xEdit, not SSEEdit. You probably need explicit_game_arg too.", False)
        ]

    def icon(self):
        return QIcon()

    def setParentWidget(self, widget):
        self.__parentWidget = widget

    def display(self):
        
        self.__dialog = PluginSelectWindow(self.__parentWidget)

        self.__dialog.startAction.connect(self.__start)

        pluginList = self.__organizer.pluginList()
        pluginNames = pluginList.pluginNames()

        # exclude Skyrim.esm because it should not be cleaned.
        bethPlugins = { "Update.esm", "Dawnguard.esm", "HearthFires.esm", "Dragonborn.esm" }
        matcher = re.compile("cc\w{6}[0-9]{3}-")
        cleanCC = self.__organizer.pluginSetting(self.name(), "clean_cc")
        cleanBeth = self.__organizer.pluginSetting(self.name(), "clean_beth")
        cleanElse = self.__organizer.pluginSetting(self.name(), "clean_else")
        for plugin in pluginNames:
            if (plugin != "Skyrim.esm"):
                pluginDefaultState = False
                isCC = matcher.match(plugin) != None
                isBeth = plugin in bethPlugins

                if ((cleanCC and isCC) or (cleanBeth and isBeth)):
                    pluginDefaultState = True
                if (isBeth == False and isCC == False and cleanElse == True):
                    pluginDefaultState = True
                
                self.__dialog.addPlugin(plugin, pluginList.priority(plugin), pluginDefaultState)

        if self.__organizer.pluginSetting(self.name(), "sort_by_priority"):
            self.__dialog.sortPlugins(key=lambda tup: tup[2])
        else:
            self.__dialog.sortPlugins(key=lambda tup: tup[1])

        self.__dialog.open()

    def __start(self):
        self.runClean(self.__dialog.getPluginList())

    def runClean(self, pluginNamesSet):
        self.__cleaning = True
        failed = []
        # Change to FO4Edit or whatever for whatever version of xEdit you are using.
        xEditPath = "xEdit" if self.__organizer.pluginSetting(self.name(), "exe_name_xedit") else "SSEEdit" 
        cleanCount = 0
        pluginNames = list(pluginNamesSet)
        # sort the plugins so they are cleaned by priority
        pluginNames.sort(key=lambda pluginName: 0 - self.__organizer.pluginList().priority(pluginName))
        for plugin in pluginNames:
            
            if self.__canceled:
                self.__canceled = False
                break
            args = ["-QuickAutoClean", "-autoexit", "-autoload", f"\"{plugin}\""]

            if self.__organizer.pluginSetting(self.name(), "explicit_data_path"):
                args.append(f"-D:\"{self.__organizer.managedGame().dataDirectory().absolutePath()}\"")

            if self.__organizer.pluginSetting(self.name(), "explicit_ini_path"):
                args.append(f"-I:\"{self.__organizer.managedGame().documentsDirectory().path()}/{self.__organizer.managedGame().iniFiles()[0]}\"")

            gameArg = self.__organizer.pluginSetting(self.name(), "explicit_game_arg")
            if len(gameArg) > 0:
                args.append(f"-{gameArg}")

            exe = self.__organizer.startApplication(xEditPath, args)
            
            if exe != 0:
                waitResult, exitCode = self.__organizer.waitForApplication(exe, False)
                if not waitResult:
                    self.__canceled = True
                elif exitCode != 0:
                    failed.append(plugin)
                else:
                    cleanCount += 1
            else:
                QMessageBox.critical(self.__parentWidget, f"Failed to start {xEditPath}", f"Make sure {xEditPath} is registered as a tool")
                break
        if len(failed) > 0:
            msg = ""
            for plugin in failed:
                msg = msg + plugin + "\n"
            QMessageBox.critical(self.__parentWidget, "Failed to clean some plugins!", msg)
        else:
            QMessageBox.information(self.__parentWidget, "Clean successful", f"Successfully cleaned {cleanCount} plugins")
    
        self.__cleaning = False

def createPlugin() -> mobase.IPluginTool:
    return CleanerPlugin()
    