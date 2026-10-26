/* ============================================================
 * 节律提醒 · Windows 桌面版（Electron 主进程）
 *
 * 后台运行保障（对应“后台不运行”问题）：
 *  1. backgroundThrottling:false —— 窗口最小化/隐藏后，
 *     页面里的 setInterval 定时器不会被 Chromium 节流；
 *  2. powerSaveBlocker('prevent-app-suspension') —— 阻止
 *     系统把本进程挂起，计时永不中断；
 *  3. 点“关闭”不是退出，而是隐藏到系统托盘，程序继续
 *     在后台计时（托盘菜单可再次唤出窗口）；
 *  4. 托盘菜单提供「开机自动启动」「阻止系统睡眠」开关，
 *     锁屏/睡眠场景下也能继续提醒（睡眠需开启“阻止系统睡眠”）。
 * ============================================================ */
'use strict';

const { app, BrowserWindow, Tray, Menu, nativeImage, powerSaveBlocker, Notification } = require('electron');
const path = require('path');

const APP_NAME = '节律提醒';
const ICON_PATH = path.join(__dirname, 'assets', 'icon.png');

let win = null;
let tray = null;
let quitting = false;
let trayHintShown = false;
let appSuspensionBlocker = null;  // 阻止进程被挂起（常开）
let displaySleepBlocker = null;   // 阻止系统睡眠（用户开关）

// 单实例
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (!win) return;
    if (win.isMinimized()) win.restore();
    win.show();
    win.focus();
  });
}

app.setAppUserModelId('com.rhythm.reminder');

/* ---------------- 窗口 ---------------- */
function createWindow() {
  win = new BrowserWindow({
    width: 460,
    height: 880,
    minWidth: 380,
    minHeight: 600,
    resizable: true,
    maximizable: true,
    backgroundColor: '#0e1116',
    title: APP_NAME,
    icon: ICON_PATH,
    show: false,
    webPreferences: {
      backgroundThrottling: false,   // ★ 后台不节流定时器
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  Menu.setApplicationMenu(null);     // 去掉默认菜单栏
  win.loadFile('index.html');
  win.once('ready-to-show', () => win.show());

  // 关闭 = 隐藏到托盘，继续后台计时
  win.on('close', (e) => {
    if (quitting) return;
    e.preventDefault();
    win.hide();
    if (!trayHintShown) {
      trayHintShown = true;
      if (Notification.isSupported()) {
        new Notification({
          title: APP_NAME,
          body: '已最小化到系统托盘，提醒继续在后台运行。',
          icon: ICON_PATH,
          silent: true
        }).show();
      }
    }
  });
}

/* ---------------- 托盘 ---------------- */
function trayIcon() {
  return nativeImage.createFromPath(ICON_PATH).resize({ width: 16, height: 16 });
}

function buildTrayMenu() {
  return Menu.buildFromTemplate([
    { label: '显示主窗口', click: () => { win.show(); win.focus(); } },
    { type: 'separator' },
    {
      label: '开机自动启动',
      type: 'checkbox',
      checked: isAutoLaunch(),
      click: (item) => setAutoLaunch(item.checked)
    },
    {
      label: '阻止系统睡眠',
      type: 'checkbox',
      checked: !!displaySleepBlocker,
      click: (item) => toggleDisplaySleep(item.checked)
    },
    { type: 'separator' },
    { label: '退出程序', click: () => { quitting = true; app.quit(); } }
  ]);
}

function refreshTray() {
  if (tray) tray.setContextMenu(buildTrayMenu());
}

function createTray() {
  tray = new Tray(trayIcon());
  tray.setToolTip(APP_NAME + ' · 后台运行中');
  tray.on('click', () => {
    if (!win) return;
    if (win.isVisible() && win.isFocused()) win.hide();
    else { win.show(); win.focus(); }
  });
  refreshTray();
}

/* ---------------- 开关 ---------------- */
function isAutoLaunch() {
  try { return !!app.getLoginItemSettings().openAtLogin; } catch (e) { return false; }
}

function setAutoLaunch(on) {
  try {
    app.setLoginItemSettings({ openAtLogin: !!on, name: APP_NAME });
  } catch (e) {}
  refreshTray();
}

function toggleDisplaySleep(on) {
  if (on && displaySleepBlocker === null) {
    displaySleepBlocker = powerSaveBlocker.start('prevent-display-sleep');
  } else if (!on && displaySleepBlocker !== null) {
    powerSaveBlocker.stop(displaySleepBlocker);
    displaySleepBlocker = null;
  }
  refreshTray();
}

/* ---------------- 生命周期 ---------------- */
app.whenReady().then(() => {
  // 阻止进程被系统挂起（后台计时的核心保障）
  appSuspensionBlocker = powerSaveBlocker.start('prevent-app-suspension');

  createWindow();
  createTray();

  app.on('activate', () => {
    if (win && !win.isVisible()) win.show();
  });
});

// 不因窗口关闭而退出（已改为隐藏到托盘）
app.on('window-all-closed', () => {});
app.on('before-quit', () => { quitting = true; });
