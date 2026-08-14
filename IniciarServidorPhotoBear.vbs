' Inicia el servidor de PhotoBearRate sin mostrar consola.
' Doble clic para ejecutar. El sitio quedará activo aunque cierre el IDE.
' Usa start_photobear.ps1 (watchdog con mutex de Windows): reinicia solo si se cae,
' y es imposible que se ejecuten dos instancias al mismo tiempo (evita peleas por el puerto 8080).
Set objShell = WScript.CreateObject("WScript.Shell")
objShell.CurrentDirectory = "c:\Users\MINIOS\CascadeProjects\photo-rating-game"
' 0 = oculto, False = no esperar a que termine
objShell.Run "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""c:\Users\MINIOS\CascadeProjects\photo-rating-game\start_photobear.ps1""", 0, False
