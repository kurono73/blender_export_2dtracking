bl_info = {
    "name": "Export 2D Tracking Data",
    "author": "Tanawat Wattanachinda (tanawat.w@gmail.comm)",
    "version": (3, 6, 0),
    "blender": (2, 77, 0),
    "location": "File > Export > 2D Tracking data (.txt)",
    "description": "Export 2D tracking data into .txt",
    "warning": "",
    "wiki_url": "",
    "category": "Import-Export",
    }
'''
version 3.6 fix:
    -export to pftrack format
version 3.5 fix:
    -export to 3dequlizer format
version 3.4.1 fix:
    -gui for toggle between frame A and B
version 3.4.0 fix:
    -gui for goto next keyframe and previous keyframe 
version 3.3.1 fix:
    -fix all duplication case
version 3.3 fix:
    -support detection in case 1 or 2 duplication
version 3.2 fix:
    -more accurate for remove duplicate
version 3.1 fix:
    -remove duplicate frame when tracking not start 0 or 1
version 3 fix:
    -can offset the frame before write data to syntheye
    -can remove duplicate frame 
'''

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty
from bpy.types import Operator
import bpy, time, os, sys
addon_keymaps = []

class MyPanel(bpy.types.Panel):
    """A Menu for Navigate to Next Keyframe and Previeus Keyframe"""
    bl_label = "Tracker Control"
    bl_space_type = 'CLIP_EDITOR'
    bl_region_type = 'TOOLS'
    bl_category = "Track"
    bpy.types.Scene.frame_a = bpy.props.IntProperty(name = "Frame A",description="toggle start frame",default=0)
    bpy.types.Scene.frame_b = bpy.props.IntProperty(name = "Frame B",description="toggle end frame",default=0)

    #state=0,wait to set frame A
    #state=1,wait to set frame B
    #state=2,toggle
    bpy.types.Scene.state = bpy.props.IntProperty(name = "State",default=0)



    def draw(self, context):
         layout = self.layout
         row = layout.row()
         #row.label(text="Test")

         #row.operator("clip.tracker_previous_keyframe", text="",icon='PREV_KEYFRAME')
         #row.operator("clip.tracker_next_keyframe", text="",icon='NEXT_KEYFRAME')
         row.prop(context.scene,"frame_a")

         row = layout.row()
         row.prop(context.scene,"frame_b")

         row = layout.row()
         row.operator("clip.tracker_toggle_reset", text="RESET")

         bpy.context.scene['frame_a'] = 0
         bpy.context.scene['frame_b'] = 0
         bpy.context.scene['state'] = 0

class ToggleFrame(Operator):
    """toggle frame between A and B"""
    bl_idname = "clip.tracker_toggle_frame"
    bl_label = "toggle frame"

    def execute(self,context):
         return toggleframeOpt()

class ToggleReset(Operator):
    """reset frame toggle"""
    bl_idname = "clip.tracker_toggle_reset"
    bl_label = "reset frame toggle"

    def execute(self,context):
         return toggelresetOpt()

class NextKeyframe(Operator):
    """jump to next keyframe"""
    bl_idname = "clip.tracker_next_keyframe"
    bl_label = "Jump to Next Keyframe"

    def execute(self,context):
         return getNextKeyframeOpt()

class PreviousKeyframe(Operator):
    """jump to previous keyframe"""
    bl_idname = "clip.tracker_previous_keyframe"
    bl_label = "Jump to Previous Keyframe"

    def execute(self,context):
         return getPreviousKeyframeOpt()

class Export2DTrackingData(Operator, ExportHelper):
    """Export 2D tracking data into .txt"""
    bl_idname = "export_data.tracking"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export 2D Tracking Data"

    # ExportHelper mixin class uses this
    filename_ext = ".txt"

    filter_glob = StringProperty(
            default="*.txt",
            options={'HIDDEN'},
            maxlen=255,  # Max internal buffer length, longer would be clamped.
            )

    space = EnumProperty(
            name="Coordinate Space",
            description="Choose between 3 space (UV, Screen, Syntheys)",
            items=(('uv', "Uv Space", "export to uv space (0,1)"),
                   ('screen', "Screen Space", "export to screen space (lef-upper=(0,0), right-lower(width,high))"),
                   ('3dequalizer', "3de format", "export to 3de format"),
                   ('pftrack', "pftrack format", "export to pftrack format"),                      
                   ('syntheys', "Syntheys format", "export to format that syntheys support (center 0,0)")),
            default='syntheys',
            )
    frame_offset = IntProperty(
            name="Frame Offset",
            description="Value to offset frame (By default, use -1 to export to Syntheye)",
            default=-1,
            )      
            
    delete_duplicate = BoolProperty(
            name="Delete Duplicate Tracking Data",
            description="Blender usaully keep value double in first and last tracking stream, but it may cause the problem with other external program. True to delete the duplicate",
            default=True,
            )                    

    def execute(self, context):
        return main(self.filepath, self.space, self.frame_offset, self.delete_duplicate)

def toggleframeOpt():
    if bpy.context.scene.state==0:
         print('set frame A')
         bpy.context.scene['frame_a'] = bpy.context.screen.scene.frame_current
         bpy.context.scene['state'] = 1
    elif bpy.context.scene.state==1:
         print('set frame B')
         bpy.context.scene['frame_b'] = bpy.context.screen.scene.frame_current
         bpy.context.scene['state'] = 2
    elif bpy.context.scene.state==2:
         print('toogle')
         current_frame = bpy.context.screen.scene.frame_current
         if current_frame == bpy.context.scene.frame_a:
              bpy.context.screen.scene.frame_current = bpy.context.scene.frame_b
         else:
              bpy.context.screen.scene.frame_current = bpy.context.scene.frame_a

    return {'FINISHED'}

def toggelresetOpt():
    bpy.context.scene['frame_a'] = 0
    bpy.context.scene['frame_b'] = 0
    bpy.context.scene['state'] = 0

    return {'FINISHED'}

def getNextKeyframeOpt():
    print('jump to next keyframe')
    track_active = bpy.context.space_data.clip.tracking.tracks.active
    current_frame = bpy.context.screen.scene.frame_current
    current_frame_use = current_frame
    start_frame = bpy.context.screen.scene.frame_start
    end_frame = bpy.context.screen.scene.frame_end
    
    current_frame_use += 1
    while current_frame_use <= end_frame:
         try:
              current_track = track_active.markers.find_frame(current_frame_use)
              if current_track.is_keyed:
                   bpy.context.screen.scene.frame_current = current_frame_use
                   break
              else:
                   current_frame_use += 1
         except:
              current_frame_use += 1

    return {'FINISHED'}

def getPreviousKeyframeOpt():
    print('jump to previous keyframe')
    track_active = bpy.context.space_data.clip.tracking.tracks.active
    current_frame = bpy.context.screen.scene.frame_current
    current_frame_use = current_frame
    start_frame = bpy.context.screen.scene.frame_start
    end_frame = bpy.context.screen.scene.frame_end
    
    current_frame_use -= 1
    while current_frame_use >= start_frame:
         try:
              current_track = track_active.markers.find_frame(current_frame_use)
              if current_track.is_keyed:
                   bpy.context.screen.scene.frame_current = current_frame_use
                   break
              else:
                   current_frame_use -= 1
         except:
              current_frame_use -= 1

    return {'FINISHED'}

def getCoordinate(co, coordinate_space, video_size):
    if coordinate_space=='uv':
        return co
    elif coordinate_space=='screen':
        return [float(co[0]*video_size[0]), float(video_size[1]-(co[1]*video_size[1]))]  
    elif coordinate_space=='syntheys':
        return [co[0]*2-1, (-1)*(co[1]*2-1)]
    elif coordinate_space in ['3dequalizer', 'pftrack']:
        return [float(co[0]*video_size[0]), float(co[1]*video_size[1])]     

def getActiveClip():
    for area in bpy.context.screen.areas:
        if area.type == 'CLIP_EDITOR' and area.spaces[0].clip is not None:
            return area.spaces[0].clip

def isRecordEquals(a,b):
    a_split = a.split()
    b_split = b.split()
    return a_split[2]==b_split[2] and a_split[3]==b_split[3]

def isRecordStatusEquals(a,b):
    a_split = a.split()
    b_split = b.split()
    return a_split[-1] == b_split[-1]

def getStatus(a):
    return a.split()[-1].strip()

def getFrame(a):
    #return a.split()[1].strip()
    try:
         return int(a.split()[1].strip())
    except:
         return 'data delete, invalid frame'


def deleteDuplicateData(tL):
    duplication_index_list = []
    for i in range(len(tL)):

        #delete reocrd?
        if tL[i]==0:
             #print('111 delete record frame: [{0}],i:[{1}]'.format( getFrame(tL[i]),i ))
             continue

        #last reocrd?
        if i==len(tL)-1:
             #print('116 last record frame: [{0}]'.format(getFrame(tL[i])))
             break

        #case D:1/2/n duplicate in first of file
        if i==0:
             j = i
             while True:
                  try:
                       if isRecordEquals(tL[j],tL[j+1]):
                            #print('125 case duplicate in first of file')
                            #print('126 frame [{0}] == [{1}]'.format( getFrame(tL[j]), getFrame(tL[j+1]) ))
                            #print('127 delete frame [{0}]'.format( getFrame(tL[j]) ))
                            duplication_index_list.append(j)
                            tL[j] = 0
                            j = j+1
                       else:
                            break
                  except:
                       break
             continue

        #case A.1: 3 last duplication
        #case A.2: 2 last duplication
        current_i = i
        j = i
        while True:
             try:
                  if isRecordEquals(tL[j],tL[j+1]):
                       #print('144 case duplicate in middle of file')
                       #print('145 frame [{0}] == [{1}]'.format( getFrame(tL[j]), getFrame(tL[j+1]) ))
                       j = j+1
                  else:
                       #no duplicate?
                       if j == current_i:
                            #print('150 no duplicate in frame [{0}]'.format( getFrame(tL[j]) ))
                            break
                       else:
                            #print('153 duplicate from frame [{0}] to [{1}]'.format( getFrame(tL[current_i]), getFrame(tL[j]) ))
                            duplication_number = abs(j-current_i)
                            #check from next record
                            #if next record's frame continue from j, 
                            #this duplication in the stream header in middle file (case C)
                            #otherwise, in the stream footer in middle file (case B)
                            current_j_frame = getFrame(tL[j])
                            next_frame = getFrame(tL[j+1])
                            #print('161 curent_j_frame : {0}, next_frame : {1}'.format(current_j_frame, next_frame))
                            if abs(next_frame - current_j_frame)==1:
                                 #case C
                                 #delete record from current_i to j-1 (not include j)
                                 #print('165 case C')
                                 while current_i < j:
                                      duplication_index_list.append(current_i)
                                      tL[current_i] = 0 #insert while debug
                                      #print('169 delete frame [{0}], current_i : {1}'.format( getFrame(tL[current_i]), current_i))
                                      current_i = current_i + 1
                            else:
                                 #case B
                                 #delete reocrd from j to current_i+1 (not include current_i)
                                 #print('174 case B')
                                 while j > current_i:
                                      cuplication_index_list.append(j)
                                      tL[j] = 0 #insert while debug
                                      #print('178 delete frame [{0}]'.format( getFrame(tL[j])))
                                      j = j-1
                            break
             except:
                  #cause error in case : j is last record, duplication occur in last record of file (may be 1 2 or n)
                  #j is current last record?
                  #print('exception messge: {0}'.format(sys.exc_info()))
                  if j == current_i:
                       #print('185 j({0}) is last record and no duplicate, current_i({1})'.format(j,current_i))
                       break
                  #duplication occur?
                  else:
                       #get number of duplication
                       #print('190 duplication from frame [{0}] to [{1}]'.format( getFrame(tL[current_i]), getFrame(tL[j])))
                       duplication_number = abs(j-current_i)
                       while duplication_number>0:
                            duplication_index_list.append(current_i+duplication_number)
                            tL[current_i+duplication_number] = 0
                            #print('195 delete frame [{0}]'.format( getFrame(tL[current_i+duplication_number])))
                            duplication_number = duplication_number-1
                       break

        #case B.1: 3 duplicate in last stream in middle file
        #case B.2: 2 duplicate in last stream in middle file
        
        #case C.1: 3 duplicate in first stream in middle file
        #case C.2: 2 duplicate in first stream in middle file


    
    #delete duplciate item
    #for delete_index in list(set(duplication_index_list)):
        #del tL[delete_index]
        #tL[delete_index] = 0
    tL = filter(lambda x: x != 0, tL)
        
    return tL

def main(filepath, space, frameOffset ,deleteDuplicate):      
    t1 = time.time()
    D = bpy.data
    coordinate_space = space # 'uv' or 'screen'
    all_clip = False #True=export all video clip,False=export only current video clip
    fn = filepath
    frame_end = bpy.context.screen.scene.frame_end
    textList = []

    clip_list = D.movieclips if all_clip else [getActiveClip()]
    number_of_clip = 1

    for clip in clip_list:
        f = open(fn,'w')

        if space == 'pftrack':
            trackersDict = {}
            #EXAMPLE#
            #{'tracker name': {'frame no.':[x,y], 'frame no.':[x,y], 'frame no.':[x,y]}, 'tracker name': {}, }
            #{'tracker': {'1':[1900,1500], '2':[1905,1505], '3':[1910,1510]}, 'tracker.002': {}, }
            #all_trackers_name = trackersDict.keys()
            #number_of_trackers = len(trackersDict.keys())
            #number_of_visible_frame = len(trackersDict[tracker_name].keys())

            #prepare old style data to delete duplicate before#
            textList_old = []
            for track in clip.tracking.tracks:
                frameno = 0
                while frameno<=frame_end:
                    markerAtFrame = track.markers.find_frame(frameno)                                
                    if markerAtFrame:
                        #break
                        coords = getCoordinate(markerAtFrame.co.xy, coordinate_space, clip.size)
                        
                        currentframe = frameno+frameOffset
                        if currentframe>=0:
                            text = '{0} {1} {2} {3} {4}\n'.format(track.name, currentframe, coords[0], coords[1], 15 if markerAtFrame.is_keyed else 7  )
                            textList_old.append(text)
                            #f.write(text)
                    frameno += 1

            if deleteDuplicate:
                textList_old = deleteDuplicateData(textList_old) 

            #textList_old = textList_old.split()
            for track in textList_old:
                track = track.split()
                #if no 'track' in trackersDict, keep it
                track_name = track[0]
                if not track_name in trackersDict.keys():
                    trackersDict[track_name] = {}

                #frameno = 0
                #while frameno<=frame_end:
                #    markerAtFrame = track.markers.find_frame(frameno)                                
                #    if markerAtFrame:
                        #break
                #coords = getCoordinate(markerAtFrame.co.xy, coordinate_space, clip.size)
                coords = [ track[2], track[3]]
                        
                #        currentframe = frameno+frameOffset
                #        if currentframe>=0:
                            #text = '{0} {1} {2} {3} {4}\n'.format(track.name, currentframe, coords[0], coords[1], 15 if markerAtFrame.is_keyed else 7  )
                currentframe = int(track[1])
                trackersDict[track_name][currentframe] = [coords[0], coords[1]]
                            #textList.append(text)
                            #f.write(text)
                #    frameno += 1

            #prepare data from dict to write to disk
            number_of_trackers = len(trackersDict.keys())
            #textList.append(str(number_of_trackers)+'\n') #number of trackers#

            tracker_list_sort = list(trackersDict.keys())
            tracker_list_sort.sort()

            for tracker in tracker_list_sort:
                tracker_name = tracker #Name
                textList.append('\"'+str(tracker_name)+'\"\n')

                clip_number = number_of_clip #clipNumber
                textList.append(str(clip_number)+'\n')

                frame_list_sort = list(trackersDict[tracker].keys())
                frame_list_sort.sort()
                frame_count = len(frame_list_sort) #frameCount
                textList.append(str(frame_count)+'\n')

                for frame in frame_list_sort:
                    tracker_frame_coor_current = trackersDict[tracker][frame]
                    frame_no = str(frame)
                    x = str(tracker_frame_coor_current[0])
                    y = str(tracker_frame_coor_current[1])
                    text = '{0} {1} {2} 1'.format(frame_no, x, y) #data record
                    textList.append(str(text)+'\n')

        elif space == '3dequalizer':
            trackersDict = {}
            #EXAMPLE#
            #{'tracker name': {'frame no.':[x,y], 'frame no.':[x,y], 'frame no.':[x,y]}, 'tracker name': {}, }
            #{'tracker': {'1':[1900,1500], '2':[1905,1505], '3':[1910,1510]}, 'tracker.002': {}, }
            #all_trackers_name = trackersDict.keys()
            #number_of_trackers = len(trackersDict.keys())
            #number_of_visible_frame = len(trackersDict[tracker_name].keys())

            #prepare old style data to delete duplicate before#
            textList_old = []
            for track in clip.tracking.tracks:
                frameno = 0
                while frameno<=frame_end:
                    markerAtFrame = track.markers.find_frame(frameno)                                
                    if markerAtFrame:
                        #break
                        coords = getCoordinate(markerAtFrame.co.xy, coordinate_space, clip.size)
                        #print('test1')
                        #print(coords)
                        
                        currentframe = frameno+frameOffset
                        #print('test2')
                        #print(currentframe)
                        if currentframe>=0:
                            text = '{0} {1} {2} {3} {4}\n'.format(track.name, currentframe, coords[0], coords[1], 15 if markerAtFrame.is_keyed else 7  )
                            textList_old.append(text)
                            #f.write(text)
                    frameno += 1

            if deleteDuplicate:
                textList_old = deleteDuplicateData(textList_old)                    

            #textList_old = textList_old.split()
            for track in textList_old:
                track = track.split()
                #if no 'track' in trackersDict, keep it
                track_name = track[0]
                if not track_name in trackersDict.keys():
                    trackersDict[track_name] = {}

                #frameno = 0
                #while frameno<=frame_end:
                #    markerAtFrame = track.markers.find_frame(frameno)                                
                #    if markerAtFrame:
                        #break
                #coords = getCoordinate(markerAtFrame.co.xy, coordinate_space, clip.size)
                coords = [ track[2], track[3]]
                        
                #        currentframe = frameno+frameOffset
                #        if currentframe>=0:
                            #text = '{0} {1} {2} {3} {4}\n'.format(track.name, currentframe, coords[0], coords[1], 15 if markerAtFrame.is_keyed else 7  )
                currentframe = int(track[1])
                trackersDict[track_name][currentframe] = [coords[0], coords[1]]
                            #textList.append(text)
                            #f.write(text)
                #    frameno += 1

            #prepare data from dict to write to disk
            number_of_trackers = len(trackersDict.keys())
            textList.append(str(number_of_trackers)+'\n') #number of trackers#

            tracker_list_sort = list(trackersDict.keys())
            tracker_list_sort.sort()

            for tracker in tracker_list_sort:
                tracker_name_current = tracker
                textList.append(tracker_name_current+'\n') #name#
                textList.append('0\n') #0
                
                frame_list_sort = list(trackersDict[tracker].keys())
                frame_list_sort.sort()
                textList.append(str(len(frame_list_sort))+'\n') #number of visible frames.#
                for frame in frame_list_sort:
                    tracker_frame_coor_current = trackersDict[tracker][frame]
                    frame_no = str(frame)
                    x = str(tracker_frame_coor_current[0])
                    y = str(tracker_frame_coor_current[1])
                    text = '{0} {1} {2}\n'.format(frame_no, x, y)
                    print(text)
                    textList.append(text)
                
        else:                    
            for track in clip.tracking.tracks:
                frameno = 0
                while frameno<=frame_end:
                    markerAtFrame = track.markers.find_frame(frameno)                                
                    if markerAtFrame:
                        #break
                        coords = getCoordinate(markerAtFrame.co.xy, coordinate_space, clip.size)
                        
                        currentframe = frameno+frameOffset
                        if currentframe>=0:
                            text = '{0} {1} {2} {3} {4}\n'.format(track.name, currentframe, coords[0], coords[1], 15 if markerAtFrame.is_keyed else 7  )
                            textList.append(text)
                            #f.write(text)
                    frameno += 1    
                
        print ("Data write to : {0}".format(os.path.abspath(fn)))
        number_of_clip += 1
    
    if deleteDuplicate and not space in ['3dequalizer', 'pftrack']:
        textList = deleteDuplicateData(textList)
        
    for line in textList:
        f.write(line)
    f.close()

    print ("Done : {0} s.".format(time.time()-t1))
    
    return {'FINISHED'}

# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(Export2DTrackingData.bl_idname, text="2D Tracking Data (.txt)")

addon_keymaps = []
def register():
    bpy.utils.register_class(Export2DTrackingData)
    bpy.utils.register_class(MyPanel)
    bpy.utils.register_class(NextKeyframe)
    bpy.utils.register_class(PreviousKeyframe)
    bpy.utils.register_class(ToggleReset)
    bpy.utils.register_class(ToggleFrame)
    bpy.types.INFO_MT_file_export.append(menu_func_export)

    #km = bpy.context.window_manager.keyconfigs.addon.keymaps.new(name='frame toggle',space_type='CLIP_EDITOR')

    km = bpy.context.window_manager.keyconfigs.default.keymaps['Clip']
    kmi = km.keymap_items.new('clip.tracker_toggle_frame', 'B', 'PRESS', ctrl=True)
    kmi = km.keymap_items.new('clip.tracker_toggle_reset', 'B', 'PRESS', shift=True, ctrl=True)
    kmi.active = True
    #kmi.properties.name = "CLIP_toggle_frame"
    addon_keymaps.append((km,kmi))


def unregister():
    bpy.utils.unregister_class(Export2DTrackingData)
    bpy.utils.unregister_class(MyPanel)
    bpy.utils.unregister_class(NextKeyframe)
    bpy.utils.unregister_class(PreviousKeyframe)
    bpy.utils.unregister_class(ToggleReset)
    bpy.utils.unregister_class(ToggleFrame)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)

    wm = bpy.context.window_manager
    for km,kmi in addon_keymaps:
         print(km)
         #wm.keyconfigs.default.keymaps.remove(km)
         km.keymap_items.remove(kmi)
    del addon_keymaps[:]

if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_data.tracking('INVOKE_DEFAULT')
