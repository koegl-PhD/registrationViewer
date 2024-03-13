from slicer import vtkMRMLScalarVolumeNode


def printVolumeName(volume: vtkMRMLScalarVolumeNode) -> None:

    print(f"Volume name: {volume.GetName()}")
