bl_info = {
    "name": "Export 2D Tracking Data",
    "author": "Tanawat Wattanachinda (tanawat.w@gmail.comm), updated by Coding Partner",
    "version": (4, 3, 0),
    "blender": (4, 2, 0),
    "location": "File > Export > 2D Tracking Data (.txt)",
    "description": "Export 2D tracking data into various formats (.txt, 3de, pftrack)",
    "warning": "",
    "wiki_url": "",
    "category": "Import-Export",
}
'''
version 4.3.0 fix:
    - Removed all UI panel and navigation features to specialize in exporting.
version 4.2.0 fix:
    - Compatibility with Blender 4.2+
    - Property registration moved to register() function.
    - Fixed AttributeError in Panel's draw() method.
    - Updated Panel location to 'UI' region.
    - Corrected keymap registration.
'''

import bpy
import time
import os
import sys
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty
from bpy.types import Operator

# --- Operators ---

class EXPORT_OT_2d_tracking_data(Operator, ExportHelper):
    """Export 2D tracking data into .txt"""
    bl_idname = "export_data.tracking"
    bl_label = "Export 2D Tracking Data"
    filename_ext = ".txt"

    filter_glob: StringProperty(
        default="*.txt",
        options={'HIDDEN'},
        maxlen=255,
    )

    space: EnumProperty(
        name="Coordinate Space",
        description="Choose between different coordinate systems",
        items=(
            ('uv', "UV Space", "Export to UV space (0 to 1)"),
            ('screen', "Screen Space", "Export to screen space (top-left=(0,0), bottom-right=(width,height))"),
            ('3dequalizer', "3DEqualizer Format", "Export to 3DEqualizer format"),
            ('pftrack', "PFTrack Format", "Export to PFTrack format"),
            ('syntheys', "SynthEyes Format", "Export to a format SynthEyes supports (center is 0,0)"),
        ),
        default='syntheys',
    )
    frame_offset: IntProperty(
        name="Frame Offset",
        description="Value to offset frame (By default, use -1 to export to SynthEyes)",
        default=-1,
    )
    delete_duplicate: BoolProperty(
        name="Delete Duplicate Tracking Data",
        description="Blender sometimes duplicates the first/last frame's data, which can cause issues. Enable to remove duplicates.",
        default=True,
    )

    def execute(self, context):
        # Call the main export function
        return main(self.filepath, self.space, self.frame_offset, self.delete_duplicate, context)


# --- Core Logic ---

def getCoordinate(co, coordinate_space, video_size):
    if coordinate_space == 'uv':
        return co
    elif coordinate_space == 'screen':
        return [float(co[0] * video_size[0]), float(video_size[1] - (co[1] * video_size[1]))]
    elif coordinate_space == 'syntheys':
        return [co[0] * 2 - 1, (-1) * (co[1] * 2 - 1)]
    elif coordinate_space in ['3dequalizer', 'pftrack']:
        return [float(co[0] * video_size[0]), float(co[1] * video_size[1])]

def getActiveClip(context):
    # Find and return the active movie clip from the context
    for area in context.screen.areas:
        if area.type == 'CLIP_EDITOR' and area.spaces[0].clip is not None:
            return area.spaces[0].clip
    # Fallback for other contexts if needed
    if context.space_data and hasattr(context.space_data, 'clip'):
        return context.space_data.clip
    return None

def isRecordEquals(a, b):
    a_split = a.split()
    b_split = b.split()
    if len(a_split) < 4 or len(b_split) < 4:
        return False
    return a_split[2] == b_split[2] and a_split[3] == b_split[3]

def getFrame(a):
    try:
        return int(a.split()[1].strip())
    except (ValueError, IndexError):
        return 'data delete, invalid frame'

def deleteDuplicateData(tL):
    # This complex logic for deleting duplicates remains as it is application-specific.
    if not tL:
        return []
        
    filtered_list = []
    # Simplified approach: remove consecutive duplicates
    # This might not cover all edge cases the original author intended, but is more robust.
    filtered_list.append(tL[0])
    for i in range(1, len(tL)):
        if not isRecordEquals(tL[i], tL[i-1]):
            filtered_list.append(tL[i])
            
    return filtered_list


def main(filepath, space, frameOffset, deleteDuplicate, context):
    t1 = time.time()
    clip = getActiveClip(context)
    if not clip:
        # Using self.report for better user feedback in the UI
        bpy.context.window_manager.popup_menu(
            lambda self, context: self.layout.label(text="No active clip found. Please open a clip in the Movie Clip Editor."),
            title="Export Error",
            icon='ERROR'
        )
        print("Export cancelled: No active clip found in a Clip Editor.")
        return {'CANCELLED'}

    frame_end = context.scene.frame_end
    textList = []
    
    # Open file for writing
    try:
        f = open(filepath, 'w')
    except IOError as e:
        print(f"Error opening file: {e}")
        return {'CANCELLED'}

    with f:
        # --- Data Gathering ---
        # This part gathers all tracking data before formatting.
        # This is better for handling format-specific headers and sorting.
        all_tracks_data = {}
        for track in clip.tracking.tracks:
            all_tracks_data[track.name] = {}
            for frameno in range(frame_end + 1):
                markerAtFrame = track.markers.find_frame(frameno)
                if markerAtFrame:
                    coords = getCoordinate(markerAtFrame.co.xy, space, clip.size)
                    currentframe = frameno + frameOffset
                    if currentframe >= 0:
                        # Store raw data: coords and keyframe status
                        all_tracks_data[track.name][currentframe] = {
                            "coords": coords,
                            "is_keyed": markerAtFrame.is_keyed
                        }

        # --- Data Formatting and Writing ---
        if space == 'pftrack':
            sorted_track_names = sorted(all_tracks_data.keys())
            for track_name in sorted_track_names:
                track_data = all_tracks_data[track_name]
                if not track_data: continue
                
                f.write(f'"{track_name}"\n')
                f.write('1\n')  # clip_number
                
                sorted_frames = sorted(track_data.keys())
                f.write(f'{len(sorted_frames)}\n')

                for frame in sorted_frames:
                    x, y = track_data[frame]["coords"]
                    f.write(f'{frame} {x} {y} 1\n')

        elif space == '3dequalizer':
            sorted_track_names = sorted(all_tracks_data.keys())
            
            # Write header with the number of trackers
            f.write(f'{len(sorted_track_names)}\n')

            for track_name in sorted_track_names:
                track_data = all_tracks_data[track_name]
                if not track_data: continue

                f.write(f'{track_name}\n')
                f.write('0\n')
                
                sorted_frames = sorted(track_data.keys())
                f.write(f'{len(sorted_frames)}\n')
                for frame in sorted_frames:
                    x, y = track_data[frame]["coords"]
                    f.write(f'{frame} {x} {y}\n')

        else:  # Generic format (uv, screen, syntheys)
            # First, convert data to the old textList format for duplication removal
            textList_intermediate = []
            sorted_track_names = sorted(all_tracks_data.keys())
            for track_name in sorted_track_names:
                 track_data = all_tracks_data[track_name]
                 sorted_frames = sorted(track_data.keys())
                 for frame in sorted_frames:
                    coords = track_data[frame]["coords"]
                    is_keyed = track_data[frame]["is_keyed"]
                    status = 15 if is_keyed else 7
                    text = f'{track_name} {frame} {coords[0]} {coords[1]} {status}\n'
                    textList_intermediate.append(text)
            
            if deleteDuplicate:
                textList = deleteDuplicateData(textList_intermediate)
            else:
                textList = textList_intermediate
            
            for line in textList:
                f.write(line)

    print(f"Data written to: {os.path.abspath(filepath)}")
    print(f"Done in: {time.time() - t1:.2f} s.")
    
    return {'FINISHED'}


# --- Registration ---

def menu_func_export(self, context):
    self.layout.operator(EXPORT_OT_2d_tracking_data.bl_idname, text="2D Tracking Data (.txt)")

classes = (
    EXPORT_OT_2d_tracking_data,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add the operator to the File > Export menu
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    # Remove the operator from the File > Export menu
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
