from __future__ import annotations

from typing import List

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

CUSTOM_LAYOUT_ID_NO_DISP = 502
CUSTOM_LAYOUT_XML_NO_DISP = """
<layout type="vertical" split="true">
  <item>
    <layout type="horizontal" split="true">
      <item><view class="vtkMRMLSliceNode" singletontag="Axial_Moving"><property name="orientation" action="default">Axial</property><property name="viewlabel" action="default">1</property><property name="viewcolor" action="default">#e86a58</property></view></item>
      <item><view class="vtkMRMLSliceNode" singletontag="Axial_Warped"><property name="orientation" action="default">Axial</property><property name="viewlabel" action="default">2</property><property name="viewcolor" action="default">#e8a558</property></view></item>
      <item><view class="vtkMRMLSliceNode" singletontag="Axial_Jacobian"><property name="orientation" action="default">Axial</property><property name="viewlabel" action="default">3</property><property name="viewcolor" action="default">#e8e858</property></view></item>
    </layout>
  </item>
  <item>
    <layout type="horizontal" split="true">
      <item><view class="vtkMRMLSliceNode" singletontag="Coronal_Moving"><property name="orientation" action="default">Coronal</property><property name="viewlabel" action="default">5</property><property name="viewcolor" action="default">#58e8e8</property></view></item>
      <item><view class="vtkMRMLSliceNode" singletontag="Coronal_Warped"><property name="orientation" action="default">Coronal</property><property name="viewlabel" action="default">6</property><property name="viewcolor" action="default">#5858e8</property></view></item>
      <item><view class="vtkMRMLSliceNode" singletontag="Coronal_Jacobian"><property name="orientation" action="default">Coronal</property><property name="viewlabel" action="default">7</property><property name="viewcolor" action="default">#a558e8</property></view></item>
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
        self._disp_checkboxes = {}

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

        if (
            not layoutManager.layoutLogic()
            .GetLayoutNode()
            .IsLayoutDescription(CUSTOM_LAYOUT_ID_NO_DISP)
        ):
            layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(
                CUSTOM_LAYOUT_ID_NO_DISP, CUSTOM_LAYOUT_XML_NO_DISP
            )
        else:
            layoutManager.layoutLogic().GetLayoutNode().SetLayoutDescription(
                CUSTOM_LAYOUT_ID_NO_DISP, CUSTOM_LAYOUT_XML_NO_DISP
            )

        self.logic = registrationViewerLogic()

        parametersCollapsibleButton = slicer.qMRMLCollapsibleButton()
        parametersCollapsibleButton.text = "Nodes"
        self.layout.addWidget(parametersCollapsibleButton)

        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

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

        self._add_vis_widget(self.layout)
        self._add_checkerboard_widget(self.layout)
        self._add_disp_widget(self.layout)

        self.layout.addStretch(1)

        if self._sceneObserverTag is None:
            self._sceneObserverTag = slicer.mrmlScene.AddObserver(
                slicer.mrmlScene.NodeAddedEvent, self._on_node_added
            )

        self._auto_select_existing_scene_nodes()
        self.onApplyButton()

    def _add_vis_widget(self, layout):
        import LandmarkRegistration

        self.visualization = LandmarkRegistration.RegistrationLib.VisualizationWidget(
            None
        )
        layout.addWidget(self.visualization.widget)

        self.visualization.groupBoxLayout.itemAt(0).widget().hide()
        self.visualization.groupBoxLayout.itemAt(1).widget().hide()
        self.visualization.groupBoxLayout.itemAt(2).widget().hide()
        self.visualization.groupBoxLayout.itemAt(3).widget().hide()

        # Orientation buttons
        btnLayout = qt.QHBoxLayout()
        btnAxi = qt.QPushButton("Axi")
        btnCor = qt.QPushButton("Cor")
        btnSag = qt.QPushButton("Sag")
        btnAxi.clicked.connect(lambda: self.set_all_views_orientation("Axial"))
        btnCor.clicked.connect(lambda: self.set_all_views_orientation("Coronal"))
        btnSag.clicked.connect(lambda: self.set_all_views_orientation("Sagittal"))
        btnLayout.addWidget(btnAxi)
        btnLayout.addWidget(btnCor)
        btnLayout.addWidget(btnSag)
        self.visualization.groupBoxLayout.insertRow(1, btnLayout)

    def _add_disp_widget(self, layout):
        self.dispCollapsibleButton = slicer.qMRMLCollapsibleButton()
        self.dispCollapsibleButton.text = "Displacement"
        layout.addWidget(self.dispCollapsibleButton)
        dispFormLayout = qt.QFormLayout(self.dispCollapsibleButton)

        # Displacement visibility checkboxes
        dispLayout = qt.QHBoxLayout()
        for name, checked in [
            ("Fixed", False),
            ("Warped", False),
            ("Jacobian", False),
            ("Transform", True),
        ]:
            cb = qt.QCheckBox(name)
            cb.setChecked(checked)
            cb.toggled.connect(self._on_displacement_visibility_changed)
            dispLayout.addWidget(cb)
            self._disp_checkboxes[name] = cb
        dispFormLayout.addRow("Visibility:", dispLayout)

        # Grid size slider
        self.gridSizeSlider = slicer.qMRMLSliderWidget()
        self.gridSizeSlider.decimals = 1
        self.gridSizeSlider.singleStep = 0.5
        self.gridSizeSlider.minimum = 0.5
        self.gridSizeSlider.maximum = 20
        self.gridSizeSlider.value = 5
        self.gridSizeSlider.setToolTip(
            "Set the grid spacing (mm) for the displacement field."
        )
        self.gridSizeSlider.valueChanged.connect(self._on_grid_size_changed)
        dispFormLayout.addRow("Grid Spacing:", self.gridSizeSlider)

    def _add_checkerboard_widget(self, layout):
        self.checkerboardCollapsibleButton = slicer.qMRMLCollapsibleButton()
        self.checkerboardCollapsibleButton.text = "Checkerboard"
        layout.addWidget(self.checkerboardCollapsibleButton)
        checkerboardFormLayout = qt.QFormLayout(self.checkerboardCollapsibleButton)

        cbLayout = qt.QHBoxLayout()
        self._checkerboard_checkbox = qt.QCheckBox("Checkerboard")
        self._checkerboard_checkbox.setChecked(False)
        self._checkerboard_checkbox.toggled.connect(self._on_checkerboard_changed)
        cbLayout.addWidget(self._checkerboard_checkbox)
        checkerboardFormLayout.addRow("Comparison:", cbLayout)

        self._checkerboard_slider = slicer.qMRMLSliderWidget()
        self._checkerboard_slider.decimals = 0
        self._checkerboard_slider.singleStep = 1
        self._checkerboard_slider.minimum = 1
        self._checkerboard_slider.maximum = 30
        self._checkerboard_slider.value = 5
        self._checkerboard_slider.setEnabled(False)
        self._checkerboard_slider.setToolTip("Checkerboard tile size in voxels.")

        self._checkerboard_slider.connect(
            "valueChanged(double)", self._on_checkerboard_slider_changed
        )

        checkerboardFormLayout.addRow("Tile Size:", self._checkerboard_slider)

    def _on_checkerboard_slider_changed(self, value: float) -> None:
        if self._checkerboard_checkbox.isChecked():
            self._on_checkerboard_regenerate()

    def _on_checkerboard_changed(self, checked: bool) -> None:
        self._checkerboard_slider.setEnabled(checked)
        if checked:
            self._on_checkerboard_regenerate()
        else:
            # Restore normal alpha blending with fixed/warped
            layoutManager = slicer.app.layoutManager()
            for view_name, bg_key, fg_key in [
                ("Axial_Warped", "fixed_sag", "warped_ax"),
                ("Coronal_Warped", "fixed_sag", "warped_cor"),
                ("Axial_Moving", "moving_ax", "warped_ax"),
                ("Coronal_Moving", "moving_cor", "warped_cor"),
            ]:
                slice_widget = layoutManager.sliceWidget(view_name)
                if slice_widget is None:
                    continue
                composite_node = slice_widget.sliceLogic().GetSliceCompositeNode()
                if composite_node:
                    bg_node = self.selectors[bg_key].currentNode()
                    fg_node = self.selectors[fg_key].currentNode()
                    composite_node.SetBackgroundVolumeID(
                        bg_node.GetID() if bg_node else ""
                    )
                    composite_node.SetForegroundVolumeID(
                        fg_node.GetID() if fg_node else ""
                    )
                    composite_node.SetForegroundOpacity(0.5)
                    composite_node.SetCompositing(0)

    def _on_checkerboard_regenerate(self) -> None:
        tile = int(self._checkerboard_slider.value)
        layoutManager = slicer.app.layoutManager()
        for bg_key, fg_key, view_name, node_name in [
            ("fixed_sag", "warped_ax", "Axial_Warped", "checkerboard_ax"),
            ("fixed_sag", "warped_cor", "Coronal_Warped", "checkerboard_cor"),
            ("moving_ax", "warped_ax", "Axial_Moving", "checkerboard_moving_ax"),
            ("moving_cor", "warped_cor", "Coronal_Moving", "checkerboard_moving_cor"),
        ]:
            bg_node = self.selectors[bg_key].currentNode()
            fg_node = self.selectors[fg_key].currentNode()
            if bg_node is None or fg_node is None:
                continue
            fg_sitk = sitkUtils.PullVolumeFromSlicer(fg_node)

            fg_float = sitk.Cast(fg_sitk, sitk.sitkFloat32)
            fg_display = fg_node.GetDisplayNode()
            min_val = (
                float(fg_display.GetWindowLevelMin())
                if fg_display
                else float(sitk.GetArrayFromImage(fg_float).min())
            )
            max_val = (
                float(fg_display.GetWindowLevelMax())
                if fg_display
                else float(sitk.GetArrayFromImage(fg_float).max())
            )
            sentinel = min_val - 1.0

            zeros = sitk.Image(fg_float.GetSize(), sitk.sitkFloat32)
            zeros.CopyInformation(fg_float)
            ones = zeros + 1.0
            mask_sitk = sitk.CheckerBoard(zeros, ones, [tile, tile, tile])
            mask_binary = sitk.Cast(mask_sitk > 0.5, sitk.sitkUInt8)
            masked_fg = sitk.Mask(fg_float, mask_binary, outsideValue=sentinel)

            result_node = slicer.mrmlScene.GetFirstNodeByName(node_name)
            if result_node is None:
                result_node = slicer.mrmlScene.AddNewNodeByClass(
                    "vtkMRMLScalarVolumeNode", node_name
                )
            sitkUtils.PushVolumeToSlicer(masked_fg, result_node)

            display_node = result_node.GetDisplayNode()
            if display_node:
                display_node.SetApplyThreshold(True)
                display_node.SetLowerThreshold(sentinel + 0.5)
                display_node.SetAutoWindowLevel(False)
                display_node.SetWindowLevelMinMax(min_val, max_val)
                display_node.SetInterpolate(False)  # prevents blended edge pixels
            slice_widget = layoutManager.sliceWidget(view_name)
            if slice_widget is None:
                continue
            composite_node = slice_widget.sliceLogic().GetSliceCompositeNode()
            if composite_node:
                composite_node.SetBackgroundVolumeID(bg_node.GetID())
                composite_node.SetForegroundVolumeID(result_node.GetID())
                composite_node.SetForegroundOpacity(1.0)
                composite_node.SetCompositing(0)

    def _on_grid_size_changed(self, value: float) -> None:
        for transform_key in ["displacement_axi", "displacement_cor"]:
            transform_node = self.selectors.get(transform_key)
            if transform_node:
                node = transform_node.currentNode()
                if node:
                    display_node = node.GetDisplayNode()
                    if display_node:
                        display_node.SetGridSpacingMm(value)

    def set_all_views_orientation(self, orientation: str) -> None:
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
                slice_node = slice_widget.mrmlSliceNode()
                if slice_node:
                    slice_node.SetOrientation(orientation)

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

        if name in mapping:
            selector = self.selectors.get(mapping[name])
            if selector and not selector.currentNode():
                selector.setCurrentNode(node)

    def cleanup(self) -> None:
        if self._sceneObserverTag is not None:
            slicer.mrmlScene.RemoveObserver(self._sceneObserverTag)
            self._sceneObserverTag = None

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

    def _setup_jacobian_colormap(self) -> str:
        color_node_name = "JacobianColorMap"
        color_node = slicer.mrmlScene.GetFirstNodeByName(color_node_name)
        if not color_node:
            color_node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLColorTableNode", color_node_name
            )
            color_node.SetTypeToUser()
            color_node.SetNumberOfColors(5)
            color_node.SetColor(0, "Background", 0.0, 0.0, 0.0, 1.0)
            color_node.SetColor(1, "Red", 1.0, 0.0, 0.0, 1.0)
            color_node.SetColor(2, "Yellow", 1.0, 1.0, 0.0, 1.0)
            color_node.SetColor(3, "White", 1.0, 1.0, 1.0, 1.0)
            color_node.SetColor(4, "Blue", 0.0, 0.0, 1.0, 1.0)
        return color_node.GetID()

    def _on_displacement_visibility_changed(self) -> None:
        # Map checkbox name -> view name pairs (axial row, coronal row)
        checkbox_to_views = {
            "Fixed": ("Axial_Moving", "Coronal_Moving"),
            "Warped": ("Axial_Warped", "Coronal_Warped"),
            "Jacobian": ("Axial_Jacobian", "Coronal_Jacobian"),
            "Transform": ("Axial_Displacement", "Coronal_Displacement"),
        }

        # Show/hide the 4th column by switching layout
        transform_checked = self._disp_checkboxes["Transform"].isChecked()
        layout_id = CUSTOM_LAYOUT_ID if transform_checked else CUSTOM_LAYOUT_ID_NO_DISP
        slicer.app.layoutManager().setLayout(layout_id)
        slicer.app.processEvents()

        # Collect checked view IDs for each row
        layoutManager = slicer.app.layoutManager()
        ax_view_ids = []
        cor_view_ids = []
        for name, (ax_view, cor_view) in checkbox_to_views.items():
            if not self._disp_checkboxes[name].isChecked():
                continue
            for view_name, id_list in [
                (ax_view, ax_view_ids),
                (cor_view, cor_view_ids),
            ]:
                slice_widget = layoutManager.sliceWidget(view_name)
                if slice_widget is not None:
                    slice_node = slice_widget.mrmlSliceNode()
                    if slice_node:
                        id_list.append(slice_node.GetID())

        # Apply to each transform node
        for transform_key, view_ids in [
            ("displacement_axi", ax_view_ids),
            ("displacement_cor", cor_view_ids),
        ]:
            transform_node = self.selectors[transform_key].currentNode()
            if transform_node and view_ids:
                self.logic.set_transform_node_visibility(transform_node, view_ids)

        self._on_grid_size_changed(self.gridSizeSlider.value)

    def onApplyButton(self) -> None:
        slicer.app.layoutManager().setLayout(CUSTOM_LAYOUT_ID)
        slicer.app.processEvents()

        jacobian_color_id = self._setup_jacobian_colormap()
        for key in ["jacobian_ax", "jacobian_cor"]:
            jac_node = self.selectors[key].currentNode()
            if jac_node:
                display_node = jac_node.GetDisplayNode()
                if display_node:
                    display_node.SetAndObserveColorNodeID(jacobian_color_id)
                    display_node.SetInterpolate(False)
                    display_node.SetAutoWindowLevel(False)
                    display_node.SetWindowLevelMinMax(0, 4)

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
            "Axial_Displacement": {},
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

        layoutManager = slicer.app.layoutManager()
        for view_name, assignment in view_assignments.items():
            slice_widget = layoutManager.sliceWidget(view_name)
            if slice_widget is None:
                continue
            composite_node = slice_widget.sliceLogic().GetSliceCompositeNode()
            if not composite_node:
                continue
            bg_node = assignment.get("Background")
            fg_node = assignment.get("Foreground")
            composite_node.SetBackgroundVolumeID(bg_node.GetID() if bg_node else "")
            composite_node.SetForegroundVolumeID(fg_node.GetID() if fg_node else "")
            if fg_node:
                composite_node.SetForegroundOpacity(0.5)

        self._on_displacement_visibility_changed()

        slicer.util.resetSliceViews()


class registrationViewerLogic(ScriptedLoadableModuleLogic):
    def __init__(self) -> None:
        ScriptedLoadableModuleLogic.__init__(self)

    def create_transform_display_node_for_views(
        self, views: List[str]
    ) -> "vtkMRMLTransformDisplayNode":
        dn = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTransformDisplayNode")
        dn.SetViewNodeIDs(views)
        dn.SetVisibility(True)
        dn.SetVisibility2D(True)
        dn.SetVisibility3D(False)
        dn.SetVisualizationMode(slicer.vtkMRMLTransformDisplayNode.VIS_MODE_GRID)
        return dn

    def set_transform_node_visibility(
        self, transform_node: "vtkMRMLTransformNode", views: List[str]
    ) -> None:
        old_dn = transform_node.GetDisplayNode()
        if old_dn:
            slicer.mrmlScene.RemoveNode(old_dn)
        new_dn = self.create_transform_display_node_for_views(views)
        transform_node.SetAndObserveDisplayNodeID(new_dn.GetID())
