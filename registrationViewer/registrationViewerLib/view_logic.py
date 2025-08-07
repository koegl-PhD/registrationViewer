from typing import List, Literal

from qt import QEvent, QObject
import slicer
from slicer import vtkMRMLScalarVolumeNode, vtkMRMLLayoutNode

# Constants
LAYOUT_ID_MAP = {"Red": 801, "Green": 802, "Yellow": 803}
VALID_VIEW_NAMES = ["Red", "Green", "Yellow"]
ALL_VIEW_NAMES = ['Red', 'Green', 'Yellow', 'Red+', 'Green+', 'Yellow+']


def _get_slice_logic(view: str):
    """Helper function to get slice logic for a view."""
    return slicer.app.layoutManager().sliceWidget(view).sliceLogic()


def _get_layout_manager():
    """Helper function to get the layout manager."""
    return slicer.app.layoutManager()


def _install_event_filters_on_views(view_names: List[str], to_layout: str) -> None:
    """Helper function to install event filters on specified views."""
    event_filter = ViewClickFilter(to_layout=to_layout)
    layout_manager = _get_layout_manager()

    for view_name in view_names:
        slice_widget = layout_manager.sliceWidget(view_name)
        if slice_widget:
            view_widget = slice_widget.sliceView()
            event_filter.add_view(view_name, view_widget)
            view_widget.installEventFilter(event_filter)

    # Keep a reference to the event filter - needs to be global so it won't be deleted
    global _event_filter
    _event_filter = event_filter


def update_views_with_volume(views: List[str], volume: vtkMRMLScalarVolumeNode) -> None:
    for view in views:
        slice_logic = _get_slice_logic(view)
        composite_node = slice_logic.GetSliceCompositeNode()

        composite_node.SetBackgroundVolumeID(
            volume.GetID() if volume else None)
        composite_node.SetForegroundVolumeID(None)


def link_views(views: List[str]) -> None:
    """Links the given views."""
    for view in views:
        slice_logic = _get_slice_logic(view)
        composite_node = slice_logic.GetSliceCompositeNode()
        composite_node.SetLinkedControl(True)


class ViewClickFilter(QObject):
    def __init__(self, to_layout: Literal["set_custom_compare_layout", "set_three_over_three_layout"], parent=None):
        super().__init__(parent)
        self.view_widgets = {}
        self.to_layout = to_layout

    def add_view(self, name, widget):
        self.view_widgets[widget] = name

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonDblClick and watched in self.view_widgets:
            view_name = self.view_widgets[watched]
            # Remove '+' suffix if present
            clean_view_name = view_name.rstrip('+')

            if self.to_layout == "set_custom_compare_layout":
                set_custom_compare_layout(clean_view_name)
            elif self.to_layout == "set_three_over_three_layout":
                set_three_over_three_layout()

            return True  # Event has been handled

        return QObject.eventFilter(self, watched, event)


def set_custom_compare_layout(view_name: Literal["Red", "Green", "Yellow"]) -> None:
    """
    Create a custom 1x2 layout for the given color.
    The two views (e.g., Red and Red+) are shown side by side.
    """
    if view_name not in VALID_VIEW_NAMES:
        raise ValueError(
            f"Invalid view name. Must be one of {VALID_VIEW_NAMES}.")

    custom_layout = f"""
    <layout type="vertical" split="true">
        <item>
            <layout type="horizontal">
                <item>
                    <view class="vtkMRMLSliceNode" singletontag="{view_name}">
                    </view>
                </item>
                <item>
                    <view class="vtkMRMLSliceNode" singletontag="{view_name}+">
                    </view>
                </item>
            </layout>
        </item>
    </layout>
    """

    layout_manager = _get_layout_manager()
    custom_layout_id = LAYOUT_ID_MAP[view_name]

    layout_manager.layoutLogic().GetLayoutNode().AddLayoutDescription(
        custom_layout_id, custom_layout)
    layout_manager.setLayout(custom_layout_id)

    # Install event filters on both views
    view_names = [view_name, f"{view_name}+"]
    _install_event_filters_on_views(view_names, "set_three_over_three_layout")


def set_three_over_three_layout() -> None:
    """Set the three-over-three layout and install event filters."""
    layout_manager = _get_layout_manager()
    layout_manager.setLayout(vtkMRMLLayoutNode.SlicerLayoutThreeOverThreeView)

    # Install event filters on all views
    _install_event_filters_on_views(
        ALL_VIEW_NAMES, "set_custom_compare_layout")


def get_view_offset(view: str) -> float:
    """Get the current offset of the given view."""
    slice_logic = _get_slice_logic(view)
    return slice_logic.GetSliceNode().GetSliceOffset()


def set_view_offset(view: str, offset: float) -> None:
    """Set the offset for the given view."""
    slice_logic = _get_slice_logic(view)
    slice_logic.GetSliceNode().SetSliceOffset(offset)


def set_offset_to_ras(position_ras, view):
    """Set the view offset based on RAS position."""
    slice_logic = _get_slice_logic(view)
    slice_node = slice_logic.GetSliceNode()

    # Get the SliceToRAS matrix for the current slice view
    slice_to_ras = slice_node.GetSliceToRAS()

    # The third column of the SliceToRAS matrix is the slice normal
    normal = [slice_to_ras.GetElement(i, 2) for i in range(3)]

    # Compute the offset as the dot product of the slice normal with the target RAS position
    offset = sum(normal[i] * position_ras[i] for i in range(3))

    # Set the computed offset for this view
    set_view_offset(view, offset)
