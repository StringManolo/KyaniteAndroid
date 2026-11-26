🇺🇸 [English](README.md) | 🇪🇸 [Español](README.es.md) | 🇷🇺 [Русский](README.ru.md) | 🇨🇳 简体中文

# KyaniteAndroid

面向高级用户的 Termux 替代方案：[**Kyanite**](https://github.com/StringManolo/Kyanite) 是一个小型、内存安全的 Rust Linux rootfs，内置 `kpkg` 和 Brush，可在 Android 上运行。项目基于 [KotlinApkTemplate](https://github.com/StringManolo/KotlinApkTemplate) 构建，并完全通过 GitHub Actions 编译。它是 [DebianLiveCD4Android](https://github.com/StringManolo/DebianLiveCD4Android) 的一个分支。

🌐 **[官方网站](https://stringmanolo.github.io/KyaniteAndroid/)** · 面向用户的介绍、截图、功能说明和下载指南。

📱 **[下载 Android 版 Kyanite](https://github.com/StringManolo/KyaniteAndroid/releases/latest/download/Kyanite.apk)**

- Kyanite 通过 **proot**（`termux/proot` 的分支）运行，而不是运行在类似 Termux 的 prefix 环境中。
- Kyanite rootfs 是来自 Kyanite Releases 的签名文件 `kyanite-rootfs-aarch64.tar.xz`，并直接打包在 APK 中（约 8 MB）。打包前，CI 会验证其 SHA-256 和 Ed25519 签名（参见 Build）。
- 后续安装的软件来自 Kyanite 内部的 `kpkg` / `apt`；应用本身不依赖 rootfs 中的软件内容。
- 终端模拟器复用 Termux 的 `terminal-emulator` / `terminal-view`，并增加了一栏快捷按键（ESC、TAB、CTRL、ALT、HOME、END、PGUP、PGDN 和方向键；轻触修饰键表示单次启用，长按表示锁定）。
- 特意使用 `targetSdk 28`：更高的 target SDK 不允许从应用数据目录执行二进制文件（W^X）。

## 首次启动、运行环境和模式（⚙ 按钮始终可用）

在你主动选择之前，不会安装或启动任何内容。首次启动时会打开设置界面。

| | **Normal（正常）** | **Ephemeral（临时）** | **VM（虚拟机）** |
|---|---|---|---|
| **System** | 在已安装的 Kyanite 上运行 proot | 在临时副本上运行 proot，退出时删除 | 使用 QEMU，将已安装的系统传输到虚拟机 RAM |
| **LiveCD** | 在持久化解压目录上运行 proot | 每次启动都重新解压，退出时删除 | 使用 QEMU，将内置镜像传输到虚拟机 RAM |

**不同模式之间的存储完全隔离，互不干扰。**

- 每个 **System** 存放在 `files/systems/<id>/` 中。只有在选择该 System 并使用 System + Normal 模式时，才允许修改它。系统必须通过 设置 > Systems 手动创建、导入或下载；不会自动安装任何系统。
- **LiveCD** 的持久化数据（`files/systems/livecd/`）只能通过 LiveCD + Normal 模式修改。
- **Ephemeral** 使用 `files/eph/*`，并在退出时删除这些数据（如果应用被强制结束，则会在下次启动时清理）。
- **VM** 不会向磁盘写入任何数据。System + Ephemeral/VM 只读取已安装的 System；如果系统尚未安装，则拒绝启动（不会自动安装）。
- 唯一明确允许的跨系统访问：在 proot 模式下运行的 LiveCD 会话可以将已安装的 System 挂载到 `/mnt/system`（可读写，需在设置中主动启用），类似于 LiveCD 挂载硬盘以进行修复或备份。VM 模式不支持此功能。

**Ephemeral 使用的是磁盘，而不是 RAM**：闪存存储（F2FS 和磨损均衡机制）可能会保留数据残留。

**VM 是唯一不会在磁盘上留下痕迹的模式**：`qemu-system-aarch64` 使用 TCG 模式（应用无法使用 KVM），启动一个小型 initramfs，通过 virtio-console 端口接收 rootfs，并将其加载到 tmpfs 中。它比 proot 慢得多；可以在设置中选择 RAM 大小和 CPU 核心数。

VM 模式是可选的构建功能（workflow 中的 `with-vm`）。如果当前版本不包含 VM，设置界面会说明缺少哪些组件，并显示诊断信息。

## 窗口与外观

- **全屏模式**或**悬浮窗口模式**（需要「显示在其他应用上层」权限）。悬浮窗口可以自由拖动（允许部分移出屏幕）、调整大小（◢ 角落）、旋转（↻：90°，长按为 15°）、固定（PIN 锁定位置、大小和旋转角度，并记住设置）、调整透明度（◐ 滑块）以及最小化（—）。最小化后窗口会消失，通知栏会提供*恢复*、*设置*和*退出*选项。点击终端可以调出键盘；点击窗口外部可以释放键盘。非 90° 倍数的旋转会产生透明角落，但这些区域仍然会接收触摸事件（Android 的限制）。
- **外观**（即时生效，无需重启）：颜色主题（Dark、Solarized、Dracula、Nord、Gruvbox、Matrix、Light）、字体大小和粗体。双指缩放手势也可以调整字体大小。

## 设置（选项卡）

- **环境**：System / LiveCD、运行模式（VM 为**实验性功能**）、VM RAM 和 CPU 核心数、窗口模式、唤醒锁（默认关闭）、可选的共享存储访问（`/sdcard`、`~/storage/shared`；需要 Android 权限，类似 `termux-setup-storage`，但只在需要时请求）。
- **Systems**：同时管理多个系统；从内置 Kyanite 创建、导入（tar、tar.gz、tar.xz、`.kya`）、下载（Kyanite 最新版本、Alpine、Ubuntu Base 和 Arch Linux ARM 目录；如果上游提供校验和则进行验证，也支持任意 URL 和可选的 SHA-256 校验）、重命名、复制、删除（可选随机数据覆盖）、导出（tar.gz / tar.xz / `.kya`）、创建快照和恢复快照。
- **外观**：28 种颜色主题（包括 Vim 风格主题），完全自定义的调色板、字体大小和粗体。
- **安全**：
  - PIN 码锁定（+ 自动重新锁定时间、+ 胁迫 PIN、+ 错误 PIN 锁定机制）。
  - **静态数据加密**：压缩并使用 AES-256-GCM 加密。未使用的系统以压缩归档形式存储，仅在会话运行期间解压。密钥由应用生成（Android Keystore），或通过密码短语派生。可以随时重新封装密钥、更换密钥（重新加密全部数据）或移除加密。
  - 隐私保护：禁止截图 / 从最近任务列表隐藏、隐藏通知内容、禁用剪贴板、退出时清空剪贴板，以及屏幕关闭时结束会话。
  - **计划擦除**：应用连续 N 小时未打开、到达指定日期、PIN 错误达到 N 次、输入胁迫 PIN，或启用 USB 调试时触发。首先销毁密钥（密码学擦除），然后使用 CSPRNG 随机数据覆盖文件并删除文件，还可以使用随机文件填满剩余磁盘空间（反取证）。条件大约每 30 分钟检查一次。
- **网络**：总开关。关闭时，应用会启用一个没有出口的本地 VPN，从而阻止应用及其内部所有进程的网络流量；VM 不会获得网络接口，应用也不会下载文件或打开浏览器。
- **更新**：关闭 / 手动（打开 Releases 页面）/ 自动（默认每 8 小时检查一次、下载更新并提示安装）。

### VM 注意事项

由于 Kyanite 目前还没有自己的内核，虚拟机使用 QEMU TCG（软件模拟，不使用 KVM）启动 Alpine 的 `linux-virt` arm64 内核。

即使使用 Kyanite 这样的小型 rootfs，在手机上启动到命令提示符通常也需要约 10–40 秒；rootfs 本身的传输只需要几秒钟。

如果控制台停留在 `[kya]` 消息处几分钟，说明出现了问题。救援 Shell 或最后一条消息会指出发生故障的步骤。

在虚拟机 Shell（PID 1）中输入 `exit` 会关闭 VM 并结束会话。

## 稳定性

应用永远不会自行关闭。如果会话结束（你输入了 `exit`、VM 关机或启动失败），应用会保持打开，并显示重新启动 / 设置按钮。会话启动失败或运行时间过短后，不会自动重新启动（避免崩溃循环）。

在服务停止之前，系统会重新打包（压缩 / 加密），并且在删除未打包的文件树之前先将其标记为无效。因此，即使退出过程被中断，也不会留下一个部分删除但仍被视为有效的系统。如果残留了未打包的文件树，下次启动时会重新打包。

## 需要了解的限制

- proot 不是安全隔离边界（需要隔离时请使用 VM 模式）。
- 闪存存储上的数据覆盖只能尽力而为；密码学密钥销毁才是可靠的保证。
- Android 不允许静默安装应用：任何更新都必须经过你的确认，并且必须使用相同的签名密钥。

## Build（构建）

将代码推送到 GitHub。`.github/actions/prepare-assets` 会执行以下步骤：

1. 从 Termux apt 仓库下载 proot（以及 QEMU），并验证 SHA-256。
2. 使用 Alpine 的 `linux-virt` 和 `busybox-static` 构建 VM 内核和 initramfs（`bash/build_vm_assets.py`）。设置 `VM_KERNEL=debian` 可以切换到 Debian 内核；`ALPINE_BRANCH` 可以固定 Alpine 分支。
3. 获取 Kyanite rootfs（`bash/fetch-rootfs.sh`）：下载 Release、验证 SHA-256、使用固定在 `bash/kyanite-release.pub` 中的公钥验证 Ed25519 签名，然后使用 `xz -6` 重新压缩，以便应用使用较小的 heap 完成解压。可以通过 action 的 `kyanite-tag` 输入参数（或 `KYANITE_TAG`）指定版本，例如 `v0.1.1`；默认使用最新版本。Release 如果没有有效签名，构建将失败（设置 `KYANITE_ALLOW_UNSIGNED=1` 可以跳过此检查）。

随后 Gradle 会构建 APK。校验和与 URL 会作为 `provenance` 构建产物上传。

Android 12 及更高版本可能会终止子进程（「phantom process killer」）；如果会话在后台被意外终止，请禁用此功能。
