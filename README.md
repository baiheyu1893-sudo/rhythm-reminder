# 节律提醒 · 双平台封装（Windows 桌面 exe / Android 手机 apk）

把一份「节律提醒」网页应用（纯 HTML/CSS/JS）同时封装成 **Windows 桌面程序（.exe）** 与 **Android 手机应用（.apk）**，
并针对性解决了「网页壳在后台 / 锁屏后定时不响」这一核心痛点。

- 工程根目录：`rhythm-reminder/`
- 网页源码（两平台共用）：`src/index.html`
- 构建产物：Windows 在 `windows/dist/`，Android 在 `android/android/app/build/outputs/apk/debug/`
- 灵感来源：一次 DeepSeek 对话（chat.deepseek.com/share/lks9avmrhqsnpw4o24）

---

## 目录

1. [项目简介](#项目简介)
2. [功能特性](#功能特性)
3. [技术栈](#技术栈)
4. [目录结构](#目录结构)
5. [一、Windows 版（.exe）](#一windows-版exe)
6. [二、Android 版（.apk）](#二android-版apk)
7. [三、后台运行核心原理（重点）](#三后台运行核心原理重点)
8. [四、源码关键设计](#四源码关键设计)
9. [五、重新构建](#五重新构建)
10. [六、已知限制](#六已知限制)
11. [许可证与致谢](#许可证与致谢)

---

## 项目简介

「节律提醒」是一个帮助用户维持工作 / 休息节律的轻量计时器。它不依赖任何后端，全部逻辑在浏览器（WebView）内运行。

其核心节奏是**双循环状态机**：

- **小循环**：每隔 3~5 分钟随机播放「叮叮」两声 → 紧接着 10 秒间歇倒计时 → 倒计时结束再「叮叮」两声 → 进入下一轮。
- **大循环**：累计约 90 分钟后播放「叮叮叮叮」四声（阶段节点）→ 休息 20 分钟 → 再次四声 → 开始新一轮大循环。

原始版本只是一个网页，在手机/桌面浏览器打开即可用，但存在两个现实问题：

1. 每次都要开浏览器、不方便常驻；
2. **锁屏或切后台后，浏览器定时器被系统节流甚至冻结，提示音与振动不再准时**——这正是本工程要解决的核心问题。

本工程用 Electron 与 Capacitor 把这份网页分别打包成可安装的程序，并在两个平台以**各自原生的方式保证「后台也能准时提醒」**。

---

## 功能特性

**网页本体（两平台共用）**

- 双循环节律计时：小循环随机两声「叮叮」+ 间歇；大循环四声「叮叮叮叮」+ 休息。
- 提示音由 **Web Audio API** 实时合成（两个振荡器叠加出柔和「叮」声），无需音频文件。
- 振动反馈（`navigator.vibrate`），与提示音同步。
- **屏幕常亮**（Screen WakeLock），运行时保持亮屏。
- 深色主题、移动端竖屏适配，桌面/手机同一套界面。
- 可调参数：休息时长、相邻「叮」间隔、小循环时长等。

**Windows 版额外能力**

- 关闭窗口 ≠ 退出，而是**最小化到系统托盘**继续计时。
- 托盘菜单：显示/隐藏窗口、开机自启、阻止系统睡眠。
- 进程级防挂起（powerSaveBlocker），不被系统节能策略暂停。

**Android 版额外能力**

- **前台服务常驻**：通知栏常驻运行状态，进程优先级最高，难被系统/国产 ROM 杀掉。
- **系统级定时提醒**：每一次「叮叮 / 叮叮叮叮」都注册到系统 **AlarmManager（精确闹钟）**，即使 App 被回收，到点也由系统直接发通知，音色与振动和 App 内一致。
- 首次启动引导开启通知权限、忽略电池优化。

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| 网页 | 原生 HTML/CSS/JS、Web Audio API、Vibration API、Screen WakeLock API |
| Windows | Electron 33 + electron-builder 25（NSIS 安装版 + 便携版） |
| Android | Capacitor 8 + 本地 Capacitor 插件 + `ForegroundService` + `@capacitor/local-notifications`（AlarmManager 精确闹钟） |
| 构建工具链 | Node.js、Gradle 8.14、Android SDK（platform-36 / build-tools 36）、JDK 21 |

---

## 目录结构

```
rhythm-reminder/
├── README.md                 # 本说明
├── src/
│   └── index.html            # 网页源码（含后台运行适配，两平台共用）
├── assets/                   # 图标与提示音源文件（重新生成用）
│   ├── icon.png / icon.ico   # 应用图标
│   ├── ic_launcher_*.png     # Android 各密度启动图标
│   ├── ic_stat_bell.png      # 通知白色小图标
│   └── ding_small.wav / ding_big.wav   # 两声/四声提示音（Android 渠道用）
├── tools/                    # 资源生成与原生补丁脚本（可重新运行）
│   ├── gen_assets.py         # 用 Pillow 生成图标、wave 合成提示音
│   ├── patch_android.py      # 一次性打 Android 原生补丁
│   ├── RhythmNativePlugin.java
│   └── ForegroundService.java
├── windows/                  # Electron 工程（Windows .exe）
│   ├── main.js               # 托盘常驻 / 防挂起 / 防节流 / 开机自启
│   ├── index.html            # 与 src/index.html 内容一致
│   ├── package.json
│   └── dist/                 # ★ 构建产物
│       ├── 节律提醒 Setup 1.0.0.exe        # 安装版（NSIS）
│       └── 节律提醒-1.0.0-便携版.exe        # 免安装便携版
└── android/                  # Capacitor 工程（Android .apk）
    ├── www/index.html        # 与 src/index.html 内容一致
    ├── capacitor.config.json
    ├── package.json
    └── android/              # 原生 Android 工程（已打后台保活补丁）
        └── app/build/outputs/apk/debug/app-debug.apk   # ★ 构建产物
```

---

## 一、Windows 版（.exe）

### 直接使用

`windows/dist/` 下有两个产物（已实际构建完成）：

| 文件 | 大小 | 说明 |
| --- | --- | --- |
| `节律提醒 Setup 1.0.0.exe` | 约 82 MB | 安装版（NSIS，可选安装目录、创建快捷方式） |
| `节律提醒-1.0.0-便携版.exe` | 约 82 MB | 免安装便携版，**双击即用**，可整个复制到别的电脑 |

> 首次运行若出现 SmartScreen 提示，点「更多信息 → 仍要运行」即可（未购买代码签名证书）。

### 后台运行是怎么解决的（Windows）

| 问题 | 方案（见 `windows/main.js`） |
| --- | --- |
| 窗口最小化后定时器被浏览器节流 | `backgroundThrottling: false` |
| 系统把后台进程挂起 | `powerSaveBlocker.start('prevent-app-suspension')` 常驻 |
| 点关闭就退出、计时中断 | 关闭 = 隐藏到**系统托盘**，继续计时；托盘左键点一下唤回窗口 |
| 想开机自动运行 | 托盘菜单勾选「开机自动启动」 |
| 锁屏/睡眠后停走 | 托盘菜单按需勾选「阻止系统睡眠」 |

---

## 二、Android 版（.apk）

### 直接使用

产物（已实际构建完成，约 4.3 MB）：

```
android/android/app/build/outputs/apk/debug/app-debug.apk
```

传到手机（微信/QQ/数据线均可）→ 点击安装 → 允许「未知来源」。
首次启动会依次申请：**通知权限**、**忽略电池优化**（弹系统对话框，建议允许）。

### 后台运行是怎么解决的（Android）

纯网页壳在锁屏 / 切后台后会被系统冻结，本工程加了一层原生保障：

| 问题 | 方案 |
| --- | --- |
| 进程被系统 / 国产 ROM 杀掉 | `ForegroundService` 前台服务常驻（通知栏显示运行状态，进程优先级最高） |
| 锁屏后定时器冻结、提醒不响 | 每一次提醒都通过 `@capacitor/local-notifications` 注册到系统 **AlarmManager**（精确闹钟），到点由系统直接发通知——**与 App 是否活着无关** |
| 提醒音色与 App 不一致 | 通知渠道预置与 App 内相同的「叮叮 / 叮叮叮叮」合成音（`res/raw/ding_small.wav`、`ding_big.wav`）+ 相同节奏的振动 |
| Doze 休眠延迟 | 申请忽略电池优化 + `allowWhileIdle` + `USE_EXACT_ALARM` |
| WebView 被节流导致状态错乱 | 状态机用绝对时间戳，恢复前台后自动追平（错过的提醒会补响一次） |

一句话总结：**App 开着 → 前台服务保活，App 内正常响；App 被切后台 / 锁屏甚至被回收 → 系统级通知照样准时响。**

---

## 三、后台运行核心原理（重点）

| 维度 | Windows（Electron） | Android（Capacitor + 原生） |
| --- | --- | --- |
| 保活手段 | 托盘隐藏 + powerSaveBlocker + backgroundThrottling:false | 前台服务（最高优先级）+ 系统 AlarmManager |
| 计时精度保障 | 进程不挂起即准时；勾选「阻止睡眠」可连睡眠也保持 | 即便进程被回收，AlarmManager 仍准时触发系统通知 |
| 音色 | Web Audio 实时合成 | 通知渠道预置相同 wav + 相同振动节奏 |
| 系统限制 | 系统进入睡眠后任何程序都暂停（故提供「阻止睡眠」开关） | 国产 ROM 激进杀后台（故用前台服务 + 忽略电池优化） |
| 适用场景 | 电脑前工作、桌面常驻 | 手机锁屏 / 切后台 / 长时间运行 |

核心思路一致：**能活着就自己响，活不了就让系统替你响**——两层兜底，确保节律提醒「不漏拍」。

---

## 四、源码关键设计

- **状态机（`src/index.html`）**：以 `setInterval(tick, 200)` 驱动，所有时间点用**绝对时间戳**计算，恢复前台后自动追平，避免被节流后状态错乱。
- **提示音合成**：`AudioContext` + 两个 `OscillatorNode` 叠加，单次「叮」为短促柔和音；两声 = 常规提示，四声 = 阶段节点。无外部音频依赖。
- **振动**：`navigator.vibrate(pattern)` 与提示音同步（桌面无振动马达时静默跳过）。
- **屏幕常亮**：`navigator.wakeLock.request('screen')`，页面隐藏时释放、可见时重新申请。
- **原生桥接（Android）**：`RhythmNativePlugin` 暴露「启动 / 停止前台服务、请求电池优化豁免、申请精确闹钟」等接口；`index.html` 据此把下一次提醒的绝对时间注册进系统闹钟。

---

## 五、重新构建

### 前置环境

- **Node.js**（建议 18+）
- **Windows 版**：仅需 Node.js
- **Android 版**：JDK 21（或 17）、Android SDK（`platforms;android-36` + `build-tools;36.0.0`）

> 本机构建环境：JDK 用 `E:\Java\java21`；Android SDK 搭建在 `D:\AndroidSdk`，`android/android/local.properties` 已指向它。Gradle 发行包已配置为腾讯云镜像（`gradle/wrapper/gradle-wrapper.properties`），国内下载更快。

### Windows

```bash
cd windows
npm install                                   # 依赖（Electron 走国内镜像）
npm run build                                 # 产物在 windows/dist/
```

### Android

```bash
cd android
npm install
cp ../src/index.html www/index.html           # 同步网页源码
npx cap sync android                          # 同步到原生工程

# 指向本机 SDK（二选一）
echo 'sdk.dir=D\:\\AndroidSdk' > android/local.properties
# 或设置环境变量 ANDROID_HOME

cd android
gradlew.bat assembleDebug                     # 产物见上方路径
# 正式发布：gradlew.bat assembleRelease（需配置 signingConfigs 签名）
```

> 修改 `src/index.html` 后，记得同步到 `windows/index.html` 与 `android/www/index.html`（或重新 `cp` + `cap sync`）。

---

## 六、已知限制

- **iOS 未打包**：iOS 对后台定时限制更严，需要单独的 Swift 改造，本次未包含。
- **Windows「阻止系统睡眠」默认关闭**：计时不受影响，但系统休眠时任何程序都会暂停；需要锁屏长时间运行请在托盘菜单勾选。
- **振动依赖硬件**：Windows 桌面无振动马达（设置里的「振动」开关无效但不报错）；Android 需 `VIBRATE` 权限（已内置）。
- **系统休眠后的提醒**：Windows 下勾选「阻止系统睡眠」即可；Android 由 AlarmManager 保证。
- **debug 包可直接安装**；上架应用商店需签名，并把 `USE_EXACT_ALARM` 的使用说明提交审核（本 App 属提醒类，符合该权限申报范围）。
- 仓库包含完整**源码与构建脚本**；`exe` / `apk` 为编译产物（体积较大：两个 exe 各约 82 MB、apk 约 4.3 MB），**未纳入版本库**，按「五、重新构建」即可在本机一键生成。本机已实测构建出可运行的安装版 / 便携版 exe 与 debug apk，如需要可单独分发这两个文件。

---

## 许可证与致谢

- 本项目为个人学习 / 自用封装示例，未内置第三方专有资源。
- 提示音与图标均由脚本（见 `tools/`）程序化生成，可自由替换。
- 封装思路参考自 DeepSeek 分享对话；Electron / Capacitor 为各自开源协议下的框架。
