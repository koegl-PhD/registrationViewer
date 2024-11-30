
def on_reset_views(self) -> None:

    if self.synchronise_with_displacement_pressed:
        return

    current_view = self.node_crosshair.GetCursorPositionXYZ([
                                                            0]*3).GetName()

    position: list[float] = [0., 0., 0.]
    self.node_crosshair.GetCursorPositionRAS(position)

    if '1' in current_view:  # jump slices in 2 and 3
        # in plus views we should follow the cursor (that's why group 2)
        slicer.modules.markups.logic().JumpSlicesToLocation(position[0],
                                                            position[1],
                                                            position[2],
                                                            False,
                                                            self.group_second_row)
        slicer.modules.markups.logic().JumpSlicesToLocation(position[0],
                                                            position[1],
                                                            position[2],
                                                            False,
                                                            self.group_third_row)
    elif '2' in current_view:  # jump slices in 1 and 3
        slicer.modules.markups.logic().JumpSlicesToLocation(position[0],
                                                            position[1],
                                                            position[2],
                                                            False,
                                                            self.group_first_row)
        slicer.modules.markups.logic().JumpSlicesToLocation(position[0],
                                                            position[1],
                                                            position[2],
                                                            False,
                                                            self.group_third_row)

    elif '3' in current_view:  # jump slices in 1 and 2
        slicer.modules.markups.logic().JumpSlicesToLocation(position[0],
                                                            position[1],
                                                            position[2],
                                                            False,
                                                            self.group_first_row)
        slicer.modules.markups.logic().JumpSlicesToLocation(position[0],
                                                            position[1],
                                                            position[2],
                                                            False,
                                                            self.group_second_row)

    self.crosshair.offset_diffs = self.current_offset = [0, 0, 0]
