' Inicia el servidor de PhotoBearRate sin mostrar consola.
' Doble clic para ejecutar. El sitio quedará activo aunque cierre el IDE.
Set objShell = WScript.CreateObject("WScript.Shell")
objShell.CurrentDirectory = "c:\Users\MINIOS\CascadeProjects\photo-rating-game"
' 0 = oculto, False = no esperar a que termine
objShell.Run "cmd /c python app.py > server.log 2>&1", 0, False
