import Foundation

class NotificationDelegate: NSObject, NSUserNotificationCenterDelegate {
    func userNotificationCenter(_ center: NSUserNotificationCenter, shouldPresent notification: NSUserNotification) -> Bool {
        return true
    }
}

let delegate = NotificationDelegate()
NSUserNotificationCenter.default.delegate = delegate

let notification = NSUserNotification()
notification.title = "黃金體驗-鎮魂曲"
notification.subtitle = "System Alert"
notification.informativeText = "無駄無駄無駄！看好了，這就是進化的速度！"
notification.soundName = NSUserNotificationDefaultSoundName

NSUserNotificationCenter.default.deliver(notification)
print("Golden Experience Requiem Notification Dispatched.")

// Keep the script alive briefly to allow the notification to be presented
RunLoop.main.run(until: Date(timeIntervalSinceNow: 1.5))
