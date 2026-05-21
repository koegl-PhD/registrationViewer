from __future__ import annotations

import time

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

SLICE_VIEW_ASSIGNMENTS = [
    ("Red", "axial", "Axial"),
    ("Yellow", "sagittal", "Sagittal"),
    ("Green", "coronal", "Coronal"),
]

CURTAIN_ROCK_INTERVAL_MS = 16
# Tune this value to change how fast the curtain rocks from 0 to 100 and back.
CURTAIN_ROCK_SPEED_PERCENT_PER_SECOND = 7.0


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
        self._curtain_checkbox = None
        self._curtain_rock_checkbox = None
        self._curtain_rock_timer = None
        self._curtain_rock_direction = 1.0
        self._curtain_rock_last_time = None

    def enter(self) -> None:
        self.onApplyButton()

    def setup(self) -> None:
        ScriptedLoadableModuleWidget.setup(self)

        self.logic = registrationViewerLogic()

        parametersCollapsibleButton = slicer.qMRMLCollapsibleButton()
        parametersCollapsibleButton.text = "Nodes"
        self.layout.addWidget(parametersCollapsibleButton)

        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        self._add_node_selector(
            parametersFormLayout,
            "axial",
            "Axial",
            ["vtkMRMLScalarVolumeNode"],
        )
        self._add_node_selector(
            parametersFormLayout,
            "sagittal",
            "Sagittal",
            ["vtkMRMLScalarVolumeNode"],
        )
        self._add_node_selector(
            parametersFormLayout,
            "coronal",
            "Coronal",
            ["vtkMRMLScalarVolumeNode"],
        )
        self._add_node_selector(
            parametersFormLayout,
            "superres",
            "Superres",
            ["vtkMRMLScalarVolumeNode"],
        )

        self.applyButton = qt.QPushButton("Update Views")
        self.applyButton.toolTip = "Assign selected nodes to the four-up layout."
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
        self._add_curtain_widget(self.layout)

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

    def _add_curtain_widget(self, layout):
        self.curtainCollapsibleButton = slicer.qMRMLCollapsibleButton()
        self.curtainCollapsibleButton.text = "Curtain"
        layout.addWidget(self.curtainCollapsibleButton)
        curtainFormLayout = qt.QFormLayout(self.curtainCollapsibleButton)

        self._curtain_checkbox = qt.QCheckBox("Curtain")
        self._curtain_checkbox.setChecked(False)
        self._curtain_checkbox.toggled.connect(self._on_curtain_changed)
        curtainFormLayout.addRow("Enable:", self._curtain_checkbox)

        self._curtain_rock_checkbox = qt.QCheckBox("Rock")
        self._curtain_rock_checkbox.setChecked(False)
        self._curtain_rock_checkbox.setEnabled(False)
        self._curtain_rock_checkbox.toggled.connect(self._on_curtain_rock_changed)
        curtainFormLayout.addRow("Rock:", self._curtain_rock_checkbox)

        self._curtain_rock_timer = qt.QTimer()
        self._curtain_rock_timer.setInterval(CURTAIN_ROCK_INTERVAL_MS)
        self._curtain_rock_timer.timeout.connect(self._on_curtain_rock_tick)

        self._curtain_slider = slicer.qMRMLSliderWidget()
        self._curtain_slider.decimals = 0
        self._curtain_slider.singleStep = 1
        self._curtain_slider.minimum = 0
        self._curtain_slider.maximum = 100
        self._curtain_slider.value = 50
        self._curtain_slider.setEnabled(False)
        self._curtain_slider.setToolTip(
            "Curtain position (0=fully closed, 100=fully open)."
        )
        self._curtain_slider.connect(
            "valueChanged(double)", self._on_curtain_slider_changed
        )
        curtainFormLayout.addRow("Position:", self._curtain_slider)

    def _get_volume_node(self, key: str):
        selector = self.selectors.get(key)
        if selector:
            return selector.currentNode()
        return slicer.mrmlScene.GetFirstNodeByName(key)

    def _on_curtain_changed(self, checked: bool) -> None:
        self._curtain_slider.setEnabled(checked)
        self._curtain_rock_checkbox.setEnabled(checked)
        if checked:
            if self._curtain_rock_checkbox.isChecked():
                self._start_curtain_rock()
            self._on_curtain_regenerate()
        else:
            self._stop_curtain_rock()
            # Restore normal alpha blending
            layoutManager = slicer.app.layoutManager()
            for view_name, bg_key, fg_key in [
                ("Red", "axial", "superres"),
                ("Yellow", "sagittal", "superres"),
                ("Green", "coronal", "superres"),
            ]:
                slice_widget = layoutManager.sliceWidget(view_name)
                if slice_widget is None:
                    continue
                composite_node = slice_widget.sliceLogic().GetSliceCompositeNode()
                if composite_node:
                    bg_node = self._get_volume_node(bg_key)
                    fg_node = self._get_volume_node(fg_key)
                    composite_node.SetBackgroundVolumeID(
                        bg_node.GetID() if bg_node else ""
                    )
                    composite_node.SetForegroundVolumeID(
                        fg_node.GetID() if fg_node else ""
                    )
                    composite_node.SetForegroundOpacity(0.5)
                    composite_node.SetCompositing(0)

    def _on_curtain_slider_changed(self, value: float) -> None:
        if self._curtain_checkbox.isChecked():
            self._on_curtain_regenerate()

    def _on_curtain_rock_changed(self, checked: bool) -> None:
        if checked and self._curtain_checkbox.isChecked():
            self._start_curtain_rock()
        else:
            self._stop_curtain_rock()

    def _start_curtain_rock(self) -> None:
        if (
            self._curtain_rock_timer is not None
            and not self._curtain_rock_timer.isActive()
        ):
            self._curtain_rock_last_time = time.monotonic()
            self._curtain_rock_timer.start()

    def _stop_curtain_rock(self) -> None:
        if self._curtain_rock_timer is not None and self._curtain_rock_timer.isActive():
            self._curtain_rock_timer.stop()
        self._curtain_rock_last_time = None

    def _on_curtain_rock_tick(self) -> None:
        now = time.monotonic()
        if self._curtain_rock_last_time is None:
            self._curtain_rock_last_time = now
            return

        elapsed_seconds = now - self._curtain_rock_last_time
        self._curtain_rock_last_time = now

        step = CURTAIN_ROCK_SPEED_PERCENT_PER_SECOND * elapsed_seconds
        next_value = self._curtain_slider.value + step * self._curtain_rock_direction

        while next_value > 100.0 or next_value < 0.0:
            if next_value > 100.0:
                next_value = 100.0 - (next_value - 100.0)
                self._curtain_rock_direction = -1.0
            elif next_value < 0.0:
                next_value = -next_value
                self._curtain_rock_direction = 1.0

        was_blocked = self._curtain_slider.blockSignals(True)
        self._curtain_slider.value = next_value
        self._curtain_slider.blockSignals(was_blocked)
        self._on_curtain_regenerate()

    def _on_curtain_regenerate(self) -> None:
        render_blocker = getattr(slicer.util, "RenderBlocker", None)
        if render_blocker is None:
            self._apply_curtain_regenerate()
        else:
            with render_blocker():
                self._apply_curtain_regenerate()

    def _apply_curtain_regenerate(self) -> None:
        position = self._curtain_slider.value / 100.0
        layoutManager = slicer.app.layoutManager()
        for bg_key, fg_key, view_name, node_name in [
            ("axial", "superres", "Red", "curtain_axial"),
            ("sagittal", "superres", "Yellow", "curtain_sagittal"),
            ("coronal", "superres", "Green", "curtain_coronal"),
        ]:
            fg_node = self._get_volume_node(fg_key)
            bg_node = self._get_volume_node(bg_key)
            if fg_node is None or bg_node is None:
                continue

            slice_widget = layoutManager.sliceWidget(view_name)
            if slice_widget is None:
                continue

            # Instead of always pulling from fg_node, use checkerboard result if active
            cb_node_names = {
                "Red": "checkerboard_axial",
                "Yellow": "checkerboard_sagittal",
                "Green": "checkerboard_coronal",
            }
            if self._checkerboard_checkbox.isChecked():
                cb_node = slicer.mrmlScene.GetFirstNodeByName(cb_node_names[view_name])
                source_sitk = (
                    sitkUtils.PullVolumeFromSlicer(cb_node)
                    if cb_node
                    else sitkUtils.PullVolumeFromSlicer(fg_node)
                )
            else:
                source_sitk = sitkUtils.PullVolumeFromSlicer(fg_node)

            fg_float = sitk.Cast(source_sitk, sitk.sitkFloat32)

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
            sentinel = min_val - abs(max_val - min_val) - 1.0

            slice_node = slice_widget.mrmlSliceNode()
            axis = self._get_horizontal_array_axis(slice_node, fg_float)

            arr = sitk.GetArrayFromImage(fg_float).copy()
            cutoff = int(position * arr.shape[axis])
            idx = [slice(None), slice(None), slice(None)]
            idx[axis] = slice(cutoff, None)
            arr[tuple(idx)] = sentinel

            # Draw a bright line at the curtain edge
            line_idx = [slice(None), slice(None), slice(None)]
            line_idx[axis] = min(max(cutoff, 0), arr.shape[axis] - 1)
            arr[tuple(line_idx)] = max(abs(min_val), abs(max_val), 1.0) * 10.0

            masked_fg = sitk.GetImageFromArray(arr)
            masked_fg.CopyInformation(fg_float)

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
                display_node.SetInterpolate(False)

            composite_node = slice_widget.sliceLogic().GetSliceCompositeNode()
            if composite_node:
                composite_node.SetBackgroundVolumeID(bg_node.GetID())
                composite_node.SetForegroundVolumeID(result_node.GetID())
                composite_node.SetForegroundOpacity(self.visualization.fadeSlider.value)
                composite_node.SetCompositing(0)

    def _get_horizontal_array_axis(
        self, slice_node: "vtkMRMLSliceNode", fg_sitk: "sitk.Image"
    ) -> int:
        slice_to_ras = slice_node.GetSliceToRAS()
        # Column 0 = right direction in RAS space
        h_ras = [slice_to_ras.GetElement(i, 0) for i in range(3)]
        # Find which sitk voxel axis is most aligned with screen-horizontal
        direction = (
            fg_sitk.GetDirection()
        )  # 3x3 as flat list, column i = RAS dir of voxel axis i
        best_axis, best_dot = 0, -1.0
        for vox_axis in range(3):
            col = [direction[r * 3 + vox_axis] for r in range(3)]
            dot = abs(sum(h_ras[r] * col[r] for r in range(3)))
            if dot > best_dot:
                best_dot = dot
                best_axis = vox_axis
        # sitk voxel axis → numpy axis: numpy = 2 - sitk
        return 2 - best_axis

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
            # Restore normal alpha blending.
            layoutManager = slicer.app.layoutManager()
            for view_name, bg_key, fg_key in [
                ("Red", "axial", "superres"),
                ("Yellow", "sagittal", "superres"),
                ("Green", "coronal", "superres"),
            ]:
                slice_widget = layoutManager.sliceWidget(view_name)
                if slice_widget is None:
                    continue
                composite_node = slice_widget.sliceLogic().GetSliceCompositeNode()
                if composite_node:
                    bg_node = self._get_volume_node(bg_key)
                    fg_node = self._get_volume_node(fg_key)
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
            ("axial", "superres", "Red", "checkerboard_axial"),
            ("sagittal", "superres", "Yellow", "checkerboard_sagittal"),
            ("coronal", "superres", "Green", "checkerboard_coronal"),
        ]:
            bg_node = self._get_volume_node(bg_key)
            fg_node = self._get_volume_node(fg_key)
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

        if self._curtain_checkbox is not None and self._curtain_checkbox.isChecked():
            self._on_curtain_regenerate()

    def set_all_views_orientation(self, orientation: str) -> None:
        layoutManager = slicer.app.layoutManager()
        for view_name, _, _ in SLICE_VIEW_ASSIGNMENTS:
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
        name_key = name.lower()

        matches = [
            ("sr", "superres"),
            ("cor", "coronal"),
            ("sag", "sagittal"),
            ("axi", "axial"),
            ("tre", "axial"),
        ]

        for token, selector_key in matches:
            if token not in name_key:
                continue
            selector = self.selectors.get(selector_key)
            if selector and not selector.currentNode():
                selector.setCurrentNode(node)
            return

    def cleanup(self) -> None:
        self._stop_curtain_rock()
        if self._sceneObserverTag is not None:
            slicer.mrmlScene.RemoveObserver(self._sceneObserverTag)
            self._sceneObserverTag = None

    def onLinkButton(self, checked: bool) -> None:
        layoutManager = slicer.app.layoutManager()
        for view_name, _, _ in SLICE_VIEW_ASSIGNMENTS:
            slice_widget = layoutManager.sliceWidget(view_name)
            if slice_widget is not None:
                composite_node = slice_widget.sliceLogic().GetSliceCompositeNode()
                if composite_node:
                    composite_node.SetLinkedControl(checked)
                    if hasattr(composite_node, "SetHotLinkedControl"):
                        composite_node.SetHotLinkedControl(checked)

    def onApplyButton(self) -> None:
        slicer.app.layoutManager().setLayout(
            slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView
        )
        slicer.app.processEvents()

        layoutManager = slicer.app.layoutManager()
        superres_node = self.selectors["superres"].currentNode()
        for view_name, volume_key, orientation in SLICE_VIEW_ASSIGNMENTS:
            slice_widget = layoutManager.sliceWidget(view_name)
            if slice_widget is None:
                continue
            slice_node = slice_widget.mrmlSliceNode()
            if slice_node:
                slice_node.SetOrientation(orientation)
            composite_node = slice_widget.sliceLogic().GetSliceCompositeNode()
            if not composite_node:
                continue
            bg_node = self.selectors[volume_key].currentNode()
            fg_node = superres_node
            composite_node.SetBackgroundVolumeID(bg_node.GetID() if bg_node else "")
            composite_node.SetForegroundVolumeID(fg_node.GetID() if fg_node else "")
            if fg_node:
                composite_node.SetForegroundOpacity(0.5)

        slicer.util.resetSliceViews()


class registrationViewerLogic(ScriptedLoadableModuleLogic):
    def __init__(self) -> None:
        ScriptedLoadableModuleLogic.__init__(self)
