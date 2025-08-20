from __future__ import annotations
import functools
import importlib
import logging
import os
import time

from typing import Optional, Any, List, Literal, Tuple, Dict, Callable

import numpy as np
import SimpleITK as sitk

import ctk
import vtk
import qt
import slicer
import slicer.util
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleWidget,
    ScriptedLoadableModuleLogic)
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
)
from slicer import vtkMRMLScalarVolumeNode, vtkMRMLSliceNode, vtkMRMLTransformNode  # pylint: disable=no-name-in-module

import CompareVolumes


class registrationViewer(ScriptedLoadableModule):
    """_summary_

    Args:
        ScriptedLoadableModule (_type_): _description_
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("registrationViewer")
        # folders where the module shows up in the module selector
        self.parent.categories = [
            translate("qSlicerAbstractCoreModule", "Examples")]
        self.parent.dependencies = []  # list of module names that this module requires
        self.parent.contributors = ["Fryderyk Kögl (TUM)"]
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""Basic module. See more information in <a href="https://github.com/koegl-PhD/registrationViewer">module documentation</a>.
""")
        self.parent.acknowledgementText = _("""
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""")

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


class registrationViewerWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        # needed for parameter node observation
        VTKObservationMixin.__init__(self)
        self._parameterNode: Optional[registrationViewerParameterNode] = None
        self._parameterNodeGuiTag = None

        self._sceneObserverTag: Optional[int] = None

        shortcut = qt.QShortcut(slicer.util.mainWindow())
        shortcut.setKey(qt.QKeySequence('s'))
        shortcut.connect('activated()', self.on_synchronise_views)

        self.crosshair = None

        self.synchronise_pressed = False
        self.crosshair_custom_observer_tags = []

        self.selected_jacobian_modes: Literal["Foldings", "Shrinkage", "Expansion", "Continuous"] = [
            "Foldings", "Shrinkage", "Expansion"]

        self.jacobian_volume = None
        self.jacobian_label_continuous = None
        self.jacobian_label_discrete = None

        # NEEDED
        self.update_jacobian = True
        self.jacobian_was_calculated = False
        self.node_segmentation_discrete = None
        self.node_segmentation_continuous = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        uiWidget = slicer.util.loadUI(
            self.resourcePath("UI/registrationViewer.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        slicer.app.processEvents()  # Ensures all widgets are fully rendered

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        for selector in [self.ui.inputSelector_fixed,
                         self.ui.inputSelector_moving,
                         self.ui.inputSelector_transformation]:
            selector.setMRMLScene(slicer.mrmlScene)
            selector.connect("currentNodeChanged(vtkMRMLNode*)",
                             self._on_inputs_changed)

        if self._sceneObserverTag is None:
            self._sceneObserverTag = slicer.mrmlScene.AddObserver(
                slicer.mrmlScene.NodeAddedEvent, self._on_node_added
            )

        # Create logic classes. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = registrationViewerLogic()
        self.CompareVolumes_logic = CompareVolumes.CompareVolumesLogic()

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene,
                         slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        self.synchronise_pressed = False
        self.ui.synchronise_views_with_transform.setText(
            "Synchronise views (s)")

        # Buttons
        self.ui.synchronise_views_with_transform.connect(
            "clicked(bool)", self.on_synchronise_views)

        self.ui.hotLinkWithCursor_checkbox.connect(
            "stateChanged(int)", self._update_from_gui)

        self._add_jacobian_widget()

        self._add_visualization_widget()

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def _add_jacobian_widget(self) -> None:
        row: int = self.ui.formLayout_2.rowCount()

        # Create the "Show jacobian" checkbox
        self.show_jacobian_checkbox = qt.QCheckBox()
        self.show_jacobian_checkbox.text = "Show jacobian"
        self.show_jacobian_checkbox.connect(
            "clicked()", self._on_show_jacobian_toggled)

        # Create the jacobian mode selection box
        self.jacobian_box = qt.QGroupBox()
        self.jacobian_box.setLayout(qt.QFormLayout())
        self.jacobian_buttons = {}
        self.jacobian_modes = ("Foldings", "Shrinkage",
                               "Expansion", "Continuous")

        for mode in self.jacobian_modes:
            self.jacobian_buttons[mode] = qt.QCheckBox()
            self.jacobian_buttons[mode].text = mode
            self.jacobian_buttons[mode].connect("clicked()",
                                                lambda m=mode: self._set_jacobian_mode(m))
            self.jacobian_box.layout().addWidget(
                self.jacobian_buttons[mode])

            if mode != "Continuous":
                self.jacobian_buttons[mode].setChecked(True)

        # Add slider at the bottom of the QGroupBox
        self.jacobian_slider = qt.QSlider(qt.Qt.Horizontal)
        self.jacobian_slider.setMinimum(0)
        self.jacobian_slider.setMaximum(100)  # 0-100 for 0.0-1.0 range
        self.jacobian_slider.setValue(50)     # Default to 0.5
        self.jacobian_slider.connect(
            "valueChanged(int)", self._on_jacobian_slider_changed)

        # Optional: Add a label to show current value
        self.jacobian_slider_label = qt.QLabel("0.50")

        # Create a horizontal layout for threshold label and slider
        threshold_layout = qt.QHBoxLayout()
        threshold_layout.addWidget(qt.QLabel("Threshold:"))
        threshold_layout.addWidget(self.jacobian_slider)
        threshold_layout.addWidget(self.jacobian_slider_label)

        # Create a widget to hold the horizontal layout
        threshold_widget = qt.QWidget()
        threshold_widget.setLayout(threshold_layout)

        # Add the threshold widget to the main QGroupBox layout
        self.jacobian_box.layout().addWidget(threshold_widget)

        # Initially disable the jacobian_box since checkbox is unchecked by default
        self.jacobian_box.setEnabled(False)

        # Add widgets to the form layout
        self.ui.formLayout_2.addWidget(
            self.show_jacobian_checkbox, row, 0, 1, 1)  # Left side
        self.ui.formLayout_2.addWidget(
            self.jacobian_box, row, 1, 2, 2)  # Right side, spans 2 columns

    def _on_show_jacobian_toggled(self) -> None:
        self.jacobian_box.setEnabled(self.show_jacobian_checkbox.checked)

        self.calculate_jacobian()

    def _on_inputs_changed(self, node: Optional[vtk.vtkObject] = None) -> None:
        """React to any input selector change."""

        if not node:
            return

        if not self._are_nodes_selected():
            return

        # if node.GetID() == self.node_fixed.GetID():

        self._update_from_gui()
        if self.show_jacobian_checkbox.isChecked():
            self.update_jacobian = True
            self.calculate_jacobian()

    def calculate_jacobian(self) -> None:

        if self.update_jacobian is False:
            return

        # todo add processing popup
        # todo only calculate when it wasnt calculated or transform changed
        ref = self.node_moving
        new_transform = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLTransformNode")
        tx = self.node_transform
        slicer.modules.transforms.logic().ConvertToGridTransform(tx, ref, new_transform)
        arr = slicer.util.arrayFromGridTransform(new_transform)

        sitk_displacement_field = sitk.GetImageFromArray(arr, isVector=True)
        jacobian_det_volume = sitk.DisplacementFieldJacobianDeterminant(
            sitk_displacement_field)
        jacobian_det_arr = sitk.GetArrayFromImage(jacobian_det_volume)
        self.jacobian_volume = slicer.mrmlScene.CopyNode(ref)
        self.jacobian_volume.SetName("jacobian_node")
        slicer.util.updateVolumeFromArray(
            self.jacobian_volume, jacobian_det_arr)
        self.jacobian_volume.GetDisplayNode().AutoThresholdOn()

        min_val = np.min(jacobian_det_arr)
        max_val = np.max(jacobian_det_arr)

        zero_label = np.round(1 + (0 - min_val) * (255 - 1) /
                              (max_val - min_val)).astype(np.uint8)
        one_label = np.round(1 + (1 - min_val) * (255 - 1) /
                             (max_val - min_val)).astype(np.uint8)

        jacobian_det_arr_label = np.round(
            1 + (jacobian_det_arr - min_val) * (255 - 1) / (max_val - min_val)
        ).astype(np.uint8)
        self.jacobian_label_continuous = slicer.mrmlScene.CopyNode(ref)
        self.jacobian_label_continuous.SetName("jacobian_node_label")
        slicer.util.updateVolumeFromArray(
            self.jacobian_label_continuous, jacobian_det_arr_label)
        label_node = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode")
        label_node.SetName("label_node")
        slicer.modules.volumes.logic().CreateLabelVolumeFromVolume(
            slicer.mrmlScene, label_node, self.jacobian_label_continuous)

        self.node_segmentation_continuous = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode", "Jacobian Segmentation Continuous")
        self.node_segmentation_continuous.CreateDefaultDisplayNodes()
        self.node_segmentation_continuous.SetReferenceImageGeometryParameterFromVolumeNode(
            self.node_moving)
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            label_node, self.node_segmentation_continuous)

        jacobian_det_arr_discrete = np.zeros_like(jacobian_det_arr)
        jacobian_det_arr_discrete[jacobian_det_arr >= 1] = 3
        jacobian_det_arr_discrete[(jacobian_det_arr >= 0) & (
            jacobian_det_arr < 1)] = 2
        jacobian_det_arr_discrete[jacobian_det_arr < 0] = 1
        self.jacobian_label_discrete = slicer.mrmlScene.CopyNode(ref)
        self.jacobian_label_discrete.SetName("jacobian_node_discrete")
        slicer.util.updateVolumeFromArray(
            self.jacobian_label_discrete, jacobian_det_arr_discrete)
        discrete_label_node = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode")
        discrete_label_node.SetName("discrete_label_node")
        slicer.modules.volumes.logic().CreateLabelVolumeFromVolume(
            slicer.mrmlScene, discrete_label_node, self.jacobian_label_discrete)

        self.node_segmentation_discrete = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode", "Jacobian Segmentation")
        self.node_segmentation_discrete.CreateDefaultDisplayNodes()
        self.node_segmentation_discrete.SetReferenceImageGeometryParameterFromVolumeNode(
            self.node_moving)
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            discrete_label_node, self.node_segmentation_discrete)

        self._set_ternary_jacobian_colors(self.node_segmentation_discrete)
        # self._set_continuous_jacobian_colors(self.node_segmentation_continuous,
        #                                      zero_label,
        #                                      one_label)

        self.node_segmentation_discrete.GetDisplayNode().SetVisibility2DOutline(False)
        self.node_segmentation_continuous.GetDisplayNode().SetVisibility2DOutline(False)

        self.update_jacobian = False
        self.jacobian_was_calculated = True

        self.display_jacobian_determinant()

    def display_jacobian_determinant(self) -> None:

        if "continuous" in self.selected_jacobian_modes:
            segmentation_to_display = self.node_segmentation_continuous
        else:
            segmentation_to_display = self.node_segmentation_discrete

        views = self.views_fixed

        # set it as the label volume in the views
        for viewName in views:
            sliceWidget = slicer.app.layoutManager().sliceWidget(viewName)
            sliceLogic = sliceWidget.sliceLogic()
            compositeNode = sliceLogic.GetSliceCompositeNode()
            compositeNode.SetLabelVolumeID(
                segmentation_to_display.GetID())

    def _set_ternary_jacobian_colors(self, seg_node: vtk.vtkMRMLSegmentationNode) -> None:

        seg = seg_node.GetSegmentation()

        names_colors = [
            ("Foldings (<0)", (1.0, 0.0, 0.0)),       # label 1
            ("Shrinkage (0–1)", (1.0, 0.5, 0.0)),     # label 2
            ("Expansion (≥1)", (134/255, 134/255, 255/255)),      # label 3
        ]

        for i, (name, color) in enumerate(names_colors):

            seg_id = seg.GetNthSegmentID(i)
            seg.GetSegment(seg_id).SetName(name)
            seg.GetSegment(seg_id).SetColor(color)

    def _set_continuous_jacobian_colors(
        self,
        seg_node: vtk.vtkMRMLSegmentationNode,
        zero_label: int,
        one_label: int
    ) -> None:

        for i in range(256):
            if i == 0:
                # Background - black or transparent
                color = (0.0, 0.0, 0.0)
                name = "Background (0)"
            elif i == 1:
                # Value 1 = Red
                color = (1.0, 0.0, 0.0)
                name = "Folding (<0)"
            elif i == zero_label:
                # Value zero_label = White
                color = (1.0, 1.0, 1.0)
                name = "Shrinkage (0-1)"
            elif i == 255:
                # Value 255 = Blue
                color = (0.0, 0.0, 1.0)
                name = "Expansion (≥1)"
            else:
                # Interpolate between the key points
                if i < 31:
                    # Interpolate between red (1) and white (31)
                    # Normalized position between 1 and 31
                    t = (i - 1) / (31 - 1)
                    r = 1.0
                    g = t
                    b = t
                    name = "Folding (<0)"
                else:
                    # Interpolate between white (31) and blue (255)
                    # Normalized position between 31 and 255
                    t = (i - 31) / (255 - 31)
                    r = 1.0 - t
                    g = 1.0 - t
                    b = 1.0

                    if i < one_label:
                        name = "Shrinkage (0-1)"
                    else:
                        name = "Expansion (≥1)"

                color = (r, g, b)

            segment = self._get_segment_by_name(seg_node, str(i))

            if not segment:
                continue

            segment.SetName(f"{name} [{i}]")
            segment.SetColor(color)

    def _get_segment_by_name(self, seg_node: vtk.vtkMRMLSegmentationNode, name: str) -> Optional[vtk.vtkSegment]:
        """
        Get a segment by its name from the segmentation node.
        Returns None if the segment is not found.
        """
        seg = seg_node.GetSegmentation()
        for i in range(seg.GetNumberOfSegments()):
            seg_id = seg.GetNthSegmentID(i)
            segment = seg.GetSegment(seg_id)
            if segment.GetName() == name:
                return segment
        return None

    def _add_visualization_widget(self) -> None:
        import LandmarkRegistration
        self.visualization = LandmarkRegistration.RegistrationLib.VisualizationWidget(
            None)
        self.visualization.groupBoxLayout.itemAt(5).widget().hide()
        self.visualization.groupBoxLayout.itemAt(4).widget().hide()
        self.visualization.groupBoxLayout.itemAt(3).widget().hide()
        self.visualization.groupBoxLayout.itemAt(2).widget().hide()

        row: int = self.ui.formLayout_2.rowCount()
        self.ui.formLayout_2.addWidget(
            self.visualization.widget, row, 0, 1, 3)  # spans columns 1–3

        self.visualization.updateVisualization = self.updateVisualization

    def updateVisualization(self):

        self._update_from_gui()

        if self.synchronise_pressed:
            self._set_up_crosshair()

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
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._update_from_gui)

    def onSceneStartClose(self, caller, event) -> None:  # pylint: disable=unused-argument
        """Called just before the scene is closed."""

        self.remove_custom_observers_from_crosshair()

        if self._sceneObserverTag is not None:
            slicer.mrmlScene.RemoveObserver(self._sceneObserverTag)
            self._sceneObserverTag = None

        self.synchronise_pressed = False
        self.ui.synchronise_views_with_transform.setText(
            "Synchronise views (s)")

        self._remove_custom_nodes()

        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:  # pylint: disable=unused-argument
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    @vtk.calldata_type(vtk.VTK_OBJECT)
    def _on_node_added(self, caller, eventid, node) -> None:  # pylint: disable=unused-argument
        """Auto-assign first two added scalar volumes: first->fixed, second->moving."""

        if not isinstance(node, vtkMRMLScalarVolumeNode):
            return

        if self.node_fixed is None:
            self.ui.inputSelector_fixed.setCurrentNode(node)

        if self.node_moving is None or self.node_fixed.GetID() == self.node_moving.GetID():
            if node.GetID() != self.node_fixed.GetID():
                self.ui.inputSelector_moving.setCurrentNode(node)

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode: Optional[registrationViewerParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._update_from_gui)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode,
                             vtk.vtkCommand.ModifiedEvent, self._update_from_gui)
            self._update_from_gui()

    def _update_from_gui(self, caller=None, event=None) -> None:  # pylint: disable=unused-argument

        if not self._are_nodes_selected():
            return

        if self.node_fixed.GetID() == self.node_moving.GetID():
            nodes = [self.node_fixed]
        else:
            nodes = [self.node_fixed, self.node_moving]

        if self.visualization.layoutOption == 'Axi/Sag/Cor':
            _, volume_mapping = self.CompareVolumes_logic.viewersPerVolume(
                volumeNodes=nodes,
                background=None,
                label=None,
                opacity=None,
                returnVolumeViewMapping=True
            )
        else:
            _, volume_mapping = self.CompareVolumes_logic.viewerPerVolume(
                volumeNodes=nodes,
                background=None,
                label=None,
                orientation=self.visualization.layoutOption,
                opacity=None,
                returnVolumeViewMapping=True
            )

        self.views_fixed = volume_mapping.get(
            self.node_fixed.GetID(), []).get("background", [])
        self.views_moving = volume_mapping.get(
            self.node_moving.GetID(), []).get("background", [])
        self.views_all = self.views_fixed + self.views_moving

        for viewName in self.views_all:
            sliceWidget = slicer.app.layoutManager().sliceWidget(viewName)
            compositeNode = sliceWidget.sliceLogic().GetSliceCompositeNode()
            compositeNode.SetLinkedControl(
                self.ui.hotLinkWithCursor_checkbox.checked)
            compositeNode.SetHotLinkedControl(
                self.ui.hotLinkWithCursor_checkbox.checked)

        self.visualization.onZoom("Fit")

    def synchronisation_checks(self) -> bool:
        """
        Internal helper method to validate synchronization prerequisites.
        Returns True if synchronization can proceed, False otherwise.
        """
        if not self._are_nodes_selected():
            slicer.util.errorDisplay(
                "Please select fixed, moving and transformation nodes")
            return False

        if slicer.util.getNode("Crosshair") is None:
            slicer.util.errorDisplay("No crosshair found")
            return False

        if self.node_transform is None:
            slicer.util.errorDisplay("No nonlinear transform found")
            return False

        if self.node_fixed.GetID() == self.node_moving.GetID():
            slicer.util.errorDisplay(
                "Fixed and moving nodes must be different")
            return False

        return True

    def on_synchronise_views(self) -> None:

        if not self.synchronisation_checks():
            return

        self.synchronise_pressed = not self.synchronise_pressed

        if self.synchronise_pressed is True:
            self._set_up_crosshair()
            self.ui.synchronise_views_with_transform.setText(
                "Unsynchronise views (s)")
        else:
            self.remove_custom_observers_from_crosshair()
            self.ui.synchronise_views_with_transform.setText(
                "Synchronise views (s)")

    def _remove_custom_nodes(self) -> None:
        if self.crosshair is not None:
            self.crosshair.delete_crosshairs_and_folder()
            self.crosshair = None

    def _are_nodes_selected(self) -> bool:
        return self.ui.inputSelector_fixed.currentNode() is not None and \
            self.ui.inputSelector_moving.currentNode() is not None and \
            self.ui.inputSelector_transformation.currentNode() is not None

    def _set_up_crosshair(self) -> None:
        if self.crosshair:
            self.remove_custom_observers_from_crosshair()
            self.crosshair.delete_crosshairs_and_folder()
            self.crosshair = None

        self.crosshair = Crosshairs(node_transform=self.node_transform,
                                    views_fixed=self.views_fixed,
                                    views_moving=self.views_moving)

        observer_tag = slicer.util.getNode("Crosshair").AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                                                    self.crosshair.on_mouse_moved_place_crosshair)
        self.crosshair_custom_observer_tags.append(observer_tag)

    def remove_custom_observers_from_crosshair(self) -> None:
        for observer_tag in self.crosshair_custom_observer_tags:
            if slicer.util.getNode("Crosshair"):
                slicer.util.getNode("Crosshair").RemoveObserver(observer_tag)

        self.crosshair_custom_observer_tags.clear()

    def _set_jacobian_mode(self, mode: Literal["Foldings", "Shrinkage", "Expansion", "Continuous"]) -> None:
        """
        Set the jacobian mode for visualization.
        """
        if mode not in self.jacobian_modes:
            raise ValueError(f"Invalid jacobian mode: {mode}")

        current_modes = []

        for m in self.jacobian_modes:
            if self.jacobian_buttons[m].checked:
                current_modes.append(m)

        self.selected_jacobian_modes = current_modes

    def _on_jacobian_slider_changed(self, value):
        # Convert slider value (0-100) to float (0.0-1.0)
        float_value = value / 100.0

        # Update the label to show current value
        self.jacobian_slider_label.setText(f"{float_value:.2f}")

        # Your callback logic here
        print(f"Jacobian slider value changed to: {float_value}")
        # Add your actual processing code here

    @property
    def node_fixed(self) -> Any:
        return self.ui.inputSelector_fixed.currentNode()

    @property
    def node_moving(self) -> Any:
        return self.ui.inputSelector_moving.currentNode()

    @property
    def node_transform(self) -> Any:
        return self.ui.inputSelector_transformation.currentNode()

    @staticmethod
    def apply_red_white_blue_lookup_table(volume_node, zero_label: int) -> None:
        import vtk
        import numpy as np

        # Create a vtkLookupTable for custom colors
        lookup_table = vtk.vtkLookupTable()
        lookup_table.SetNumberOfTableValues(256)  # 256 colors
        lookup_table.SetRange(0, 255)  # Changed to match your discrete range
        lookup_table.Build()

        # Populate the lookup table with custom color mapping
        for i in range(256):
            if i == 0:
                # Background - black or transparent
                lookup_table.SetTableValue(i, 0.0, 0.0, 0.0, 1.0)
            elif i == 1:
                # Value 1 = Red
                lookup_table.SetTableValue(i, 1.0, 0.0, 0.0, 1.0)
            elif i == zero_label:
                # Value 31 = White
                lookup_table.SetTableValue(i, 1.0, 1.0, 1.0, 1.0)
            elif i == 255:
                # Value 255 = Blue
                lookup_table.SetTableValue(i, 0.0, 0.0, 1.0, 1.0)
            else:
                # Interpolate between the key points
                if i < 31:
                    # Interpolate between red (1) and white (31)
                    # Normalized position between 1 and 31
                    t = (i - 1) / (31 - 1)
                    r = 1.0
                    g = t
                    b = t
                else:
                    # Interpolate between white (31) and blue (255)
                    # Normalized position between 31 and 255
                    t = (i - 31) / (255 - 31)
                    r = 1.0 - t
                    g = 1.0 - t
                    b = 1.0

                lookup_table.SetTableValue(i, r, g, b, 1.0)

        # Create a vtkMRMLColorTableNode and set the lookup table
        color_table_node = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLColorTableNode", "RedWhiteBlueColorTable")
        color_table_node.SetAndObserveLookupTable(lookup_table)

        # Get the display node for the volume
        display_node = volume_node.GetDisplayNode()
        if not display_node:
            display_node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLScalarVolumeDisplayNode")
            volume_node.SetAndObserveDisplayNodeID(display_node.GetID())

        # Assign the color table to the display node
        display_node.SetAndObserveColorNodeID(color_table_node.GetID())

    @staticmethod
    def apply_three_color_labelmap(volume_node) -> None:
        import vtk

        # Create a vtkLookupTable for the labelmap
        lookup_table = vtk.vtkLookupTable()
        lookup_table.SetNumberOfTableValues(3)  # Only 3 colors needed
        lookup_table.SetRange(0, 2)  # Range from 0 to 2
        lookup_table.Build()

        # Set the three specific colors
        lookup_table.SetTableValue(0, 1.0, 0.0, 0.0, 1.0)  # Value 0 = Red
        lookup_table.SetTableValue(1, 1.0, 0.5, 0.0, 1.0)  # Value 1 = Orange
        lookup_table.SetTableValue(2, 0.0, 0.0, 1.0, 1.0)  # Value 2 = Blue

        # Create a vtkMRMLColorTableNode and set the lookup table
        color_table_node = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLColorTableNode", "ThreeColorLabelMap")
        color_table_node.SetAndObserveLookupTable(lookup_table)

        # Convert volume to labelmap if it isn't already
        if not volume_node.GetClassName() == "vtkMRMLLabelMapVolumeNode":
            # Create new labelmap node
            labelmap_node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLabelMapVolumeNode")
            labelmap_node.SetName(volume_node.GetName() + "_LabelMap")
            labelmap_node.Copy(volume_node)
            labelmap_node.SetLabelMap(True)
        else:
            labelmap_node = volume_node

        # Get or create display node for the labelmap
        display_node = labelmap_node.GetDisplayNode()
        if not display_node:
            display_node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLabelMapVolumeDisplayNode")
            labelmap_node.SetAndObserveDisplayNodeID(display_node.GetID())

        # Assign the color table to the display node
        display_node.SetAndObserveColorNodeID(color_table_node.GetID())


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

        start_time = time.time()
        logging.info("Processing started")

        # print(f"Volume name: {inputVolume.GetName()}")

        stop_time = time.time()
        logging.info(
            "Processing completed in %.2f seconds", stop_time-start_time)


class Crosshairs():

    """
    Class to handle crosshairs for each view
    """

    def __init__(self,
                 node_transform: slicer.vtkMRMLGridTransformNode,
                 views_fixed: List[str],
                 views_moving: List[str]
                 ) -> None:

        self.node_transform = node_transform

        self.reverse_transf_direction = False

        self.views_fixed = views_fixed
        self.views_moving = views_moving
        self.views_all = views_fixed + views_moving

        self.create_crosshairs_and_folder()

    def create_crosshairs_and_folder(self) -> None:

        self.crosshair_nodes = {
            view: self.create_crosshair(view) for view in self.views_all
        }

        # create a folder to put the crosshairs in
        self.sh_node = slicer.mrmlScene.GetSubjectHierarchyNode()
        self.crosshair_folder_id = self.sh_node.CreateFolderItem(
            self.sh_node.GetSceneItemID(), "crosshairs")

        for crosshair_node in self.crosshair_nodes.values():
            self.sh_node.SetItemParent(self.sh_node.GetItemByDataNode(
                crosshair_node), self.crosshair_folder_id)

        # collapse folder
        self.sh_node.SetItemExpanded(self.crosshair_folder_id, False)

    def delete_crosshairs_and_folder(self) -> None:
        """
        Delete the crosshairs and the folder.
        """

        for node in self.crosshair_nodes.values():
            slicer.mrmlScene.RemoveNode(node)

        self.sh_node.RemoveItem(self.crosshair_folder_id)

    @staticmethod
    def create_crosshair(view: str) -> slicer.vtkMRMLMarkupsFiducialNode:
        """
        Create a crosshair in the given views.
        """

        crosshair_node = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsFiducialNode")
        crosshair_node.SetName("")

        crosshair_node.AddControlPoint(0, 0, 0, "")
        crosshair_node.SetNthControlPointLabel(0, "")
        crosshair_node.GetDisplayNode().SetGlyphScale(1)

        crosshair_node.LockedOn()

        crosshair_node.GetDisplayNode().SetViewNodeIDs([
            slicer.app.layoutManager().sliceWidget(view).mrmlSliceNode().GetID()
        ])

        return crosshair_node

    def place_crosshair_with_transformation(
        self,
        views: List[str],
        crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
        reverse_transf_direction: bool
    ) -> None:
        """
        Places the crosshair in the current view and transforms it to the new position.
        """

        initial_position: list[float] = [0., 0., 0.]
        slicer.util.getNode("Crosshair").GetCursorPositionRAS(initial_position)

        # now we set the position of our crosshair and then transform it to the new position
        self.set_crosshair_nodes_to_position(crosshair_nodes,
                                             initial_position)

        # now transform the crosshair to the new position
        self.transform_crosshair_nodes(crosshair_nodes,
                                       not reverse_transf_direction)

        new_position: List[float] = [0., 0., 0.]
        crosshair_nodes[0].GetNthControlPointPositionWorld(0,
                                                           new_position)

        for view in views:
            self.set_offset_to_ras(new_position, view)

        self.set_crosshair_visibility()

        self.set_crosshair_nodes_to_position(crosshair_nodes,
                                             new_position)

    def place_crosshair_without_transformation(
        self,
        views: List[str],
        crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
    ) -> None:

        initial_position: list[float] = [0., 0., 0.]
        slicer.util.getNode("Crosshair").GetCursorPositionRAS(initial_position)

        self.set_crosshair_visibility()

        self.set_crosshair_nodes_to_position(crosshair_nodes,
                                             initial_position)

        # only jump the *other* slice views in this group; leave the active view’s slice unchanged
        for view in views:
            if view == self.get_cursor_view_name():
                continue

            self.set_offset_to_ras(initial_position, view)

    def on_mouse_moved_place_crosshair(self, observer, eventid) -> None:  # pylint: disable=unused-argument
        """
        When the mouse moves in a view, the crosshair should follow the cursor.

        """
        current_view = self.get_cursor_view_name()

        if current_view in self.views_fixed:
            self.place_crosshair_without_transformation(views=self.views_fixed,
                                                        crosshair_nodes=self.crosshairs_1)
            self.place_crosshair_with_transformation(views=self.views_moving,
                                                     crosshair_nodes=self.crosshairs_2,
                                                     reverse_transf_direction=self.reverse_transf_direction)

        elif current_view in self.views_moving:
            self.place_crosshair_with_transformation(views=self.views_fixed,
                                                     crosshair_nodes=self.crosshairs_1,
                                                     reverse_transf_direction=not self.reverse_transf_direction)
            self.place_crosshair_without_transformation(views=self.views_moving,
                                                        crosshair_nodes=self.crosshairs_2)

    def transform_crosshair_nodes(self,
                                  crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
                                  invert: bool) -> None:
        """
        Transform every crosshair from the list of nodes with the current transformation.
        """

        if not self.node_transform:
            print("No transformation available")
            return

        for node in crosshair_nodes:
            transform = (self.node_transform.GetTransformFromParent()
                         if invert
                         else self.node_transform.GetTransformToParent())
            node.ApplyTransform(transform)

    def _set_node_visibility(self, node: slicer.vtkMRMLMarkupsFiducialNode, visibility: bool) -> None:
        """Helper method to set visibility of a crosshair node."""
        display_node = node.GetDisplayNode()
        if display_node is not None:
            display_node.SetVisibility(visibility)

    @staticmethod
    def set_crosshair_nodes_to_position(crosshair_nodes: list[slicer.vtkMRMLMarkupsFiducialNode],
                                        position: list[float]) -> None:
        """
        Set every crosshair from the list of nodes to the given position.
        """

        for node in crosshair_nodes:
            node.SetNthControlPointPositionWorld(0, *position)

    def set_crosshair_visibility_in_views(self, views: list[str], visibility: bool) -> None:
        """
        Hide the crosshair in the given views.
        """

        for view in views:
            if view in self.crosshair_nodes:
                self._set_node_visibility(
                    self.crosshair_nodes[view], visibility)

    def set_crosshair_visibility(self) -> None:
        """
        Turns off the crosshair in the current view
        """

        for node in self.crosshair_nodes.values():
            self._set_node_visibility(node, True)

        current_view = self.get_cursor_view_name()
        if current_view in self.crosshair_nodes:
            self._set_node_visibility(
                self.crosshair_nodes[current_view], False)

    @staticmethod
    def get_cursor_view_name() -> str:
        """
        Get the name of the view where the cursor is currently located.
        """
        node_crosshair = slicer.util.getNode("Crosshair")

        if node_crosshair is None:
            return ""

        position = node_crosshair.GetCursorPositionXYZ([0]*3)

        if position is not None:
            return position.GetName()

        return ""

    @staticmethod
    def set_offset_to_ras(position_ras: List[float], view: str) -> None:
        """Set the view offset based on RAS position."""
        slice_logic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
        slice_node = slice_logic.GetSliceNode()

        # Get the SliceToRAS matrix for the current slice view
        slice_to_ras = slice_node.GetSliceToRAS()

        # The third column of the SliceToRAS matrix is the slice normal
        normal = [slice_to_ras.GetElement(i, 2) for i in range(3)]

        # Compute the offset as the dot product of the slice normal with the target RAS position
        offset = sum(normal[i] * position_ras[i] for i in range(3))

        # Set the computed offset for this view
        slice_logic.GetSliceNode().SetSliceOffset(offset)

    @property
    def crosshairs_1(self) -> list[slicer.vtkMRMLMarkupsFiducialNode]:

        try:
            a = [self.crosshair_nodes[view] for view in self.views_fixed]
        except KeyError as e:
            print(
                f"we only have {self.crosshair_nodes.keys()} crosshairs, but tried to access {self.views_fixed}")
            a = []
        return a

    @property
    def crosshairs_2(self) -> list[slicer.vtkMRMLMarkupsFiducialNode]:
        try:
            b = [self.crosshair_nodes[view] for view in self.views_moving]
        except KeyError as e:
            print(
                f"we only have {self.crosshair_nodes.keys()} crosshairs, but tried to access {self.views_moving}")
            b = []
        return b
