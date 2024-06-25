# Original plugin created for Skyrim by bluebuiy
# Original Mod Page: https://www.nexusmods.com/skyrimspecialedition/mods/59598
# This ver Mod Page: https://www.nexusmods.com/fallout4/mods/84962
# Modified for Fallout 4
# For mo 2.5.0+. Use at your own risk.

import mobase # type: ignore
import re
import typing
from PyQt6.QtCore import Qt, pyqtSignal, QAbstractItemModel, QModelIndex
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QWidget, QCheckBox, QPushButton, QListView

xEditExeName = "FO4Edit"
mainMaster = "Fallout4.esm"
bethPlugins = {
	"DLCRobot.esm",
	"DLCworkshop01.esm",
	"DLCworkshop02.esm",
	"DLCworkshop03.esm",
	"DLCCoast.esm",
	"DLCNukaWorld.esm",
	"DLCUltraHighResolution.esm",
}
launchOptions = [
	"-IKnowWhatImDoing",
	"-QuickAutoClean",
	"-autoexit",
	"-autoload",
]
ccPattern = re.compile("cc\w{6}[0-9]{3}-")

class PluginSelectionLine(QWidget):
	enableChange = pyqtSignal(bool, str)

	def __init__(self, pluginName: str, parent: typing.Optional[QWidget]=None) -> None:
		super(PluginSelectionLine, self).__init__(parent)
		self.__pluginName = pluginName
		self.__checkbox = QCheckBox(pluginName, self)
		self.__checkbox.stateChanged.connect(self.__checkboxChange)

		layout = QVBoxLayout(self)
		layout.addWidget(self.__checkbox)

	def __checkboxChange(self, state: Qt.CheckState) -> None:
		self.enableChange.emit(self.__checkbox.isChecked(), self.__pluginName)

	def setState(self, state: bool) -> None:
		if state:
			self.__checkbox.setCheckState(2)
		else:
			self.__checkbox.setCheckState(0)

class PluginListModel(QAbstractItemModel):
	def __init__(self, parent: typing.Optional[QWidget]=None) -> None:
		super(PluginListModel, self).__init__(parent)
		self.__data: list[tuple[bool, str, int]] = []

	def flags(self, index: QModelIndex) -> Qt.ItemFlag:
		if index.isValid():
			return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable

	def index(self, row: int, col: int, parent: QModelIndex) -> QModelIndex:
		if col == 0:
			return self.createIndex(row, col, self.__data[row][1])
		return QModelIndex()

	def parent(self, childIndex: QModelIndex) -> QModelIndex:
		return QModelIndex()

	def rowCount(self, index: QModelIndex) -> int:
		return len(self.__data)

	def columnCount(self, index: QModelIndex) -> int:
		return 1

	def data(self, index: QModelIndex, role: int):
		row = index.row()
		if role == Qt.ItemDataRole.CheckStateRole:
			if self.__data[row][0]:
				return Qt.CheckState.Checked
			else:
				return Qt.CheckState.Unchecked

		if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
			return self.__data[row][1]
		return None

	def setData(self, index: QModelIndex, value: typing.Any, role: int) -> bool:
		if role == Qt.ItemDataRole.CheckStateRole and index.isValid():
			inState = None
			# I have no idea how these are supposed to be referenced. Qt.CheckState.Checked and Qt.CheckState.Unchecked are not working.
			if value == 2:
				inState = True
			elif value == 0:
				inState = False

			if inState is not None:
				self.__data[index.row()] = (inState, self.__data[index.row()][1], self.__data[index.row()][2])
				self.dataChanged.emit(index, index, [role])

			return True
		return False

	def addPlugin(self, pluginName: str, priority: int, state: bool) -> None:
		self.__data.append((state, pluginName, priority))

	def getEnabledPlugins(self) -> set[str]:
		ret = set()
		for item in self.__data:
			if item[0]:
				ret.add(item[1])
		return ret

	def deselectAll(self) -> None:
		self.beginResetModel()
		for i, val in enumerate(self.__data):
			self.__data[i] = (False, val[1], val[2])
		self.endResetModel()

	def selectAll(self) -> None:
		self.beginResetModel()
		for i, val in enumerate(self.__data):
			self.__data[i] = (True, val[1], val[2])
		self.endResetModel()

	def sortData(self, key: typing.Callable) -> None:
		self.beginResetModel()
		self.__data.sort(key=key)
		self.endResetModel()

class PluginSelectWindow(QDialog):
	startAction = pyqtSignal()
	cancelAction = pyqtSignal()

	def __init__(self, parent: typing.Optional[QWidget]=None) -> None:
		super(PluginSelectWindow, self).__init__(parent)
		self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
		self.setWindowTitle("Batch Plugin Cleaner")
		self.resize(400, 600)
		self.__listModel = PluginListModel()
		self.__layout = QHBoxLayout()
		self.__listView = QListView()
		self.__listView.setModel(self.__listModel)

		selectAllButton = QPushButton("Select All")
		selectNoneButton = QPushButton("Select None")
		startButton = QPushButton("Clean")

		self.__layout.addWidget(self.__listView)

		buttonHolder = QWidget()
		buttonLayout = QVBoxLayout(buttonHolder)

		buttonLayout.addWidget(selectAllButton)
		buttonLayout.addWidget(selectNoneButton)
		buttonLayout.addWidget(startButton)

		self.__layout.addWidget(buttonHolder)

		self.setLayout(self.__layout)

		selectAllButton.clicked.connect(self.__selectAll)
		selectNoneButton.clicked.connect(self.__selectNone)
		startButton.clicked.connect(self.__startPressed)

	def addPlugin(self, pluginName: str, priority: int, defaultState: bool) -> None:
		self.__listModel.addPlugin(pluginName, priority, defaultState)

	def getPluginList(self) -> set[str]:
		return self.__listModel.getEnabledPlugins()

	def sortPlugins(self, key: typing.Callable) -> None:
		self.__listModel.sortData(key)

	def __startPressed(self) -> None:
		self.startAction.emit()

	def __selectNone(self) -> None:
		self.__listModel.deselectAll()

	def __selectAll(self) -> None:
		self.__listModel.selectAll()

class CleanerPlugin(mobase.IPluginTool):
	def __init__(self) -> None:
		super().__init__()
		self.__canceled = False

	def init(self, organizer: mobase.IOrganizer) -> bool:
		self.__organizer = organizer
		return True

	def name(self) -> str:
		return "Batch Plugin Cleaner"

	def author(self) -> str:
		return "bluebuiy & wxMichael"

	def displayName(self) -> str:
		return "Clean Plugins"

	def description(self) -> str:
		return f"Clean all plugins with one button. Requres {xEditExeName}."

	def version(self) -> mobase.VersionInfo:
		return mobase.VersionInfo(1, 0, 0)

	def isActive(self) -> mobase.MoVariant:
		return self.__organizer.pluginSetting(self.name(), "enabled")

	def tooltip(self) -> str:
		return "Clean all plugins at once"

	def settings(self) -> list[mobase.PluginSetting]:
		return [
			mobase.PluginSetting("enabled", "Enable this plugin", True),
			mobase.PluginSetting("clean_cc", "Clean Creation Club plugins", True),
			mobase.PluginSetting("clean_beth", "Clean base game plugins", False),
			mobase.PluginSetting("clean_else", "Clean mod plugins", True),
			mobase.PluginSetting("sort_by_priority", "If plugins should be ordered by priority instead of alphabetically", True),
			mobase.PluginSetting("explicit_data_path", "If the data directory should be explicitly provided.  May need to be enabled if you get errors from xEdit.", False),
			mobase.PluginSetting("explicit_ini_path", "If the ini path should be explicitly provided.  May need to be enabled if you get errors from xEdit.", False),
			mobase.PluginSetting("explicit_game_arg", "Adds -<game> as an argument to xEdit. Options: sse tes5vr fo4vr test4 tes5 enderal fo3 fnv fo4 fo76", ""),
			mobase.PluginSetting("exe_name_xedit", f"Invoke xEdit as xEdit, not {xEditExeName}. You probably need explicit_game_arg too.", False)
		]

	def icon(self) -> QIcon:
		return QIcon()

	def setParentWidget(self, widget: QWidget) -> None:
		self.__parentWidget = widget

	def display(self) -> None:
		self.__dialog = PluginSelectWindow(self.__parentWidget)
		self.__dialog.startAction.connect(self.__start)

		pluginList = self.__organizer.pluginList()
		pluginNames = list(pluginList.pluginNames())
		# Exclude main esm because it should not be cleaned.
		pluginNames.remove(mainMaster)

		cleanCC = self.__organizer.pluginSetting(self.name(), "clean_cc")
		cleanBeth = self.__organizer.pluginSetting(self.name(), "clean_beth")
		cleanElse = self.__organizer.pluginSetting(self.name(), "clean_else")
		for plugin in pluginNames:
			pluginDefaultState = False

			if pluginList.state(plugin) == mobase.PluginState.ACTIVE:
				isCC = ccPattern.match(plugin) is not None
				isBeth = plugin in bethPlugins
				if (cleanCC and isCC) or (cleanBeth and isBeth):
					pluginDefaultState = True
				if not isBeth and not isCC and cleanElse:
					pluginDefaultState = True

			self.__dialog.addPlugin(plugin, pluginList.priority(plugin), pluginDefaultState)

		if self.__organizer.pluginSetting(self.name(), "sort_by_priority"):
			self.__dialog.sortPlugins(key=lambda tup: tup[2])
		else:
			self.__dialog.sortPlugins(key=lambda tup: tup[1])

		self.__dialog.open()

	def __start(self) -> None:
		self.runClean(self.__dialog.getPluginList())

	def runClean(self, pluginNamesSet: set[str]) -> None:
		failed = []
		xEditPath = "xEdit" if self.__organizer.pluginSetting(self.name(), "exe_name_xedit") else xEditExeName
		cleanCount = 0
		pluginNames = list(pluginNamesSet)
		# Sort the plugins so they are cleaned by priority
		pluginNames.sort(key=lambda pluginName: 0 - self.__organizer.pluginList().priority(pluginName))
		for plugin in pluginNames:

			if self.__canceled:
				self.__canceled = False
				break

			args = list(launchOptions)
			args.append(f"\"{plugin}\"")

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

def createPlugin() -> mobase.IPluginTool:
	return CleanerPlugin()
