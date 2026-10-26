package com.rhythm.reminder;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.PowerManager;
import android.provider.Settings;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * 节律提醒 · 本地 Capacitor 插件
 * 提供：前台服务启停、常驻通知文案更新、电池优化豁免、精确闹钟引导。
 */
@CapacitorPlugin(name = "RhythmNative")
public class RhythmNativePlugin extends Plugin {

    @PluginMethod
    public void ensureChannels(PluginCall call) {
        ForegroundService.createChannels(getContext());
        call.resolve();
    }

    @PluginMethod
    public void startForeground(PluginCall call) {
        Intent i = new Intent(getContext(), ForegroundService.class);
        i.setAction(ForegroundService.ACTION_START);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getContext().startForegroundService(i);
        } else {
            getContext().startService(i);
        }
        call.resolve();
    }

    @PluginMethod
    public void stopForeground(PluginCall call) {
        Intent i = new Intent(getContext(), ForegroundService.class);
        i.setAction(ForegroundService.ACTION_STOP);
        getContext().startService(i);
        call.resolve();
    }

    @PluginMethod
    public void updateStatus(PluginCall call) {
        String text = call.getString("text");
        if (text == null) text = "节律提醒运行中";
        Intent i = new Intent(getContext(), ForegroundService.class);
        i.setAction(ForegroundService.ACTION_UPDATE);
        i.putExtra(ForegroundService.EXTRA_TEXT, text);
        getContext().startService(i);
        call.resolve();
    }

    @PluginMethod
    public void isIgnoringBatteryOptimizations(PluginCall call) {
        PowerManager pm = (PowerManager) getContext().getSystemService(Context.POWER_SERVICE);
        boolean ignoring = pm != null && pm.isIgnoringBatteryOptimizations(getContext().getPackageName());
        JSObject ret = new JSObject();
        ret.put("granted", ignoring);
        call.resolve(ret);
    }

    @PluginMethod
    public void requestIgnoreBatteryOptimizations(PluginCall call) {
        PowerManager pm = (PowerManager) getContext().getSystemService(Context.POWER_SERVICE);
        if (pm != null && !pm.isIgnoringBatteryOptimizations(getContext().getPackageName())) {
            try {
                Intent i = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
                i.setData(Uri.parse("package:" + getContext().getPackageName()));
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                getContext().startActivity(i);
            } catch (Exception ignored) {
                // 部分 ROM 没有该设置页
            }
        }
        JSObject ret = new JSObject();
        ret.put("granted", pm != null && pm.isIgnoringBatteryOptimizations(getContext().getPackageName()));
        call.resolve(ret);
    }

    @PluginMethod
    public void openExactAlarmSettings(PluginCall call) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            try {
                Intent i = new Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM);
                i.setData(Uri.parse("package:" + getContext().getPackageName()));
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                getContext().startActivity(i);
            } catch (Exception ignored) {}
        }
        call.resolve();
    }
}
