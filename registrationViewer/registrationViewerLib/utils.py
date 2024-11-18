from typing import Tuple, Callable, List, Literal

import qt
import slicer
import vtk
from qt import QEvent, QObject


def create_shortcuts(*shortcuts: Tuple[str, Callable]) -> None:
    """
    Creates and initializes shortcuts for the main window.
    """

    for (shortcutKey, callback) in shortcuts:
        shortcut = qt.QShortcut(slicer.util.mainWindow())
        shortcut.setKey(qt.QKeySequence(shortcutKey))
        shortcut.connect('activated()', callback)


def temp_load_data(self):
    node_volume_fixed = slicer.util.loadVolume(
        self.resourcePath("Data/lung/fixed.nii.gz"))
    node_volume_moving = slicer.util.loadVolume(
        self.resourcePath("Data/lung/moving.nii.gz"))
    node_transformation = slicer.util.loadTransform(
        self.resourcePath("Data/lung/moving_deformation_to_fixed.nii.gz"))

    node_volume_fixed.SetName('volume_fixed')
    node_volume_moving.SetName('volume_moving')
    node_transformation.SetName('displacement_field')

    # add to the scene
    slicer.mrmlScene.AddNode(node_volume_fixed)
    slicer.mrmlScene.AddNode(node_volume_moving)
    slicer.mrmlScene.AddNode(node_transformation)

    # set the nodes
    self.ui.inputSelector_fixed.setCurrentNode(node_volume_fixed)
    self.ui.inputSelector_moving.setCurrentNode(node_volume_moving)
    self.ui.inputSelector_transformation.setCurrentNode(node_transformation)


def link_views(views: List[str]) -> None:
    """
    Links the given views.

    @param views: The views to link.
    """

    for view in views:
        sliceLogic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
        compositeNode = sliceLogic.GetSliceCompositeNode()
        compositeNode.SetLinkedControl(True)


def unlink_views(views: List[str]) -> None:

    for view in views:
        sliceLogic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
        compositeNode = sliceLogic.GetSliceCompositeNode()
        compositeNode.SetLinkedControl(False)


class ViewClickFilter(QObject):
    def __init__(self, to_layout: Literal["set_1x2_layout", "set_2x3_layout", "set_3x3_layout"], parent=None):
        super().__init__(parent)
        self.view_widgets = {}
        self.to_layout = to_layout

    def add_view(self, name, widget):
        self.view_widgets[widget] = name

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonDblClick:
            if watched in self.view_widgets:
                view_name = self.view_widgets[watched]

                if self.to_layout == "set_1x2_layout":
                    set_1x2_layout(view_name[:-1])
                elif self.to_layout == "set_2x3_layout":
                    set_2x3_layout()
                elif self.to_layout == "set_3x3_layout":
                    set_3x3_layout()

                return True  # Event has been handled
        return QObject.eventFilter(self, watched, event)


def set_2x3_layout() -> None:
    customLayout = """
    <layout type="vertical" split="true">
    <item>
        <layout type="horizontal">
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Red1">
            <property name="orientation" action="default">Axial</property>
            <property name="viewlabel" action="default">Fixed - axial</property>
            <property name="viewcolor" action="default">#F34A33</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Green1">
            <property name="orientation" action="default">Coronal</property>
            <property name="viewlabel" action="default">Fixed - coronal</property>
            <property name="viewcolor" action="default">#6EB04B</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Yellow1">
            <property name="orientation" action="default">Sagittal</property>
            <property name="viewlabel" action="default">Fixed - saggital</property>
            <property name="viewcolor" action="default">#EDD54C</property>
            </view>
        </item>
        </layout>
    </item>

    <item>
        <layout type="horizontal">
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Red2">
            <property name="orientation" action="default">Axial</property>
            <property name="viewlabel" action="default">Moving - axial</property>
            <property name="viewcolor" action="default">#F34A33</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Green2">
            <property name="orientation" action="default">Coronal</property>
            <property name="viewlabel" action="default">Moving - coronal</property>
            <property name="viewcolor" action="default">#6EB04B</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Yellow2">
            <property name="orientation" action="default">Sagittal</property>
            <property name="viewlabel" action="default">Moving - sagittal</property>
            <property name="viewcolor" action="default">#EDD54C</property>
            </view>
        </item>
        </layout>
    </item>
    </layout>
    """

    # Built-in layout IDs are all below 100, so you can choose any large random number
    # for your custom layout ID.
    customLayoutId = 701

    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode(
    ).AddLayoutDescription(customLayoutId, customLayout)

    # Switch to the new custom layout
    layoutManager.setLayout(customLayoutId)

    # Create event filter
    event_filter = ViewClickFilter(to_layout="set_1x2_layout")

    # Install filter on all views
    view_names = ['Red1', 'Green1', 'Yellow1', 'Red2', 'Green2', 'Yellow2']
    for view_name in view_names:
        slice_widget = layoutManager.sliceWidget(view_name)
        if slice_widget:
            view_widget = slice_widget.sliceView()
            event_filter.add_view(view_name, view_widget)
            view_widget.installEventFilter(event_filter)
            print(f"Installed event filter on {view_name}")

    # Keep a reference to the event filter
    global _event_filter
    _event_filter = event_filter


def set_3x3_layout() -> None:

    customLayout = """
    <layout type="vertical" split="true">
    <item>
        <layout type="horizontal">
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Red1">
            <property name="orientation" action="default">Axial</property>
            <property name="viewlabel" action="default">Fixed - axial</property>
            <property name="viewcolor" action="default">#F34A33</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Green1">
            <property name="orientation" action="default">Coronal</property>
            <property name="viewlabel" action="default">Fixed - coronal</property>
            <property name="viewcolor" action="default">#6EB04B</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Yellow1">
            <property name="orientation" action="default">Sagittal</property>
            <property name="viewlabel" action="default">Fixed - sagittal</property>
            <property name="viewcolor" action="default">#EDD54C</property>
            </view>
        </item>
        </layout>
    </item>

    <item>
        <layout type="horizontal">
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Red2">
            <property name="orientation" action="default">Axial</property>
            <property name="viewlabel" action="default">Moving - axial</property>
            <property name="viewcolor" action="default">#F34A33</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Green2">
            <property name="orientation" action="default">Coronal</property>
            <property name="viewlabel" action="default">Moving - coronal</property>
            <property name="viewcolor" action="default">#6EB04B</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Yellow2">
            <property name="orientation" action="default">Sagittal</property>
            <property name="viewlabel" action="default">Moving - sagittal</property>
            <property name="viewcolor" action="default">#EDD54C</property>
            </view>
        </item>
        </layout>
    </item>

    <item>
        <layout type="horizontal">
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Red3">
            <property name="orientation" action="default">Axial</property>
            <property name="viewlabel" action="default">Diff - axial</property>
            <property name="viewcolor" action="default">#F34A33</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Green3">
            <property name="orientation" action="default">Coronal</property>
            <property name="viewlabel" action="default">Diff - coronal</property>
            <property name="viewcolor" action="default">#6EB04B</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Yellow3">
            <property name="orientation" action="default">Sagittal</property>
            <property name="viewlabel" action="default">Diff - sagittal</property>
            <property name="viewcolor" action="default">#EDD54C</property>
            </view>
        </item>
        </layout>
    </item>
    </layout>
    """

    # Built-in layout IDs are all below 100, so you can choose any large random number
    # for your custom layout ID.
    customLayoutId = 601

    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode(
    ).AddLayoutDescription(customLayoutId, customLayout)

    # Switch to the new custom layout
    layoutManager.setLayout(customLayoutId)

    # Create event filter
    event_filter = ViewClickFilter(to_layout="set_1x2_layout")

    view_names = [
        "Red1", "Green1", "Yellow1",
        "Red2", "Green2", "Yellow2",
        "Red3", "Green3", "Yellow3"]

    # Install filter on all views
    for view_name in view_names:
        slice_widget = layoutManager.sliceWidget(view_name)
        if slice_widget:
            view_widget = slice_widget.sliceView()
            event_filter.add_view(view_name, view_widget)
            view_widget.installEventFilter(event_filter)
            print(f"Installed event filter on {view_name}")

    # Keep a reference to the event filter
    global _event_filter
    _event_filter = event_filter


def set_1x2_layout(color: Literal["Red", "Green", "Yellow"]) -> None:
    """
    Create a custom 1x2 layout for the given color.
    The two views (e.g., Red1 and Red2) are shown side by side.

    Parameters:
    - color (str): The color of the slice view to use ("Red", "Green", or "Yellow").
    """

    if color not in ["Red", "Green", "Yellow"]:
        raise ValueError("Invalid color. Must be 'Red', 'Green', or 'Yellow'.")

    if color == "Red":
        orientation = "Axial"
        hexColor = "#F34A33"
    elif color == "Green":
        orientation = "Coronal"
        hexColor = "#6EB04B"
    else:
        orientation = "Sagittal"
        hexColor = "#EDD54C"

    customLayout = f"""
    <layout type="vertical" split="true">
        <item>
            <layout type="horizontal">
                <item>
                    <view class="vtkMRMLSliceNode" singletontag="{color}4">
                    <property name="orientation" action="default">{orientation}</property>
                    <property name="viewlabel" action="default">Fixed - {orientation.lower()}</property>
                    <property name="viewcolor" action="default">{hexColor}</property>
                    </view>
                </item>
                <item>
                    <view class="vtkMRMLSliceNode" singletontag="{color}5">
                    <property name="orientation" action="default">{orientation}</property>
                    <property name="viewlabel" action="default">Moving - {orientation.lower()}</property>
                    <property name="viewcolor" action="default">{hexColor}</property>
                    </view>
                </item>
            </layout>
        </item>
    </layout>
    """

    # Create a unique layout ID based on the color
    layoutIdMap = {"Red": 801, "Green": 802, "Yellow": 803}
    customLayoutId = layoutIdMap[color]

    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode(
    ).AddLayoutDescription(customLayoutId, customLayout)

    # Switch to the new custom layout
    layoutManager.setLayout(customLayoutId)

    # Create event filter
    event_filter = ViewClickFilter(to_layout="set_2x3_layout")

    # Install filter on all views
    view_names = [f"{color}4", f"{color}5"]
    for view_name in view_names:
        slice_widget = layoutManager.sliceWidget(view_name)
        if slice_widget:
            view_widget = slice_widget.sliceView()
            event_filter.add_view(view_name, view_widget)
            view_widget.installEventFilter(event_filter)
            print(f"Installed event filter on {view_name}")

    # Keep a reference to the event filter
    global _event_filter
    _event_filter = event_filter


def apply_and_harden_transform_to_node(node_target: slicer.vtkMRMLNode,
                                       node_transform: slicer.vtkMRMLTransformNode, ) -> None:
    """
    Applies the given transform to the target node and hardens it.

    @param node_target: The target node.
    @param node_transform: The transform node.
    """

    node_target.SetAndObserveTransformNodeID(node_transform.GetID())

    node_target.HardenTransform()


def resample_node_to_reference_node(node_input: slicer.vtkMRMLScalarVolumeNode,
                                    node_reference: slicer.vtkMRMLScalarVolumeNode) -> None:
    params = {}

    params["inputVolume"] = node_input
    params["outputVolume"] = node_input
    params["referenceVolume"] = node_reference
    params["interpolationType"] = "linear"

    slicer.cli.runSync(
        slicer.modules.resamplescalarvectordwivolume, None, params)


def warp_moving_with_transform(node_moving: slicer.vtkMRMLScalarVolumeNode,
                               node_transform: slicer.vtkMRMLTransformNode,
                               node_warped):

    apply_and_harden_transform_to_node(node_warped, node_transform)

    resample_node_to_reference_node(node_warped, node_moving)


def collapse_all_segmentations() -> None:

    subjectHierarchyNode = slicer.mrmlScene.GetSubjectHierarchyNode()

    if subjectHierarchyNode:
        itemIDs = vtk.vtkIdList()
        subjectHierarchyNode.GetItemChildren(
            subjectHierarchyNode.GetSceneItemID(), itemIDs, True)

        for i in range(itemIDs.GetNumberOfIds()):
            itemID = itemIDs.GetId(i)
            node = subjectHierarchyNode.GetItemDataNode(itemID)
            if node and node.IsA("vtkMRMLSegmentationNode"):
                subjectHierarchyNode.SetItemExpanded(itemID, False)
                # turn off visibility
                node.SetDisplayVisibility(False)


def get_view_offset(view: str) -> float:
    """
    Get the current offset of the given view.
    """

    sliceLogic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
    sliceNode = sliceLogic.GetSliceNode()

    return sliceNode.GetSliceOffset()


def set_view_offset(view: str, offset: float) -> None:
    """
    Set the offset for the given view.
    """

    sliceLogic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
    sliceNode = sliceLogic.GetSliceNode()

    sliceNode.SetSliceOffset(offset)
