#pragma once

#include "Export.h"

#include <QObject>
#include <QString>

/**
 * @brief Self-contained WebSocket injection server for Qt widget automation.
 *
 * Originally inspired by qt-widgeteer
 * (https://github.com/AurynRobotics/qt-widgeteer), but reimplemented here as a
 * single-file, zero-dependency server that handles the four commands needed by
 * the BrainVoyager MCP bridge:
 *
 *   list_windows  — enumerate top-level windows
 *   get_tree      — walk the widget tree to a given depth
 *   click         — click a widget by @text / @name / @class selector
 *   invoke        — invoke a Qt slot or Q_INVOKABLE method on a widget
 *
 * Usage from an injection hook:
 * @code
 *   auto* server = new BVInjectServer(qApp);
 *   server->startServer(9000);  // ws://localhost:9000
 * @endcode
 */
class MYLIB_EXPORT BVInjectServer : public QObject {
  Q_OBJECT

public:
  explicit BVInjectServer(QObject *parent = nullptr);
  ~BVInjectServer() override;

  /// Start the WebSocket control server on @p port.
  bool startServer(quint16 port = 9000);

  /// Stop the server.
  void stopServer();

  /// Check if the server is currently running.
  bool isRunning() const;

  /// Version string.
  QString version() const;

private:
  class Private;
  Private *d; // PIMPL — hides Qt WebSocket headers from consumers
};
