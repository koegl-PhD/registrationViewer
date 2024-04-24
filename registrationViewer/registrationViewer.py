import logging
import os
from typing import Annotated, Optional
import functools

import vtk
import vtk, qt
import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLScalarVolumeNode, vtkMRMLTransformNode

from registrationViewerLib import utils

#
# registrationViewer
#

class registrationViewer(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("registrationViewer")
        # folders where the module shows up in the module selector
        self.parent.categories = [
            translate("qSlicerAbstractCoreModule", "Examples")]
        self.parent.dependencies = []  # list of module names that this module requires
        self.parent.contributors = ["Fryderyk Kögl (TUM)"]
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""Basic module. See more information in <a href="https://github.com/koegl-PhD/registrationViewer">module documentation</a>.
""")
        self.parent.acknowledgementText = _("""
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""")

        # Additional initialization step after application startup is complete
        slicer.app.connect("startupCompleted()", registerSampleData)


#
# Register sample data sets in Sample Data module
#


def registerSampleData():
    """Add data sets to Sample Data module."""
    # It is always recommended to provide sample data for users to make it easy to try the module,
    # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

    import SampleData

    iconsPath = os.path.join(os.path.dirname(__file__), "Resources/Icons")

    # To ensure that the source code repository remains small (can be downloaded and installed quickly)
    # it is recommended to store data sets that are larger than a few MB in a Github release.

    # registrationViewer1
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category="helloWorld",
        sampleName="helloWorld1",
        # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
        # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
        thumbnailFileName=os.path.join(iconsPath, "helloWorld1.png"),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        fileNames="helloWorld1.nrrd",
        # Checksum to ensure file integrity. Can be computed by this command:
        #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
        checksums="SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        # This node name will be used when the data set is loaded
        nodeNames="helloWorld1",
    )

#
# registrationViewerParameterNode
#


@parameterNodeWrapper
class registrationViewerParameterNode:
    """
    The parameters needed by module.

    inputVolume - Input volume to print the name
    """

    volume_fixed: vtkMRMLScalarVolumeNode
    volume_moving: vtkMRMLScalarVolumeNode
    transformation: vtkMRMLTransformNode


#
# registrationViewerWidget
#
    
def place_my_crosshair_at(crosshair_node, transformation_matrix, position: tuple[float, float, float], use_transform = True, centered: bool = True, view_group: int = 1) -> None:
    """
    Place the crosshair at the given position. Position is in RAS coordinates.
    """
    
    # in normal views we should follow the cursor (that's why group 1)
    slicer.modules.markups.logic().JumpSlicesToLocation(position[0],
                                                        position[1],
                                                        position[2],
                                                        False,
                                                        1)
    
    # now we set the position of our corsshair and then transform it to the new position
    crosshair_node.SetNthControlPointPositionWorld(0, position[0], position[1], position[2])
    
    # now transform the crosshair to the new position
    if use_transform:
        crosshair_node.ApplyTransformMatrix(transformation_matrix)
    new_position = [0, 0, 0]
    crosshair_node.GetNthControlPointPositionWorld(0, new_position)
    
    # make it visible
    crosshair_node.GetDisplayNode().SetVisibility(True)
    
    # in plus views we should follow the transformed cursor (that's why group 2)
    slicer.modules.markups.logic().JumpSlicesToLocation(new_position[0],
                                                        new_position[1],
                                                        new_position[2],
                                                        False,
                                                        2)

def on_mouse_moved(self, observer, eventid):
    
    ras=[0,0,0]
    self.cursor_node.GetCursorPositionRAS(ras)
    
    # print(use_transform)
    
    place_my_crosshair_at(self.my_crosshair_node,
                          self.transformation_matrix,
                          position = (ras[0], ras[1], ras[2]),
                          use_transform=self.use_transform,
                          centered=False)
    

class registrationViewerWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        # needed for parameter node observation
        VTKObservationMixin.__init__(self)
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None
        
        # set the view to 3 over 3
        slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutThreeOverThreeView)
        
        self.group_normal = 1
        self.group_plus = 2
        self.views_normal = ["Red", "Green", "Yellow"]
        self.views_plus = ["Red+", "Green+", "Yellow+"]
        # set groups
        for i in range(3):
            slicer.app.layoutManager().sliceWidget(self.views_normal[i]).mrmlSliceNode().SetViewGroup(self.group_normal)
            slicer.app.layoutManager().sliceWidget(self.views_plus[i]).mrmlSliceNode().SetViewGroup(self.group_plus)
        
        # utils.create_shortcuts(('t', self.on_toggle_transform),
        #                        ('s', self.on_synchronise_views))
        
        shortcuts = [('t', self.on_toggle_transform),
                               ('s', self.on_synchronise_views)]
        for (shortcutKey, callback) in shortcuts:
            shortcut = qt.QShortcut(slicer.util.mainWindow())
            shortcut.setKey(qt.QKeySequence(shortcutKey))
            shortcut.connect('activated()', callback)
            
        self.use_transform = True
        
        self.my_crosshair_node = None
        self.cursor_node = None
        
        self.logic = registrationViewerLogic()
        
        self.pressed = False
        
    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/registrationViewer.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene,
                         slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.synchronise_views.connect("clicked(bool)", self.on_synchronise_views)
        self.ui.toggle_transform.connect("clicked(bool)", self.on_toggle_transform)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()
        
        node_volume_fixed = slicer.util.loadVolume(
            r"/home/fryderyk/Documents/code/registrationbaselines/registrationbaselines/data/unregistered/tumor1.nii")
        node_volume_moving = slicer.util.loadVolume(
            r"/home/fryderyk/Documents/code/registrationbaselines/registrationbaselines/data/unregistered/tumor2.nii")
        node_transformation = slicer.util.loadTransform(
            r"/home/fryderyk/Documents/code/registrationbaselines/registrationbaselines/data/unregistered/affine.h5")

        node_volume_fixed.SetName('volume_fixed')
        node_volume_moving.SetName('volume_moving')
        node_transformation.SetName('affine')

        # add to the scene
        slicer.mrmlScene.AddNode(node_volume_fixed)
        slicer.mrmlScene.AddNode(node_volume_moving)
        slicer.mrmlScene.AddNode(node_transformation)
        
        # set the nodes
        self.ui.inputSelector_fixed.setCurrentNode(node_volume_fixed)
        self.ui.inputSelector_moving.setCurrentNode(node_volume_moving)
        self.ui.inputSelector_transformation.setCurrentNode(node_transformation)
        
        self.my_crosshair_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        self.my_crosshair_node.SetName("")
        
        self.my_crosshair_node.AddControlPoint(0, 0, 0, "")
        self.my_crosshair_node.SetNthControlPointLabel(0, "")
        self.my_crosshair_node.GetDisplayNode().SetGlyphScale(1)
        
        sliceNodeRed_plus = slicer.app.layoutManager().sliceWidget("Red+").mrmlSliceNode()
        sliceNodeGreen_plus = slicer.app.layoutManager().sliceWidget("Green+").mrmlSliceNode()
        sliceNodeYellow_plus = slicer.app.layoutManager().sliceWidget("Yellow+").mrmlSliceNode()
        
        self.my_crosshair_node.GetDisplayNode().SetViewNodeIDs([sliceNodeRed_plus.GetID(), sliceNodeGreen_plus.GetID(), sliceNodeYellow_plus.GetID()])
        
        self.transformation_matrix = vtk.vtkMatrix4x4()
        node_transformation.GetMatrixTransformFromParent(self.transformation_matrix)

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""        
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # to do make smart selection
        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        # if not self._parameterNode.inputVolume:
        #     firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass(
        #         "vtkMRMLScalarVolumeNode")
        #     if firstVolumeNode:
        #         self._parameterNode.inputVolume = firstVolumeNode

    def setParameterNode(self, inputParameterNode: Optional[registrationViewerParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode,
                             vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            self._checkCanApply()

    # todo why is this needed
    def _checkCanApply(self, caller=None, event=None) -> None:
        pass
    
    def on_toggle_transform(self) -> None:            
        self.use_transform = not self.use_transform
        
        if self.use_transform:
            self.ui.toggle_transform.setText("Turn off transform (t)")
        else:
            self.ui.toggle_transform.setText("Turn on transform (t)")
    
    def on_synchronise_views(self) -> None:
        """Run processing when user clicks "Apply" button."""
        
        if self.pressed is False:
            self.cursor_node = slicer.util.getNode("Crosshair")
            self.cursor_node.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                                                            functools.partial(on_mouse_moved, self))
            self.pressed = True
            self.ui.synchronise_views.setText("Unsynchronise views (s)")
            
        else:
            self.cursor_node.RemoveAllObservers()
            self.pressed = False
            self.ui.synchronise_views.setText("Synchronise views (s)")

class registrationViewerLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return registrationViewerParameterNode(super().getParameterNode())

    def process(self, inputVolume: vtkMRMLScalarVolumeNode) -> None:
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        """

        if not inputVolume:
            raise ValueError("Input volume is invalid")

        import time

        startTime = time.time()
        logging.info("Processing started")

        utils.printVolumeName(inputVolume)

        # print(f"Volume name: {inputVolume.GetName()}")

        stopTime = time.time()
        logging.info(
            f"Processing completed in {stopTime-startTime:.2f} seconds")