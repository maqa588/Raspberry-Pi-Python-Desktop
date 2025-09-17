# Problem running on Raspberry Pi

Due to the system permission and X11 issues, you need to modify some commands related to wireless functions so that they could be running neither asking password nor try to run in root privilege.

Please create `/etc/polkit-1/localauthority/50-local.d/your-user-privileges.pkla`
And add these contents(my user name is maqa, you need to modify depend on yours):

```
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

after saving files, you need to restart your Linux device or restart polkit service:

`sudo systemctl restart polkit.service`

when executed, your local user could directly use bluetoothctl and nmcli without root privileges.