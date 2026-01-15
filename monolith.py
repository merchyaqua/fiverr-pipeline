import gzip
import xml.etree.ElementTree as ET
import os

# Source - https://stackoverflow.com/a
# Posted by tomvodi, modified by community. See post 'Timeline' for change history
# Retrieved 2026-01-15, License - CC BY-SA 4.0

# import tkinter as tk
# from tkinter import filedialog

# root = tk.Tk()
# root.withdraw()

# file_path = filedialog.askopenfilename()


audio_file_path = '''D:/_MusicMaking/Ableton related files/Projects/Gigs/dump/Back of skoolbus.mp3'''
template_project_file_path = '''D:/_MusicMaking/Ableton related files/Projects/one_track Project/norelpath/template.als'''

intermediate_file_path_out = '''D:/_MusicMaking/Ableton related files/Projects/one_track Project/norelpath/intermediate'''
project_file_path_out = '''D:/_MusicMaking/Ableton related files/Projects/one_track Project/norelpath/output.als'''


# XML paths to the tags to be modified
XPath = "./LiveSet/Tracks/AudioTrack/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip/SampleRef/FileRef/Path"
RelPathType_XPath = "./LiveSet/Tracks/AudioTrack/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip/SampleRef/FileRef/RelativePathType"
Rel_XPath = "./LiveSet/Tracks/AudioTrack/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip/SampleRef/FileRef/RelativePath"



xml_bytes = None

with gzip.open(template_project_file_path, "rb") as project:
    xml_bytes = project.read()
    xml_string = xml_bytes.decode('utf-8')
    
    # '''Replaces the first audio clip of the first audio track found to the new audio. File path'''

    root = ET.fromstring(xml_string)

    pathTag = root.find(XPath)
    relPathTypeTag = root.find(RelPathType_XPath)
    relPathTag = root.find(Rel_XPath)

    # print(pathTag.attrib)
    if pathTag is not None:
        pathTag.set("Value", audio_file_path)
        relPathTypeTag.set("Value", '0')
        relPathTag.set("Value", '')
        # print(pathTag.attrib)
        # print(root.find(XPath).attrib)
    else:
        print("No audio clips in template")

    tree = ET.ElementTree(root)
    # xml_string = ET.tostring(root, encoding='unicode', xml_declaration=True)
    tree.write(intermediate_file_path_out, xml_declaration=True)
    # xml_bytes = xml_string.encode('utf-8')
    
# with gzip.open(project_file_path_out, 'wb') as new_project:
#     # new_project.write(xml_bytes)
#     new_project.write()
import shutil
with open(intermediate_file_path_out, 'rb') as f_in:
    with gzip.open(project_file_path_out, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)


os.startfile(project_file_path_out)