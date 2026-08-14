' Inicia el servidor de PhotoBearRate sin mostrar consola.
' Doble clic para ejecutar. El sitio quedará activo aunque cierre el IDE.
' Usa start_photobear.bat que reinicia automáticamente si el servidor se cae (indestructible).
Set objShell = WScript.CreateObject("WScript.Shell")
objShell.CurrentDirectory = "c:\Users\MINIOS\CascadeProjects\photo-rating-game"
' 0 = oculto, False = no esperar a que termine
objShell.Run "cmd /c ""c:\Users\MINIOS\CascadeProjects\photo-rating-game\start_photobear.bat""", 0, False
