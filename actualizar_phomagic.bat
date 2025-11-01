@echo off
echo ========================================
echo 🚀 Actualizando proyecto PHOMAGIC...
echo ========================================

:: Cambiar al directorio del proyecto
cd /d H:\phomagic

:: Forzar inclusión de la carpeta media/lineas (en caso de nuevas vistas)
echo.
echo ➕ Añadiendo cambios al repositorio...
git add products/views.py
git add products/templates/*
git add phomagic/urls.py
git add phomagic/settings.py
git add README.md
git add media/lineas -f
git add .gitignore

:: Crear commit con fecha/hora
set fecha=%date%_%time%
git commit -m "auto: actualización automática %fecha%"

:: Subir cambios a GitHub
echo.
echo ⬆️ Subiendo cambios a GitHub...
git push

echo.
echo ========================================
echo ✅ Cambios subidos correctamente
echo Render iniciará el deploy automáticamente.
echo ========================================
pause
