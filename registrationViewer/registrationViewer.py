from __future__ import annotations

import logging
from typing import Any, Optional

import qt
import slicer
import slicer.util
import vtk
from slicer import vtkMRMLScalarVolumeNode, vtkMRMLTransformNode
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleWidget,
)
from slicer.util import VTKObservationMixin


CUSTOM_LAYOUT_ID = 501
CUSTOM_LAYOUT_XML = """
<layout type="vertical" split="true">
  <item>
    <layout type="horizontal" split="true">
      <item><view class="vtkMRMLSliceNode" singletontag="Axial_Moving"><property name="orientation" action="default">Axial</property><property name="viewlabel" action="default">1</property><property name="viewcolor" action="default">#e86a58</property></view></item>
      <item><view class="vtkMRMLSliceNode" singletontag="Axial_Warped"><property name="orientation" action="default">Axial</property><property name="viewlabel" action="default">2</property><property name="viewcolor" action="default">#e8a558</property></view></item>
      <item><view class="vtkMRMLSliceNode" singletontag="Axial_Jacobian"><property name="orientation" action="default">Axial</property><property name="viewlabel" action="default">3</property><property name="viewcolor" action="default">#e8e858</property></view></item>
      <item><view class="vtkMRMLSliceNode" singletontag="Axial_Displacement"><property name="orientation" action="default">Axial</property><property name="viewlabel" action="default">4</property><property name="viewcolor" action="default">#58e86a</property></view></item>
    </layout>
  </item>
  <item>
    <layout type="horizontal" split="true">
      <item><view class="vtkMRMLSliceNode" singletontag="Coronal_Moving"><property name="orientation" action="default">Coronal</property><property name="viewlabel" action="default">5</property><property name="viewcolor" action="default">#58e8e8</property></view></item>
      <item><view class="vtkMRMLSliceNode" singletontag="Coronal_Warped"><property name="orientation" action="default">Coronal</property><property name="viewlabel" action="default">6</property><property name="viewcolor" action="default">#5858e8</property></view></item>
      <item><view class="vtkMRMLSliceNode" singletontag="Coronal_Jacobian"><property name="orientation" action="default">Coronal</property><property name="viewlabel" action="default">7</property><property name="viewcolor" action="default">#a558e8</property></view></item>
      <item><view class="vtkMRMLSliceNode" singletontag="Coronal_Displacement"><property name="orientation" action="default">Coronal</property><property name="viewlabel" action="default">8</property><property name="viewcolor" action="default">#e858e8</property></view></item>
    </layout>
  </item>
</layout>
"""


class registrationViewer(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("registrationViewer")
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Registration")]
        self.parent.dependencies = []
        self.parent.contributors = ["Fryderyk Kögl (TUM)"]
        self.parent.helpText = _("Custom viewer for registration results. See more information in documentation.")
        self.parent.acknowledgementText = _("Developed by Fryderyk Kögl (TUM).")


class registrationViewerWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None) -> None:
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None
        self._sceneObserverTag = None
        self.selectors = {}

    def setup(self) -> None:
        ScriptedLoadableModuleWidget.setup(self)

        layoutManager = slicer.app.layoutManager()
        if not layoutManager.layoutLogic().GetLayoutNode().IsLayoutDescription(CUSTOM_LAYOUT_ID):
            layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(CUSTOM_LAYOUT_ID, CUSTOM_LAYOUT_XML)
        else:
            layoutManager.layoutLogic().GetLayoutNode().SetLayoutDescription(CUSTOM_LAYOUT_ID, CUSTOM_LAYOUT_XML)

        self.logic = registrationViewerLogic()

        # Create UI from Python
        parametersCollapsibleButton = slicer.qMRMLCollapsibleButton()
        parametersCollapsibleButton.text = "Nodes"
        self.layout.addWidget(parametersCollapsibleButton)

        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)
        
        # Configure Dropdowns
        self._add_node_selector(parametersFormLayout, "fixed_sag", "Fixed (Sagittal)", ["vtkMRMLScalarVolumeNode"])
        self._add_node_selector(parametersFormLayout, "moving_ax", "Moving (Axial)", ["vtkMRMLScalarVolumeNode"])
        self._add_node_selector(parametersFormLayout, "moving_cor", "Moving (Coronal)", ["vtkMRMLScalarVolumeNode"])
        self._add_node_selector(parametersFormLayout, "warped_ax", "Warped (Axial)", ["vtkMRMLScalarVolumeNode"])
        self._add_node_selector(parametersFormLayout, "warped_cor", "Warped (Coronal)", ["vtkMRMLScalarVolumeNode"])
        self._add_node_selector(parametersFormLayout, "jacobian_ax", "Jacobian (Axial)", ["vtkMRMLScalarVolumeNode"])
        self._add_node_selector(parametersFormLayout, "jacobian_cor", "Jacobian (Coronal)", ["vtkMRMLScalarVolumeNode"])
        # Transforms for displacement fields
        self._add_node_selector(parametersFormLayout, "displacement_ax", "Displacement (Axial)", ["vtkMRMLTransformNode"])
        self._add_node_selector(parametersFormLayout, "displacement_cor", "Displacement (Coronal)", ["vtkMRMLTransformNode"])

        self.applyButton = qt.QPushButton("Update Views")
        self.applyButton.toolTip = "Assign selected nodes to views in the 8-up layout."
        self.applyButton.clicked.connect(self.onApplyButton)
        parametersFormLayout.addRow(self.applyButton)

        self.layout.addStretch(1)

        if self._sceneObserverTag is None:
            self._sceneObserverTag = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent, self._on_node_added)

        self._auto_select_existing_scene_nodes()
        self.onApplyButton()

    def _add_node_selector(self, layout, name, label, nodeTypes):
        selector = slicer.qMRMLNodeComboBox()
        selector.nodeTypes = nodeTypes
        selector.selectNodeUponCreation = True
        selector.addEnabled = False
        selector.removeEnabled = False
        selector.noneEnabled = True
        selector.showHidden = False
        selector.showChildNodeTypes = True
        selector.setMRMLScene(slicer.mrmlScene)
        selector.setToolTip(f"Pick the {label} node.")
        layout.addRow(label + ":", selector)
        self.selectors[name] = selector

    def _on_node_added(self, caller, eventid, node) -> None:
        pass # we can skip auto selection for simplicity, or implement later

    def _auto_select_existing_scene_nodes(self) -> None:
        pass # Optional auto-selection could go here

    def cleanup(self) -> None:
        if self._sceneObserverTag is not None:
            slicer.mrmlScene.RemoveObserver(self._sceneObserverTag)
            self._sceneObserverTag = None

    def onApplyButton(self) -> None:
        slicer.app.layoutManager().setLayout(CUSTOM_LAYOUT_ID)
        slicer.app.processEvents()

        # Dictionary of view tag to foreground, background, labelmap volumes, etc.
        # Column 1: moving (Background)
        # Column 2: fixed (Background), warped moving (Foreground)
        # Column 3: jacobian (Background)
        # Column 4: displacement (We can set the transform to the slice logic but actually slice views just show it if 
        #           it's enabled in Transforms module. Alternatively, if displacement is loaded as volume, we would set
        #           it as background. I will set the slice composite nodes first.)

        view_assignments = {
            "Axial_Moving": {"Background": self.selectors["moving_ax"].currentNode()},
            "Axial_Warped": {"Background": self.selectors["fixed_sag"].currentNode(), "Foreground": self.selectors["warped_ax"].currentNode()},
            "Axial_Jacobian": {"Background": self.selectors["jacobian_ax"].currentNode()},
            "Axial_Displacement": {}, # Volume assignment not needed if using transforms, handled via Slicer Transforms
            "Coronal_Moving": {"Background": self.selectors["moving_cor"].currentNode()},
            "Coronal_Warped": {"Background": self.selectors["fixed_sag"].currentNode(), "Foreground": self.selectors["warped_cor"].currentNode()},
            "Coronal_Jacobian": {"Background": self.selectors["jacobian_cor"].currentNode()},
            "Coronal_Displacement": {},
        }
        
        # We need to manually add the slice nodes if they are missing (usually layout manager does it)
        layoutManager = slicer.app.layoutManager()
        for view_name, assignment in view_assignments.items():
            slice_widget = layoutManager.sliceWidget(view_name)
            if slice_widget is None:
                continue
            
            slice_logic = slice_widget.sliceLogic()
            composite_node = slice_logic.GetSliceCompositeNode()
            if not composite_node:
                continue

            bg_node = assignment.get("Background")
            fg_node = assignment.get("Foreground")
            
            composite_node.SetBackgroundVolumeID(bg_node.GetID() if bg_node else "")
            composite_node.SetForegroundVolumeID(fg_node.GetID() if fg_node else "")

            # Set 50% opacity for foreground to see both
            if fg_node:
                composite_node.SetForegroundOpacity(0.5)

        # To show transform grids (displacement fields) in slice views, we can use the Transform display nodes
        for axis, transform_key, view_name in [("Axial", "displacement_ax", "Axial_Displacement"), 
                                               ("Coronal", "displacement_cor", "Coronal_Displacement")]:
            transform_node = self.selectors[transform_key].currentNode()
            if transform_node:
                display_node = transform_node.GetDisplayNode()
                if not display_node:
                    slicer.mrmlScene.AddNode(slicer.vtkMRMLTransformDisplayNode())
                    transform_node.CreateDefaultDisplayNodes()
                    display_node = transform_node.GetDisplayNode()
                
                if display_node:
                    # Enable grid or contour visualization on slice viewers
                    display_node.SetVisibility2D(True)
                    slice_widget = layoutManager.sliceWidget(view_name)
                    if slice_widget is not None:
                        slice_node = slice_widget.mrmlSliceNode()
                        if slice_node:
                            display_node.AddViewNodeID(slice_node.GetID())


class registrationViewerLogic(ScriptedLoadableModuleLogic):
    def __init__(self) -> None:
        ScriptedLoadableModuleLogic.__init__(self)

