import winreg
import win32com.client

def get_desktop():
    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                       r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    return winreg.QueryValueEx(k, "Desktop")[0]

shell = win32com.client.Dispatch("WScript.Shell")
lnk = get_desktop() + "\\Fiverr Pipeline.lnk"
sc = shell.CreateShortcut(lnk)
sc.TargetPath = r"D:\_CodingProjects\fiverr-pipeline\launch.vbs"
sc.WorkingDirectory = r"D:\_CodingProjects\fiverr-pipeline"
sc.IconLocation = r"D:\_MusicMaking\Ableton related files\Projects\one_track Project\template_project\Ableton Project Info\AProject.ico"
sc.Description = "Fiverr Pipeline watcher"
sc.Save()
print(f"Shortcut created at: {lnk}")
