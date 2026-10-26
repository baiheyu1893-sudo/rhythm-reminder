package com.rhythm.reminder;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.media.AudioAttributes;
import android.net.Uri;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

import androidx.core.app.NotificationCompat;

/**
 * 节律提醒 · 前台服务
 * 作用：进程保活（国产 ROM 不杀后台）+ 常驻状态通知；
 *      同时创建两个带自定义「叮咚」音色与振动的通知渠道，
 *      供 LocalNotifications 按系统闹钟准时触发。
 */
public class ForegroundService extends Service {

    public static final String ACTION_START  = "com.rhythm.reminder.action.START";
    public static final String ACTION_STOP   = "com.rhythm.reminder.action.STOP";
    public static final String ACTION_UPDATE = "com.rhythm.reminder.action.UPDATE";
    public static final String EXTRA_TEXT    = "com.rhythm.reminder.extra.TEXT";

    private static final String CH_SERVICE = "rhythm-service";  // 常驻通知（静默）
    private static final String CH_SMALL   = "rhythm-small";    // 两声提醒
    private static final String CH_BIG     = "rhythm-big";      // 四声提醒

    private static final int NOTIF_ID = 1001;
    private static String statusText = "节律提醒运行中";

    private PowerManager.WakeLock wakeLock;

    @Override
    public void onCreate() {
        super.onCreate();
        createChannels(this);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) {
            startForegroundCompat(statusText);
            return START_STICKY;
        }
        String action = intent.getAction();
        if (ACTION_STOP.equals(action)) {
            stopForeground(true);
            stopSelf();
            return START_NOT_STICKY;
        }
        if (ACTION_UPDATE.equals(action)) {
            String t = intent.getStringExtra(EXTRA_TEXT);
            if (t != null) statusText = t;
            startForegroundCompat(statusText);
            return START_STICKY;
        }
        // ACTION_START
        acquireWakeLock();
        startForegroundCompat(statusText);
        return START_STICKY;
    }

    private void startForegroundCompat(String text) {
        Intent open = new Intent(this, MainActivity.class);
        open.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pi = PendingIntent.getActivity(this, 0, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification n = new NotificationCompat.Builder(this, CH_SERVICE)
                .setSmallIcon(R.drawable.ic_stat_bell)
                .setContentTitle("节律提醒")
                .setContentText(text)
                .setOngoing(true)
                .setSilent(true)
                .setShowWhen(false)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setCategory(NotificationCompat.CATEGORY_SERVICE)
                .setContentIntent(pi)
                .build();

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(NOTIF_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
        } else {
            startForeground(NOTIF_ID, n);
        }
    }

    private void acquireWakeLock() {
        if (wakeLock == null) {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null) {
                wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "rhythm:timer");
                wakeLock.setReferenceCounted(false);
            }
        }
        if (wakeLock != null && !wakeLock.isHeld()) {
            wakeLock.acquire();
        }
    }

    @Override
    public void onDestroy() {
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        wakeLock = null;
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    /* ---------------- 通知渠道 ---------------- */
    public static void createChannels(Context ctx) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;

        AudioAttributes attrs = new AudioAttributes.Builder()
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                .build();

        // 常驻通知渠道：静默、低优先级
        NotificationChannel svc = new NotificationChannel(CH_SERVICE, "运行状态", NotificationManager.IMPORTANCE_LOW);
        svc.setDescription("显示节律提醒的运行状态");
        svc.setShowBadge(false);
        svc.setSound(null, null);
        nm.createNotificationChannel(svc);

        // 两声提醒渠道：自定义叮咚声 + 振动
        NotificationChannel small = new NotificationChannel(CH_SMALL, "节律提醒·两声", NotificationManager.IMPORTANCE_HIGH);
        small.setDescription("小循环到点的两声提醒");
        small.setSound(rawUri(ctx, R.raw.ding_small), attrs);
        small.enableVibration(true);
        small.setVibrationPattern(new long[]{0, 160, 400, 160});
        nm.createNotificationChannel(small);

        // 四声提醒渠道
        NotificationChannel big = new NotificationChannel(CH_BIG, "节律提醒·四声", NotificationManager.IMPORTANCE_HIGH);
        big.setDescription("阶段节点的四声提醒");
        big.setSound(rawUri(ctx, R.raw.ding_big), attrs);
        big.enableVibration(true);
        big.setVibrationPattern(new long[]{0, 160, 400, 160, 400, 160, 400, 160});
        nm.createNotificationChannel(big);
    }

    private static Uri rawUri(Context ctx, int rawId) {
        return Uri.parse("android.resource://" + ctx.getPackageName() + "/" + rawId);
    }
}
