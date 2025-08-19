import SimpleITK as sitk
import numpy as np
import slicer

def apply_red_white_blue_lookup_table(volume_node):
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
        elif i == 31:
            # Value 31 = White
            lookup_table.SetTableValue(i, 1.0, 1.0, 1.0, 1.0)
        elif i == 255:
            # Value 255 = Blue
            lookup_table.SetTableValue(i, 0.0, 0.0, 1.0, 1.0)
        else:
            # Interpolate between the key points
            if i < 31:
                # Interpolate between red (1) and white (31)
                t = (i - 1) / (31 - 1)  # Normalized position between 1 and 31
                r = 1.0
                g = t
                b = t
            else:
                # Interpolate between white (31) and blue (255)
                t = (i - 31) / (255 - 31)  # Normalized position between 31 and 255
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

def apply_three_color_labelmap(volume_node):
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
        labelmap_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
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
    
    return labelmap_node

ref = getNode("LungCT_0001_0001")
new_transform = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTransformNode")
tx = getNode("LungCT_0001_0001 to LungCT_0001_0000")
slicer.modules.transforms.logic().ConvertToGridTransform(tx, ref, new_transform)
arr = slicer.util.arrayFromGridTransform(new_transform)


sitk_displacement_field = sitk.GetImageFromArray(arr, isVector=True)
jacobian_det_volume = sitk.DisplacementFieldJacobianDeterminant(sitk_displacement_field)
jacobian_det_arr = sitk.GetArrayFromImage(jacobian_det_volume)
jacobian_node = slicer.mrmlScene.CopyNode(ref)
jacobian_node.SetName("jacobian_node")
slicer.util.updateVolumeFromArray(jacobian_node, jacobian_det_arr)
jacobian_node.GetDisplayNode().AutoThresholdOn()


min_val = np.min(jacobian_det_arr)
max_val = np.max(jacobian_det_arr)

zero_label = np.round(1 + (0 - min_val) * (255 - 1) / (max_val - min_val)).astype(np.uint8)
one_label = np.round(1 + (1 - min_val) * (255 - 1) / (max_val - min_val)).astype(np.uint8)

jacobian_det_arr_label = np.round(
    1 + (jacobian_det_arr - min_val) * (255 - 1) / (max_val - min_val)
).astype(np.uint8)
jacobian_node_label = slicer.mrmlScene.CopyNode(ref)
jacobian_node_label.SetName("jacobian_node_label")
slicer.util.updateVolumeFromArray(jacobian_node_label, jacobian_det_arr_label)
label_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
label_node.SetName("label_node")
slicer.modules.volumes.logic().CreateLabelVolumeFromVolume(slicer.mrmlScene, label_node, jacobian_node_label)
apply_red_white_blue_lookup_table(label_node)


jacobian_det_arr_discrete = np.zeros_like(jacobian_det_arr)
jacobian_det_arr_discrete[jacobian_det_arr >= 1] = 2
jacobian_det_arr_discrete[(jacobian_det_arr >= 0) & (jacobian_det_arr < 1)] = 1
jacobian_det_arr_discrete[jacobian_det_arr < 0] = 0
jacobian_node_discrete = slicer.mrmlScene.CopyNode(ref)
jacobian_node_discrete.SetName("jacobian_node_discrete")
slicer.util.updateVolumeFromArray(jacobian_node_discrete, jacobian_det_arr_discrete)
discrete_label_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
discrete_label_node.SetName("discrete_label_node")
slicer.modules.volumes.logic().CreateLabelVolumeFromVolume(slicer.mrmlScene, discrete_label_node, jacobian_node_discrete)
apply_three_color_labelmap(discrete_label_node)