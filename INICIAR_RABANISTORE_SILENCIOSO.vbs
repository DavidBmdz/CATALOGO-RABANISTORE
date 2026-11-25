Option Explicit

Dim shell, fso, folder, url, request, started, i, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

folder = fso.GetParentFolderName(WScript.ScriptFullName)
url = "http://127.0.0.1:8000/"

' Ejecuta Python sin mostrar una ventana de consola.
shell.CurrentDirectory = folder

' Si el servidor ya está activo, no intenta iniciar una segunda copia.
If ServerResponds(url) Then
    shell.Run url, 1, False
    WScript.Quit 0
End If

' pyw utiliza el mismo lanzador de Python, pero sin ventana de consola.
shell.Run "pyw -m backend.server", 0, False

' Espera hasta 30 segundos a que el servidor responda.
started = False
For i = 1 To 30
    WScript.Sleep 1000
    If ServerResponds(url) Then
        started = True
        Exit For
    End If
Next

If started Then
    shell.Run url, 1, False
Else
    MsgBox "No se pudo iniciar Rabanistore." & vbCrLf & vbCrLf & _
           "Comprueba que Python esté instalado " & _
           "y que el puerto 8000 esté libre." & vbCrLf & vbCrLf & _
           "Para instalar dependencias, abre una terminal en esta carpeta " & _
           "y ejecuta: py -m pip install -r requirements.txt", _
           vbExclamation, "Rabanistore"
End If

Function ServerResponds(address)
    On Error Resume Next
    Dim http
    Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
    http.SetTimeouts 500, 500, 500, 1000
    http.Open "GET", address, False
    http.Send
    ServerResponds = (Err.Number = 0 And http.Status = 200)
    Err.Clear
    Set http = Nothing
    On Error GoTo 0
End Function
