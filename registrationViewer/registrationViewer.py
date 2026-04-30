from __future__ import annotations

import os
import tempfile

import qt
import SimpleITK as sitk
import sitkUtils
import slicer
import slicer.util
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
        self.parent.categories = [
            translate("qSlicerAbstractCoreModule", "Registration")
        ]
        self.parent.dependencies = []
        self.parent.contributors = ["Fryderyk Kögl (TUM)"]
        self.parent.helpText = _(
            "Custom viewer for registration results. See more information in documentation."
        )
        self.parent.acknowledgementText = _("Developed by Fryderyk Kögl (TUM).")


class registrationViewerWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None) -> None:
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None
        self._sceneObserverTag = None
        self.selectors = {}

    def enter(self) -> None:
        self.onApplyButton()

    def setup(self) -> None:
        ScriptedLoadableModuleWidget.setup(self)

        layoutManager = slicer.app.layoutManager()
        if (
            not layoutManager.layoutLogic()
            .GetLayoutNode()
            .IsLayoutDescription(CUSTOM_LAYOUT_ID)
        ):
            layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(
                CUSTOM_LAYOUT_ID, CUSTOM_LAYOUT_XML
            )
        else:
            layoutManager.layoutLogic().GetLayoutNode().SetLayoutDescription(
                CUSTOM_LAYOUT_ID, CUSTOM_LAYOUT_XML
            )

        self.logic = registrationViewerLogic()

        # Create UI from Python
        parametersCollapsibleButton = slicer.qMRMLCollapsibleButton()
        parametersCollapsibleButton.text = "Nodes"
        self.layout.addWidget(parametersCollapsibleButton)

        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        # Configure Dropdowns
        self._add_node_selector(
            parametersFormLayout,
            "fixed_sag",
            "Fixed (Sagittal)",
            ["vtkMRMLScalarVolumeNode"],
        )
        self._add_node_selector(
            parametersFormLayout,
            "moving_ax",
            "Moving (Axial)",
            ["vtkMRMLScalarVolumeNode"],
        )
        self._add_node_selector(
            parametersFormLayout,
            "moving_cor",
            "Moving (Coronal)",
            ["vtkMRMLScalarVolumeNode"],
        )
        self._add_node_selector(
            parametersFormLayout,
            "warped_ax",
            "Warped (Axial)",
            ["vtkMRMLScalarVolumeNode"],
        )
        self._add_node_selector(
            parametersFormLayout,
            "warped_cor",
            "Warped (Coronal)",
            ["vtkMRMLScalarVolumeNode"],
        )
        self._add_node_selector(
            parametersFormLayout,
            "jacobian_ax",
            "Jacobian (Axial)",
            ["vtkMRMLScalarVolumeNode"],
        )
        self._add_node_selector(
            parametersFormLayout,
            "jacobian_cor",
            "Jacobian (Coronal)",
            ["vtkMRMLScalarVolumeNode"],
        )
        # Transforms for displacement fields
        self._add_node_selector(
            parametersFormLayout,
            "displacement_axi",
            "Displacement (Axial)",
            ["vtkMRMLTransformNode"],
        )
        self._add_node_selector(
            parametersFormLayout,
            "displacement_cor",
            "Displacement (Coronal)",
            ["vtkMRMLTransformNode"],
        )

        self.applyButton = qt.QPushButton("Update Views")
        self.applyButton.toolTip = "Assign selected nodes to views in the 8-up layout."
        self.applyButton.clicked.connect(self.onApplyButton)
        parametersFormLayout.addRow(self.applyButton)

        self.linkButton = qt.QPushButton("Hot Link Views")
        self.linkButton.toolTip = (
            "Link all views so scrolling and zooming are synchronized."
        )
        self.linkButton.setCheckable(True)
        self.linkButton.clicked.connect(self.onLinkButton)
        parametersFormLayout.addRow(self.linkButton)

        self.layout.addStretch(1)

        if self._sceneObserverTag is None:
            self._sceneObserverTag = slicer.mrmlScene.AddObserver(
                slicer.mrmlScene.NodeAddedEvent, self._on_node_added
            )

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
        self._try_auto_select_node(node)

    def _auto_select_existing_scene_nodes(self) -> None:
        for i in range(slicer.mrmlScene.GetNumberOfNodes()):
            self._try_auto_select_node(slicer.mrmlScene.GetNthNode(i))

    def _try_auto_select_node(self, node) -> None:
        if not node:
            return
        name = node.GetName()
        if not name:
            return

        mapping = {
            "sag": "fixed_sag",
            "axi": "moving_ax",
            "cor": "moving_cor",
            "warped_axi": "warped_ax",
            "warped_cor": "warped_cor",
            "jacob_axi": "jacobian_ax",
            "jacob_cor": "jacobian_cor",
            "disp_axi": "displacement_axi",
            "disp_cor": "displacement_cor",
        }

        # Check if exact name match exists in our predefined list map
        if name in mapping:
            selector = self.selectors.get(mapping[name])
            if selector and not selector.currentNode():
                selector.setCurrentNode(node)

    def cleanup(self) -> None:
        if self._sceneObserverTag is not None:
            slicer.mrmlScene.RemoveObserver(self._sceneObserverTag)
            self._sceneObserverTag = None

    def _generate_warped_grid(
        self,
        displacement_node: slicer.vtkMRMLScalarVolumeNode,
        result_node_name: str,
        through_plane_axis: int = 0,
        grid_spacing_vox: int = 10,
        upsample_factor: int = 2,
    ) -> slicer.vtkMRMLScalarVolumeNode:
        if displacement_node is None:
            return None

        with tempfile.NamedTemporaryFile(suffix=".nii.gz", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            slicer.util.saveNode(displacement_node, tmp_path)
            disp_sitk = sitk.ReadImage(tmp_path)
        finally:
            os.unlink(tmp_path)

        orig_spacing = disp_sitk.GetSpacing()
        orig_size = disp_sitk.GetSize()
        new_spacing = tuple(s / upsample_factor for s in orig_spacing)
        new_size = tuple(int(sz * upsample_factor) for sz in orig_size)

        grid_sitk = sitk.Image(new_size[0], new_size[1], new_size[2], sitk.sitkFloat32)
        grid_sitk.SetSpacing(new_spacing)
        grid_sitk.SetOrigin(disp_sitk.GetOrigin())
        grid_sitk.SetDirection(disp_sitk.GetDirection())

        grid_array = sitk.GetArrayFromImage(grid_sitk)
        hr_step = grid_spacing_vox * upsample_factor
        axes = [0, 1, 2]
        axes.remove(through_plane_axis)
        for ax in axes:
            idx = [slice(None), slice(None), slice(None)]
            idx[ax] = slice(None, None, hr_step)
            grid_array[tuple(idx)] = 1.0
        grid_sitk = sitk.GetImageFromArray(grid_array)
        grid_sitk.SetSpacing(new_spacing)
        grid_sitk.SetOrigin(disp_sitk.GetOrigin())
        grid_sitk.SetDirection(disp_sitk.GetDirection())

        result_node = slicer.mrmlScene.GetFirstNodeByName(result_node_name)
        if result_node is None:
            result_node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLScalarVolumeNode", result_node_name
            )
        sitkUtils.PushVolumeToSlicer(grid_sitk, result_node)

        # Let Slicer apply the deformation at render time — no manual warping needed
        result_node.SetAndObserveTransformNodeID(displacement_node.GetID())

        return result_node

    def onLinkButton(self, checked: bool) -> None:
        layoutManager = slicer.app.layoutManager()
        view_names = [
            "Axial_Moving",
            "Axial_Warped",
            "Axial_Jacobian",
            "Axial_Displacement",
            "Coronal_Moving",
            "Coronal_Warped",
            "Coronal_Jacobian",
            "Coronal_Displacement",
        ]
        for view_name in view_names:
            slice_widget = layoutManager.sliceWidget(view_name)
            if slice_widget is not None:
                composite_node = slice_widget.sliceLogic().GetSliceCompositeNode()
                if composite_node:
                    composite_node.SetLinkedControl(checked)
                    if hasattr(composite_node, "SetHotLinkedControl"):
                        composite_node.SetHotLinkedControl(checked)

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
            "Axial_Moving": {
                "Background": self.selectors["moving_ax"].currentNode(),
                "Foreground": self.selectors["warped_ax"].currentNode(),
            },
            "Axial_Warped": {
                "Background": self.selectors["fixed_sag"].currentNode(),
                "Foreground": self.selectors["warped_ax"].currentNode(),
            },
            "Axial_Jacobian": {
                "Background": self.selectors["jacobian_ax"].currentNode()
            },
            "Axial_Displacement": {},  # Volume assignment not needed if using transforms, handled via Slicer Transforms
            "Coronal_Moving": {
                "Background": self.selectors["moving_cor"].currentNode(),
                "Foreground": self.selectors["warped_cor"].currentNode(),
            },
            "Coronal_Warped": {
                "Background": self.selectors["fixed_sag"].currentNode(),
                "Foreground": self.selectors["warped_cor"].currentNode(),
            },
            "Coronal_Jacobian": {
                "Background": self.selectors["jacobian_cor"].currentNode()
            },
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

        # Generate warped grid volumes and assign as plain background volumes
        # to the displacement panels — fully per-view controllable like every other column
        for transform_key, view_name, node_name, through_plane_axis in [
            ("displacement_axi", "Axial_Displacement", "warped_grid_ax", 0),
            ("displacement_cor", "Coronal_Displacement", "warped_grid_cor", 1),
        ]:
            warped_grid = self._generate_warped_grid(
                self.selectors[transform_key].currentNode(),
                node_name,
                through_plane_axis=through_plane_axis,
            )
            slice_widget = layoutManager.sliceWidget(view_name)
            if slice_widget is None:
                continue
            composite_node = slice_widget.sliceLogic().GetSliceCompositeNode()
            if composite_node:
                composite_node.SetBackgroundVolumeID(
                    warped_grid.GetID() if warped_grid else ""
                )

        # Reset field of view to fit the loaded/assigned volumes
        slicer.util.resetSliceViews()


class registrationViewerLogic(ScriptedLoadableModuleLogic):
    def __init__(self) -> None:
        ScriptedLoadableModuleLogic.__init__(self)
