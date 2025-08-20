from __future__ import annotations
import slicer
from typing import Tuple
import numpy as np
import vtk


def _slice_axes_and_point(sn: "vtkMRMLSliceNode") -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (x,y,z,point) from SliceToRAS; do not mutate."""
    m: vtk.vtkMatrix4x4 = sn.GetSliceToRAS()
    x = np.array([m.GetElement(0, 0), m.GetElement(
        1, 0), m.GetElement(2, 0)], dtype=float)
    y = np.array([m.GetElement(0, 1), m.GetElement(
        1, 1), m.GetElement(2, 1)], dtype=float)
    z = np.array([m.GetElement(0, 2), m.GetElement(
        1, 2), m.GetElement(2, 2)], dtype=float)
    p = np.array([m.GetElement(0, 3), m.GetElement(
        1, 3), m.GetElement(2, 3)], dtype=float)
    return x, y, z, p


def _triple_plane_intersection(n1: np.ndarray, p1: np.ndarray,
                               n2: np.ndarray, p2: np.ndarray,
                               n3: np.ndarray, p3: np.ndarray) -> np.ndarray:
    """Return point x with n_i·x = n_i·p_i."""
    A = np.vstack([n1, n2, n3])
    b = np.array([n1.dot(p1), n2.dot(p2), n3.dot(p3)], dtype=float)
    return np.linalg.solve(A, b)


def _build_rt_from_axes_and_corner(axes: np.ndarray, corner: np.ndarray, size: np.ndarray) -> vtk.vtkMatrix4x4:
    """Return 4x4 transform: align ROI axes, place one corner at 'corner'."""
    R = axes  # 3x3 with columns = ROI local X,Y,Z in RAS
    center = corner + R @ (size * 0.5)
    m = vtk.vtkMatrix4x4()
    for i in range(3):
        m.SetElement(i, 0, R[i, 0])
        m.SetElement(i, 1, R[i, 1])
        m.SetElement(i, 2, R[i, 2])
        m.SetElement(i, 3, center[i])
    m.SetElement(3, 3, 1.0)
    return m


def anchor_roi_corner_to_triplanar(roiName: str = "R") -> None:
    """Anchor one ROI corner at 3-slice intersection; follow all rotations/translations."""
    roi = slicer.util.getNode(roiName)
    if not roi.IsA("vtkMRMLMarkupsROINode"):
        raise RuntimeError("ROI must be vtkMRMLMarkupsROINode")

    roi.SetCenter(0.0, 0.0, 0.0)

    tnode = slicer.mrmlScene.GetFirstNodeByName(f"{roiName}_follow_triplanar")
    if tnode is None:
        tnode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLinearTransformNode", f"{roiName}_follow_triplanar")
    roi.SetAndObserveTransformNodeID(tnode.GetID())

    lm = slicer.app.layoutManager()
    red = lm.sliceWidget("Red").mrmlSliceNode()
    yellow = lm.sliceWidget("Yellow").mrmlSliceNode()
    green = lm.sliceWidget("Green").mrmlSliceNode()

    def _update(*_) -> None:
        xr, yr, zr, pr = _slice_axes_and_point(red)
        xy, yy, zy, py = _slice_axes_and_point(yellow)
        xg, yg, zg, pg = _slice_axes_and_point(green)
        corner = _triple_plane_intersection(zr, pr, zy, py, zg, pg)
        axes = np.column_stack((xr, yr, zr))
        size = np.array(roi.GetSize(), dtype=float)
        m = _build_rt_from_axes_and_corner(axes, corner, size)
        tnode.SetMatrixTransformToParent(m)

    for sn in (red, yellow, green):
        sn.AddObserver(vtk.vtkCommand.ModifiedEvent, _update)
    _update()


# usage:
anchor_roi_corner_to_triplanar("R")
