#import <Cocoa/Cocoa.h>
#import <objc/runtime.h>

#include <QApplication>
#include <QTimer>

#include "mylib.h"

// ── Swizzled -[NSApplication run] ─────────────────────────────────────
// Called from within QApplication::exec().  At this point qApp exists
// and the event loop is about to start — perfect time to boot our server.

static void (*original_run)(id, SEL);

static void swizzled_NSApplication_run(id self, SEL _cmd) {
  static dispatch_once_t once;
  dispatch_once(&once, ^{
    auto *app = qobject_cast<QApplication *>(QCoreApplication::instance());
    if (app) {
      // Create and start the bv_ui_control WebSocket server.
      // Parented to qApp so it lives as long as the application.
      auto *server = new BVInjectServer(app);
      server->startServer(9000);
      server->setObjectName(QStringLiteral("_bv_ui_control_injected"));

      qDebug() << "[bv_ui_control] Injected — WebSocket server on port 9000";
      qDebug() << "[bv_ui_control] Connect via:  ws://localhost:9000";
    } else {
      qWarning() << "[bv_ui_control] No QApplication found, injection skipped";
    }
  });

  // Forward to the real -[NSApplication run] (enters the event loop).
  original_run(self, _cmd);
}

// ── Constructor — runs automatically on DYLD_INSERT_LIBRARIES ─────────

__attribute__((constructor)) static void widgeteer_inject() {
  @autoreleasepool {
    Class nsapp = objc_getClass("NSApplication");
    if (!nsapp) {
      // Not a GUI app — nothing to do.
      return;
    }

    Method runMethod = class_getInstanceMethod(nsapp, @selector(run));
    if (runMethod) {
      original_run = (void (*)(id, SEL))method_getImplementation(runMethod);
      method_setImplementation(runMethod, (IMP)swizzled_NSApplication_run);

      NSLog(
          @"[bv_ui_control] Hook installed — waiting for QApplication::exec()");
    }
  }
}
