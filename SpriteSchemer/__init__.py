# Blender script
#
# Put dir with this file (__init__.py) under scripts/startup and restart
#     blender
# Before invoking with F3 (search for spriteschemer)
#     Mark the single object that we will rotate. Other mesh objects
#          may need to be reparented to this one
#     Define a custom _String property 'SP_Name' at the bottom of Object Properties
#          (not Object Data Properties...) for the top level object and set it to
#           a string that should be the stem of generated image names.
#     Set the number of angles in a custom integer property 'SP_NumAngles'
#     Adjust camera and set to orthographic projection.
#     Mark Render Properties >> Film >> Transparent
#
# In the System Console Window one can view the file generation progress. The
# image output format is PNG and will be put in a subdirectory 'spritesheets'
# under the project path.
#
# For on-line sprite sheet generation see e.g.
#     https://codeshack.io/images-sprite-sheet-generator/

import bpy
import bpy_types
from idprop.types import IDPropertyArray
import random
import math
from math import pi
import os
from os.path import join as joinpath

print("*** Loading SpriteSchemer ***")
print("    Aurora Svanberg")

# Sources of inspiration to get some feed-back what is happening in the viewport.
# https://blender.stackexchange.com/questions/28673/update-viewport-while-running-script

class ModalTimerOperator(bpy.types.Operator):
    """Timer driven rotation and single image rendering"""

    ModuleName = "SpriteSchemer"

    PERIOD = 0.01  #  unit: seconds Controls how much we wait in the GUI between
                  #  each rendered frame. Lower for speedier operation.

    bl_idname = "wm.spriteschemer"
    bl_label = "Rotate/Animate Object and render still images"
    bl_info = {
        "name": ModuleName,
        "blender": (3, 0, 0),
        "category": "Render",
    }

    angleIter : bpy.props.IntProperty(default=0)
    _timer = None

    def modal(self, context: bpy_types.Context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'} or not self._jobs:
            self.cancel(context)
            # Reset the state to what we started with
            self._obj.rotation_euler[2] = self._orig_rot
            context.scene.frame_set(self._orig_frame)

            print("SpriteSchemer: Ready")
            return {'FINISHED'}

        if event.type == 'TIMER':
            # Pop one job
            rads, frame, filepath = self._jobs.pop(0)

            # Update object orientation and the frame in the timeline
            context.scene.frame_set(frame)
            self._obj.rotation_euler[2] = rads

            context.scene.render.filepath = filepath
            print(f"Rendering frame {filepath}.")

            # Render and store a single image
            bpy.ops.render.render(
                animation=False,
                write_still=True,
                use_viewport=False,
                layer='',
                scene=context.scene.name)

        return {'PASS_THROUGH'}

    def execute(self, context: bpy_types.Context):

        # We use the current marked object as the target of the rotations.
        # If this object does not have the custom property SP_Name we report
        # an error and aborts the operation.
        self._obj = context.object

        # Save original values so we can set them back after the rendering.
        self._orig_rot = self._obj.rotation_euler[2]
        self._orig_frame = context.scene.frame_current

        if 'SP_Name' not in self._obj:
            self.report(
                {'ERROR'},
                f"The marked object {self._obj.name} does not"
                " have the sprite sheet name property \"SP_Name\""
            )
            return {'FINISHED'}

        # Create the pattern for the image file path. Must contain two %d
        # format specifiers corresponding to angle number and animation frame.
        projpath = os.path.dirname(bpy.data.filepath) # .blend file location
        fileNamePattern = joinpath(
            projpath,
            "spritesheets",
            f"{self._obj.get('SP_Name')}_%04d_%04d"
        )

        # Create a list of tuples (radians, frame, filepath) where
        # each tuple represent a "render job" to be performed.
        # We will start a timer that will in each tick pop a job from this
        # list as long as it is non-empty.

        self._jobs = list()

        bpyintarr = self._obj.get('SP_AnimationFrames', None)
        if not bpyintarr:
            frames = [1]  # Render just first frame
        elif type(bpyintarr) is not IDPropertyArray:
            self.report(
                {'ERROR'},
                f"The SP_AnimationFrames property of {self._obj.name} "
                "does not seem to be an integer array"
            )
        else:
            frames = bpyintarr.to_list()

        numangles = self._obj.get('SP_NumAngles', 8)  # Defaults to 8
        angleoffset = math.radians(self._obj.get('SP_AngleOffset', 0.0))

        for i in range(numangles):
            rads = math.fmod(i * 2 * pi / numangles + self._orig_rot, 2 * pi)
            for j, f in enumerate(frames):  # j will count 0, 1, ...
                self._jobs.append((
                    rads + angleoffset,
                    f,
                    fileNamePattern % (i, j)
                ))

        # Create and start the timer
        wm = context.window_manager
        self._timer = wm.event_timer_add(time_step=self.PERIOD, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)


def register():
    bpy.utils.register_class(ModalTimerOperator)


def unregister():
    bpy.utils.unregister_class(ModalTimerOperator)


if __name__ == "__main__":
    register()
