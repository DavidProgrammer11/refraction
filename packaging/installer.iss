; Instalador de Refracción (Inno Setup 6.3 o superior: https://jrsoftware.org/isinfo.php)
;
; Lo normal es compilarlo con:  python packaging/build.py --instalador
; (genera antes el ejecutable y pasa la versión de __init__.py como MyAppVersion).
;
; El AppId NO se cambia nunca entre versiones: así cada versión nueva actualiza
; a la anterior en lugar de instalarse duplicada.

#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#define MyAppName "Refracción"
#define MyAppPublisher "DZM"
#define MyAppExeName "Refraccion.exe"

[Setup]
AppId={{03D0D04B-F809-481B-865A-AA807920BC3D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\DZM\{#MyAppName}
DefaultGroupName=DZM\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Refraccion-{#MyAppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
; Descomenta cuando exista el icono:
; SetupIconFile=..\src\refraccion\resources\icons\app.ico

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\Refraccion\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
