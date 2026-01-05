import gzip
import xml.etree.ElementTree as ET

audio_file_path = '''D:/_MusicMaking/Ableton related files/Projects/Gigs/dump/Back of skoolbus.mp3'''
project_file_path = '''D:/_MusicMaking/Ableton related files/Projects/one_track Project/norelpath/norelpath.als'''
intermediate_file_path_out = '''D:/_MusicMaking/Ableton related files/Projects/one_track Project/norelpath/autosubbb'''

project_file_path_out = '''D:/_MusicMaking/Ableton related files/Projects/one_track Project/norelpath/norelpath.als'''
XPath = "./LiveSet/Tracks/AudioTrack/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip/SampleRef/FileRef/Path"
RelPathType_XPath = "./LiveSet/Tracks/AudioTrack/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip/SampleRef/FileRef/RelativePathType"
Rel_XPath = "./LiveSet/Tracks/AudioTrack/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip/SampleRef/FileRef/RelativePath"



xml_bytes = None

with gzip.open(project_file_path, "rb") as project:
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
        print(pathTag.attrib)
        print(root.find(XPath).attrib)
    else:
        print("Not found")

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