# Python commands in this file are executed on Slicer startup

# Examples:
#
# Load a scene file
# slicer.util.loadScene('c:/Users/SomeUser/Documents/SlicerScenes/SomeScene.mrb')
#
# Open a module (overrides default startup module in application settings / modules)
# slicer.util.mainWindow().moduleSelector().selectModule('registrationViewer')
#
path = "/home/koeglf/Documents/code/registrationViewer/"


def select_extension_and_module(path_to_load: str) -> None:

    import ast
    import os

    import qt

    import slicer

    from slicer.i18n import tr as _

    # -----------------------------------------------------------------------------
    def _dialogIcon(icon):
        s = slicer.app.style()
        i = s.standardIcon(icon)
        return i.pixmap(qt.QSize(64, 64))

    # =============================================================================
    #
    # _ui_LoadModulesDialog
    #
    # =============================================================================

    class _ui_LoadModulesDialog:
        # ---------------------------------------------------------------------------
        def __init__(self, parent):
            vLayout = qt.QVBoxLayout(parent)
            hLayout = qt.QHBoxLayout()

            self.icon = qt.QLabel()
            self.icon.setPixmap(_dialogIcon(qt.QStyle.SP_MessageBoxQuestion))
            hLayout.addWidget(self.icon, 0)

            self.label = qt.QLabel()
            self.label.wordWrap = True
            hLayout.addWidget(self.label, 1)

            vLayout.addLayout(hLayout)

            self.moduleList = qt.QListWidget()
            self.moduleList.selectionMode = qt.QAbstractItemView.NoSelection
            vLayout.addWidget(self.moduleList)

            self.addToSearchPaths = qt.QCheckBox()
            vLayout.addWidget(self.addToSearchPaths)
            self.addToSearchPaths.checked = True

            self.enableDeveloperMode = qt.QCheckBox()
            self.enableDeveloperMode.text = _("Enable developer mode")
            self.enableDeveloperMode.toolTip = _("Sets the 'Developer mode' "
                                                 "application option to enabled. Enabling developer mode is "
                                                 "recommended while developing scripted modules, as it makes "
                                                 "the Reload and Testing section displayed in "
                                                 "the module user interface.")
            self.enableDeveloperMode.checked = True
            vLayout.addWidget(self.enableDeveloperMode)

            self.buttonBox = qt.QDialogButtonBox()
            self.buttonBox.setStandardButtons(qt.QDialogButtonBox.Yes |
                                              qt.QDialogButtonBox.No)
            vLayout.addWidget(self.buttonBox)

    # =============================================================================
    #
    # LoadModulesDialog
    #
    # =============================================================================

    class LoadModulesDialog:
        # ---------------------------------------------------------------------------
        def __init__(self, parent):
            self.dialog = qt.QDialog(parent)
            self.ui = _ui_LoadModulesDialog(self.dialog)

            self.ui.buttonBox.connect("accepted()", self.dialog, "accept()")
            self.ui.buttonBox.connect("rejected()", self.dialog, "reject()")
            self.ui.moduleList.connect(
                "itemChanged(QListWidgetItem*)", self.validate)

        # ---------------------------------------------------------------------------
        def validate(self):
            moduleCount = len(self.selectedModules)

            if moduleCount == 0:
                self.ui.buttonBox.button(
                    qt.QDialogButtonBox.Yes).enabled = False
                self.ui.addToSearchPaths.enabled = False

                moduleCount = len(self._moduleItems)

            else:
                self.ui.buttonBox.button(
                    qt.QDialogButtonBox.Yes).enabled = True
                self.ui.addToSearchPaths.enabled = True

            if moduleCount == 1:
                self.ui.addToSearchPaths.text = _(
                    "Add selected module to 'Additional module paths'")
            else:
                self.ui.addToSearchPaths.text = _(
                    "Add selected modules to 'Additional module paths'")

            # If developer mode is already enabled then don't even show the option
            developerModeAlreadyEnabled = slicer.util.settingsValue(
                "Developer/DeveloperMode", False, converter=slicer.util.toBool)
            if developerModeAlreadyEnabled:
                self.ui.enableDeveloperMode.visible = False
                self.ui.enableDeveloperMode.checked = False

        # ---------------------------------------------------------------------------
        def exec_(self):
            return self.dialog.exec_()

        # ---------------------------------------------------------------------------
        def setModules(self, modules):
            self.ui.moduleList.clear()
            self._moduleItems = {}

            for module in modules:
                item = qt.QListWidgetItem(module.key)
                item.setFlags(item.flags() | qt.Qt.ItemIsUserCheckable)
                item.setCheckState(qt.Qt.Checked)
                self.ui.moduleList.addItem(item)
                self._moduleItems[item] = module

            if len(modules) > 1:
                self.ui.label.text = _(
                    "The following modules can be loaded. Would you like to load them now?")

            elif len(modules) == 1:
                self.ui.label.text = _(
                    "The following module can be loaded. Would you like to load it now?")

            else:
                raise ValueError(_("At least one module must be provided"))

            self.validate()

        # ---------------------------------------------------------------------------
        @property
        def addToSearchPaths(self):
            return self.ui.addToSearchPaths.checked

        # ---------------------------------------------------------------------------
        @property
        def enableDeveloperMode(self):
            return self.ui.enableDeveloperMode.checked

        # ---------------------------------------------------------------------------
        @property
        def selectedModules(self):
            result = []

            for item, module in self._moduleItems.items():
                if item.checkState():
                    result.append(module)

            return result

    # =============================================================================
    #
    # _ui_CreateComponentDialog
    #
    # =============================================================================
    # =============================================================================
    #
    # ModuleInfo
    #
    # =============================================================================
    class ModuleInfo:
        # ---------------------------------------------------------------------------
        def __init__(self, path, key=None):
            self.path = path
            self.searchPath = os.path.dirname(path)

            if key is None:
                self.key = os.path.splitext(os.path.basename(path))[0]
            else:
                self.key = key

        # ---------------------------------------------------------------------------
        def __repr__(self):
            return "ModuleInfo(key=%(key)r, path=%(path)r)" % self.__dict__

        # ---------------------------------------------------------------------------
        def __str__(self):
            return self.path

        # ---------------------------------------------------------------------------
        @staticmethod
        def findModules(path, depth):
            result = []
            if os.path.isfile(path):
                entries = [path]
            elif os.path.isdir(path):
                entries = [os.path.join(path, entry)
                           for entry in os.listdir(path)]
                # If the folder contains __init__.py, it means that this folder
                # is not a Slicer module but an embedded Python library that a module will load.
                if any(entry.endswith("__init__.py") for entry in entries):
                    entries = []
            else:
                # not a file or folder
                return result

            if depth > 0:
                for entry in filter(os.path.isdir, entries):
                    result += ModuleInfo.findModules(entry, depth - 1)

            for entry in filter(os.path.isfile, entries):
                if not entry.endswith(".py"):
                    continue

                # Criteria for a Slicer module to have a module class
                # that has the same name as the filename and its base class is ScriptedLoadableModule.

                try:
                    # Find all class definitions
                    with open(entry) as entry_file:
                        tree = ast.parse(entry_file.read())
                    classes = [node for node in tree.body if isinstance(
                        node, ast.ClassDef)]

                    # Add file if module class is found
                    filename = os.path.basename(entry)
                    expectedClassName = os.path.splitext(filename)[0]
                    for cls in classes:
                        if cls.name == expectedClassName:
                            # Found a class name that matches the filename
                            if "ScriptedLoadableModule" in [base.id for base in cls.bases]:
                                # Its base class is ScriptedLoadableModule
                                result.append(ModuleInfo(entry))
                except:
                    # Error while processing the file (e.g., syntax error),
                    # it cannot be a Slicer module.
                    pass

                # We have the option to identify scripted CLI modules, such as by examining the existence of a
                # compatible module descriptor XML file. However, this type of module is relatively uncommon, so
                # the decision was made not to invest in implementing this feature.

            return result

    def _settingsList(settings, key, convertToAbsolutePaths=False):
        # Return a settings value as a list (even if empty or a single value)

        value = settings.value(key)
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]

        if convertToAbsolutePaths:
            absolutePaths = []
            for path in value:
                absolutePaths.append(slicer.app.toSlicerHomeAbsolutePath(path))
            return absolutePaths
        else:
            return value

    def loadModules(path=None, depth=1, modules=None, parent=None):
        if parent is None:
            parent = slicer.util.mainWindow()
        if path is not None:
            # Get list of modules in specified path
            modules = ModuleInfo.findModules(path, depth)
        elif modules is None:
            raise RuntimeError("loadModules require 'path' or 'modules' input")

        # Determine which modules in above are not already loaded
        factory = slicer.app.moduleManager().factoryManager()
        loadedModules = factory.instantiatedModuleNames()

        candidates = [m for m in modules if m.key not in loadedModules]

        # Prompt to load additional module(s)
        if len(candidates):
            dlg = LoadModulesDialog(parent)
            dlg.setModules(candidates)

            modulesToLoad = dlg.selectedModules

            # Add module(s) to permanent search paths, if requested
            settings = slicer.app.revisionUserSettings()
            rawSearchPaths = list(_settingsList(
                settings, "Modules/AdditionalPaths", convertToAbsolutePaths=True))
            searchPaths = [qt.QDir(path) for path in rawSearchPaths]
            modified = False

            for module in modulesToLoad:
                rawPath = os.path.dirname(module.path)
                path = qt.QDir(rawPath)
                if path not in searchPaths:
                    searchPaths.append(path)
                    rawSearchPaths.append(rawPath)
                    modified = True

            if modified:
                settings.setValue(
                    "Modules/AdditionalPaths", slicer.app.toSlicerHomeRelativePaths(rawSearchPaths))

            # Enable developer mode (shows Reload&Test section, etc.), if requested
            qt.QSettings().setValue('Developer/DeveloperMode', 'true')

            # Register requested module(s)
            failed = []

            for module in modulesToLoad:
                factory.registerModule(qt.QFileInfo(module.path))
                if not factory.isRegistered(module.key):
                    failed.append(module)

            if len(failed):

                if len(failed) > 1:
                    text = "The following modules could not be registered:"
                else:
                    text = "The '%s' module could not be registered:" % failed[0].key

                failedFormat = "<ul><li>%(key)s<br/>(%(path)s)</li></ul>"
                detailedInformation = "".join(
                    [failedFormat % m.__dict__ for m in failed])

                slicer.util.errorDisplay(text, parent=parent, windowTitle="Module loading failed",
                                         standardButtons=qt.QMessageBox.Close, informativeText=detailedInformation)

                return

            # Instantiate and load requested module(s)
            if not factory.loadModules([module.key for module in modulesToLoad]):
                text = ("The module factory manager reported an error. "
                        "One or more of the requested module(s) and/or "
                        "dependencies thereof may not have been loaded.")
                slicer.util.errorDisplay(text, parent, windowTitle="Error loading module(s)",
                                         standardButtons=qt.QMessageBox.Close)

    loadModules(path_to_load)


select_extension_and_module(path)


slicer.util.mainWindow().moduleSelector().selectModule('registrationViewer')
