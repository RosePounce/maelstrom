; Windows installer - compiled by Inno Setup 6 (iscc.exe).
; The version is passed on the command line: iscc /DVersion=1.2.3 installer.iss

#ifndef Version
  #define Version "0.0.0-dev"
#endif
#define Name "Maelstrom"
#define Exe "Maelstrom.exe"

[Setup]
; Never change the AppId: a new version must update the installed one, not
; install itself a second time.
AppId={{3B707F24-46D2-4287-ADCF-B0C3FE12FEFC}
AppName={#Name}
AppVersion={#Version}
AppPublisher=RosePounce
DefaultDirName={autopf}\Maelstrom
DefaultGroupName={#Name}
DisableProgramGroupPage=yes
; "lowest": install into the user folder, without asking for administrator
; rights. The player has nothing to confirm.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\dist
OutputBaseFilename=Maelstrom-{#Version}-setup
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\{#Exe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
french.DesktopIcon=Créer un raccourci sur le Bureau
french.Shortcuts=Raccourcis :
french.Uninstall=Désinstaller
english.DesktopIcon=Create a desktop shortcut
english.Shortcuts=Shortcuts:
english.Uninstall=Uninstall

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; \
    GroupDescription: "{cm:Shortcuts}"

[Files]
Source: "..\..\dist\Maelstrom\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Name}"; Filename: "{app}\{#Exe}"
Name: "{group}\{cm:Uninstall} {#Name}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Name}"; Filename: "{app}\{#Exe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#Exe}"; Description: "{cm:LaunchProgram,{#Name}}"; \
    Flags: nowait postinstall skipifsilent
