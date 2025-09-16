pyinstaller --noconfirm \
--name "Raspberry Pi Desktop" \
--windowed \
--onefile \
--add-data "icons:icons" \
--add-data "software:software" \
--add-data "system:system" \
--version-file "system:version.txt" \
app.py