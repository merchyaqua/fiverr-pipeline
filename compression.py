audio_file_path = '''D:/_MusicMaking/Ableton related files/Projects/Gigs/dump/Back of skoolbus.mp3'''
project_file_path = '''D:/_MusicMaking/Ableton related files/Projects/one_track Project/one_track_gzip_xml/one_track_gzip_xml.als'''
project_file_path_out = '''D:/_MusicMaking/Ableton related files/Projects/one_track Project/one_track_gzip_xml/autosub.als'''

import gzip
def get_xml_text(path) -> str:
    with gzip.open(path, "rb") as project:
        project_content = project.read()
        return project_content.decode("utf-8")
        
def write_xml_to_als(xml_bytes, path):
    # xml_bytes = xml_string.encode("utf-8")
    with gzip.open(path, 'wb', 6) as project:
        project.write(xml_bytes)

string = get_xml_text(project_file_path)
# print(string)
# write_xml_to_als(string, project_file_path_out)



def replace_sample_audio(xml, new_audio_path):
    '''Replaces the first audio clip of the first audio track found to the new audio. File path'''

    import xml.etree.ElementTree as ET

    tree = ET.fromstring(xml)
    tree = ET.ElementTree(tree)
    identifier = "./LiveSet/Tracks/AudioTrack/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip/SampleRef/FileRef/Path"
    pathTag = tree.find(identifier)
    print(pathTag.attrib)
    if pathTag is not None:
        pathTag.set("Value", audio_file_path)
        print(pathTag.attrib)
        print(tree.find(identifier).attrib)
        
        elem = tree.getroot()
        test = ET.tostring(elem)
        return test
    else:
        print("Not found")
    

bytestring = replace_sample_audio(string, audio_file_path)
# print("Back" in newstring) # proves it works.

write_xml_to_als(bytestring, project_file_path_out)
