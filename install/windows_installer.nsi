;
; This script needs to be processed by the NSIS compiler to produce a
; convenient Windows installer for public distribution.
;
; This script is designed to be invoked from setup.py, which passes
; the following variables to it:
;
; VERSION - the current version of PyKaraoke
;
;--------------------------------

!include "MUI.nsh"

; The name of the installer
Name "PyKaraoke"

; The file to write
OutFile "..\pykaraoke-${VERSION}.exe"

; The default installation directory
InstallDir $PROGRAMFILES\PyKaraoke

; Registry key to check for the directory (so if you install again, it
; will overwrite the old one automatically)
InstallDirRegKey HKLM "Software\PyKaraoke" "Install_Dir"

SetCompress auto

; Comment out this line to use the default compression instead during
; development, which is much faster, but doesn't do quite as good a
; job.
SetCompressor lzma

;--------------------------------

; Pages

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
Var STARTMENU_FOLDER
!insertmacro MUI_PAGE_STARTMENU "PyKaraoke" $STARTMENU_FOLDER
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

;--------------------------------

; The stuff to install
Section "" ;No components page, name is not important

  ; Set output path to the installation directory.
  SetOutPath $INSTDIR
  
  ; Put the entire contents of the dist directory there.
  File /r "..\dist\*"

  RMDir /r "$SMPROGRAMS\$STARTMENU_FOLDER"
  CreateDirectory "$SMPROGRAMS\$STARTMENU_FOLDER"
  CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\PyKaraoke.lnk" "$INSTDIR\pykaraoke.exe"
  CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\PyKaraoke Mini.lnk" "$INSTDIR\pykaraoke_mini.exe"
  WriteINIStr "$SMPROGRAMS\$STARTMENU_FOLDER\PyKaraoke on the Web.url" "InternetShortcut" "URL" "http://www.kibosh.org/pykaraoke/"

SectionEnd ; end the section

Section -post
        DetailPrint "Adding the uninstaller ..."
        Delete "$INSTDIR\uninst.exe"
        WriteUninstaller "$INSTDIR\uninst.exe"
        WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyKaraoke" "DisplayName" "PyKaraoke"
        WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyKaraoke" "UninstallString" '"$INSTDIR\uninst.exe"'
        CreateShortcut "$SMPROGRAMS\$STARTMENU_FOLDER\Uninstall PyKaraoke.lnk" "$INSTDIR\uninst.exe"

SectionEnd

Section Uninstall

        Delete "$INSTDIR\uninst.exe"
        RMDir /r "$SMPROGRAMS\$STARTMENU_FOLDER"
        RMDir /r "$INSTDIR"
        DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyKaraoke"

SectionEnd
