# Running Wireless Functions on Raspberry Pi Without Root

On Raspberry Pi, you may encounter permission and X11 issues when trying to run wireless-related commands. To avoid being prompted for a password or requiring root privileges, you can configure **PolicyKit**.

### Step 1. Create a Policy File

Create the file:

/etc/polkit-1/localauthority/50-local.d/your-user-privileges.pkla

### Step 2. Add the Following Content

Replace `maqa` with your actual username:

```ini
[Allow maqa to control NetworkManager]
Identity=unix-user:maqa
Action=org.freedesktop.NetworkManager.network-control
ResultAny=yes

[Allow maqa to enable/disable Wi-Fi]
Identity=unix-user:maqa
Action=org.freedesktop.NetworkManager.settings.system.wifi-enabled
ResultAny=yes

[Allow maqa to control Bluetooth]
Identity=unix-user:maqa
Action=org.bluez.adapter.SetPowered
ResultAny=yes
```

### Step 3. Restart the Service
After saving the file, restart your Linux device or simply restart the polkit service:
```bash
sudo systemctl restart polkit.service
```
### Step 4. Test
Now, your local user can run commands like bluetoothctl and nmcli directly, without needing sudo.