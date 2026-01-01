audio_file_path = '''D:/_MusicMaking/Ableton related files/Projects/Gigs/dump/Back of skoolbus.mp3'''
project_file_path = '''D:/_MusicMaking/Ableton related files/Projects/Saturday Night/nyc Project/nyc.als'''
project_file_path_out = '''D:/_MusicMaking/Ableton related files/Projects/one_track Project/one_track_gzip_xml.als'''

import gzip
def get_xml_text(path) -> str:
    with gzip.open(path, "rb") as project:
        project_content = project.read()
        return project_content.decode("utf-8")
        
def write_xml_to_als(xml_string: str, path):
    xml_bytes = xml_string.encode("utf-8")
    with gzip.open(path, 'wb', 6) as project:
        project.write(xml_bytes)

string = get_xml_text(project_file_path)
print(string)
write_xml_to_als(string, project_file_path_out)