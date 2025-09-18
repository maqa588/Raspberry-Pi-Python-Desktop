# 在树莓派上无需 Root 权限运行无线功能

在树莓派上运行与无线相关的命令时，可能会遇到权限和 X11 的问题。为了避免每次都要求输入密码或必须使用 root 权限，可以通过 **PolicyKit** 进行配置。

### 步骤 1. 创建策略文件

新建文件：

/etc/polkit-1/localauthority/50-local.d/your-user-privileges.pkla

### 步骤 2. 添加以下内容

请将 `maqa` 替换为你的实际用户名：

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

### 步骤 3. 重启服务
保存文件后，可以重启整个系统，或仅重启 polkit 服务：
```bash
sudo systemctl restart polkit.service
```
### 步骤 4. 测试
此时，本地用户就可以直接运行 bluetoothctl 和 nmcli 等命令，而无需使用 sudo。
