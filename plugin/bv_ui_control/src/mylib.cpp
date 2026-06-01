#include "mylib.h"

#include <QAbstractButton>
#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMetaMethod>
#include <QPointer>
#include <QRadioButton>
#include <QSet>
#include <QTest>
#include <QTimer>
#include <QWebSocket>
#include <QWebSocketServer>
#include <QWidget>

#include <memory>

// ═══════════════════════════════════════════════════════════════════════════
//  Inline element finder — resolves @text / @name / @class selectors against
//  the live widget tree.  No external dependencies.
// ═══════════════════════════════════════════════════════════════════════════

static QWidget* findByObjectName(const QString& name) {
    const auto tops = QApplication::topLevelWidgets();
    for (auto* w : tops) {
        if (w->objectName() == name) return w;
        if (auto* f = w->findChild<QWidget*>(name)) return f;
    }
    return nullptr;
}

static QWidget* findByClassName(const QString& className) {
    const auto tops = QApplication::topLevelWidgets();
    for (auto* w : tops) {
        if (QString::fromLatin1(w->metaObject()->className()) == className) return w;
        const auto kids = w->findChildren<QWidget*>();
        for (auto* k : kids) {
            if (QString::fromLatin1(k->metaObject()->className()) == className) return k;
        }
    }
    return nullptr;
}

static QWidget* findByVisibleText(const QString& text) {
    // Partial / case-insensitive match against visible text
    const QString lower = text.toLower();
    const auto tops = QApplication::topLevelWidgets();
    for (auto* w : tops) {
        const auto all = w->findChildren<QWidget*>();
        QList<QWidget*> search = all;
        search.prepend(w);
        for (auto* sw : search) {
            // Try accessible name first
            if (!sw->accessibleName().isEmpty() &&
                sw->accessibleName().toLower().contains(lower)) {
                return sw;
            }
            // Try window title / button text / label text
            QString candidate;
            if (sw->isWindow()) candidate = sw->windowTitle();
            if (candidate.isEmpty()) candidate = sw->property("text").toString();
            if (candidate.isEmpty()) candidate = sw->property("title").toString();
            if (candidate.isEmpty()) candidate = sw->property("plainText").toString();
            if (!candidate.isEmpty() && candidate.toLower().contains(lower)) {
                return sw;
            }
        }
    }
    return nullptr;
}

static QWidget* resolveSelector(const QString& target) {
    if (target.startsWith(QLatin1String("@name:")))
        return findByObjectName(target.mid(6));
    if (target.startsWith(QLatin1String("@class:")))
        return findByClassName(target.mid(7));
    if (target.startsWith(QLatin1String("@text:")))
        return findByVisibleText(target.mid(6));
    return nullptr;
}

// ═══════════════════════════════════════════════════════════════════════════
//  Inline widget-tree walker — produces the same JSON shape the Python
//  clients (bv.py / bv_ws.py) expect.
// ═══════════════════════════════════════════════════════════════════════════

// Set of QMetaMethod names to skip (internal Qt noise).
static bool _isActionableSlot(const QMetaMethod& m) {
    if (m.access() != QMetaMethod::Public) return false;
    if (m.methodType() != QMetaMethod::Slot) return false;
    // Only no-arg methods — safe to invoke without guessing parameter types.
    if (m.parameterCount() != 0) return false;
    const QByteArray name = m.name();
    // Skip Qt-internal and identity methods.
    static const QSet<QByteArray> skip = {
        "deleteLater", "_q_reregisterTimers",
        "blockSignals", "connectNotify", "customEvent",
        "disconnectNotify", "dumpObjectInfo", "dumpObjectTree",
        "dynamicPropertyNames", "event", "eventFilter",
        "findChild", "findChildren", "inherits",
        "installEventFilter", "killTimer",
        "moveToThread", "removeEventFilter",
        "sender", "startTimer", "stop", "timerEvent",
        "update", "repaint", "updateGeometry", "updateMicroFocus",
        "setFocus", "clearFocus"
    };
    return !skip.contains(name);
}

// Curated per-widget-type actions plus auto-discovered no-arg public slots.
static QJsonArray collectActions(QWidget* widget) {
    QJsonArray actions;
    QSet<QString> seen;
    auto add = [&](const QString& a) {
        if (!seen.contains(a)) { seen.insert(a); actions.append(a); }
    };

    const char* cn = widget->metaObject()->className();

    // -- Curated actions by widget type --
    if (qobject_cast<QAbstractSpinBox*>(widget)) {
        add("stepUp"); add("stepDown");
    } else if (qobject_cast<QAbstractButton*>(widget)) {
        add("click"); add("toggle");
        if (qobject_cast<QCheckBox*>(widget) || qobject_cast<QRadioButton*>(widget))
            add("click");  // already added, just for clarity
    } else if (qstrcmp(cn, "QLineEdit") == 0 || qstrcmp(cn, "QTextEdit") == 0 ||
               qstrcmp(cn, "QPlainTextEdit") == 0) {
        add("clear"); add("selectAll"); add("undo"); add("redo"); add("cut"); add("copy"); add("paste");
    } else if (qobject_cast<QComboBox*>(widget)) {
        add("showPopup"); add("hidePopup");
    } else if (qobject_cast<QAbstractSlider*>(widget)) {
        // Sliders need a value arg — still useful to know
        add("setValue");
    } else if (qstrcmp(cn, "QTabWidget") == 0) {
        add("setCurrentIndex");
    }

    // -- Auto-discover no-arg public slots (catches custom BV widgets) --
    const QMetaObject* mo = widget->metaObject();
    for (int i = mo->methodOffset(); i < mo->methodCount(); ++i) {
        QMetaMethod m = mo->method(i);
        if (_isActionableSlot(m)) {
            add(QString::fromLatin1(m.name()));
        }
    }

    return actions;
}

static QJsonObject widgetToJson(QWidget* widget, int depth, int maxDepth) {
    if (!widget || !widget->isVisible()) return {};
    if (maxDepth >= 0 && depth > maxDepth) return {};

    QJsonObject json;
    json["objectName"] = widget->objectName();
    json["class"] = QString::fromLatin1(widget->metaObject()->className());
    json["visible"] = widget->isVisible();
    json["enabled"] = widget->isEnabled();

    // ---- type hint ----
    {
        const char* cn = widget->metaObject()->className();
        if (qobject_cast<QAbstractButton*>(widget))
            json["type"] = "button";
        else if (qstrcmp(cn, "QLabel") == 0)
            json["type"] = "label";
        else if (qstrcmp(cn, "QLineEdit") == 0)
            json["type"] = "textfield";
        else if (qstrcmp(cn, "QTextEdit") == 0 || qstrcmp(cn, "QPlainTextEdit") == 0)
            json["type"] = "textarea";
        else if (qstrcmp(cn, "QComboBox") == 0)
            json["type"] = "combobox";
        else if (qstrcmp(cn, "QSpinBox") == 0 || qstrcmp(cn, "QDoubleSpinBox") == 0)
            json["type"] = "spinbox";
        else if (qstrcmp(cn, "QSlider") == 0 || qstrcmp(cn, "QScrollBar") == 0)
            json["type"] = "slider";
        else if (qstrcmp(cn, "QProgressBar") == 0)
            json["type"] = "progressbar";
        else if (qstrcmp(cn, "QGroupBox") == 0)
            json["type"] = "group";
        else if (qstrcmp(cn, "QTabWidget") == 0)
            json["type"] = "tabwidget";
        else if (qstrcmp(cn, "QListWidget") == 0)
            json["type"] = "list";
        else if (qstrcmp(cn, "QTreeWidget") == 0)
            json["type"] = "tree";
        else if (qstrcmp(cn, "QTableWidget") == 0)
            json["type"] = "table";
        else if (qstrcmp(cn, "QMenuBar") == 0)
            json["type"] = "menubar";
        else if (qstrcmp(cn, "QMenu") == 0)
            json["type"] = "menu";
        else if (qstrcmp(cn, "QToolBar") == 0)
            json["type"] = "toolbar";
        else if (qstrcmp(cn, "QStatusBar") == 0)
            json["type"] = "statusbar";
        else if (widget->isWindow())
            json["type"] = "window";
        else
            json["type"] = "widget";
    }

    // ---- visible text (the most useful piece for an LLM) ----
    {
        QString text;
        if (auto* btn = qobject_cast<QAbstractButton*>(widget))
            text = btn->text();
        else
            text = widget->property("text").toString();
        if (text.isEmpty()) text = widget->property("title").toString();
        if (text.isEmpty()) text = widget->property("plainText").toString();
        if (text.isEmpty()) text = widget->property("placeholderText").toString();
        if (!text.isEmpty()) json["text"] = text;
    }

    // ---- available actions (what can the AI agent do with this widget) ----
    {
        QJsonArray actions = collectActions(widget);
        if (!actions.isEmpty()) json["actions"] = actions;
    }

    // ---- children ----
    const auto kids = widget->findChildren<QWidget*>(QString(), Qt::FindDirectChildrenOnly);
    if (!kids.isEmpty()) {
        QJsonArray children;
        for (auto* child : kids) {
            QJsonObject cj = widgetToJson(child, depth + 1, maxDepth);
            if (!cj.isEmpty()) children.append(cj);
        }
        if (!children.isEmpty()) json["children"] = children;
    }

    return json;
}

// ═══════════════════════════════════════════════════════════════════════════
//  Private implementation
// ═══════════════════════════════════════════════════════════════════════════

class BVInjectServer::Private {
public:
    std::unique_ptr<QWebSocketServer> server;
    QList<QWebSocket*> clients;
    quint16 port = 0;
};

// ═══════════════════════════════════════════════════════════════════════════
//  Public API
// ═══════════════════════════════════════════════════════════════════════════

BVInjectServer::BVInjectServer(QObject* parent)
    : QObject(parent)
    , d(new Private) {}

BVInjectServer::~BVInjectServer() {
    stopServer();
    delete d;
}

bool BVInjectServer::startServer(quint16 port) {
    if (d->server && d->server->isListening()) return false;

    d->port = port;
    d->server = std::make_unique<QWebSocketServer>(
        QStringLiteral("bv-ui-control"), QWebSocketServer::NonSecureMode, this);

    if (!d->server->listen(QHostAddress::LocalHost, port)) {
        d->server.reset();
        return false;
    }

    connect(d->server.get(), &QWebSocketServer::newConnection, this, [this]() {
        while (auto* socket = d->server->nextPendingConnection()) {
            d->clients.append(socket);

            connect(socket, &QWebSocket::textMessageReceived, this,
                    [this, socket](const QString& message) {
                // Parse incoming JSON command
                QJsonParseError err;
                QJsonDocument doc = QJsonDocument::fromJson(message.toUtf8(), &err);
                if (err.error != QJsonParseError::NoError) {
                    QJsonObject resp;
                    resp["id"] = QString();
                    resp["error"] = QStringLiteral("Parse error: ") + err.errorString();
                    socket->sendTextMessage(QJsonDocument(resp).toJson(QJsonDocument::Compact));
                    return;
                }

                QJsonObject msg = doc.object();
                QString cmdId = msg.value("id").toString();
                QString command = msg.value("command").toString();
                QJsonObject params = msg.value("params").toObject();

                QJsonObject result;
                bool success = true;

                // ── list_windows ──────────────────────────────────────────
                if (command == "list_windows") {
                    QJsonArray windows;
                    const auto tops = QApplication::topLevelWidgets();
                    for (auto* w : tops) {
                        QJsonObject win;
                        win["windowTitle"] = w->windowTitle();
                        win["className"] = QString::fromLatin1(w->metaObject()->className());
                        win["objectName"] = w->objectName();
                        win["isActiveWindow"] = w->isActiveWindow();
                        win["isVisible"] = w->isVisible();
                        win["isModal"] = w->isModal();

                        // Build a selector string for get_tree's root param
                        QString sel;
                        if (!w->objectName().isEmpty())
                            sel = "@name:" + w->objectName();
                        else
                            sel = "@class:" + QString::fromLatin1(w->metaObject()->className());
                        win["selector"] = sel;

                        QRect g = w->geometry();
                        QJsonObject geom;
                        geom["x"] = g.x();
                        geom["y"] = g.y();
                        geom["width"] = g.width();
                        geom["height"] = g.height();
                        win["geometry"] = geom;

                        windows.append(win);
                    }
                    QJsonObject wrapper;
                    wrapper["windows"] = windows;
                    result = wrapper;
                }
                // ── get_tree ──────────────────────────────────────────────
                else if (command == "get_tree") {
                    int depth = params.value("depth").toInt(5);
                    QString rootSel = params.value("root").toString();

                    QWidget* root = nullptr;
                    if (!rootSel.isEmpty()) {
                        root = resolveSelector(rootSel);
                    }
                    if (!root) {
                        // Default: pick first visible top-level
                        const auto tops = QApplication::topLevelWidgets();
                        for (auto* w : tops) {
                            if (w->isVisible()) { root = w; break; }
                        }
                        if (!root && !tops.isEmpty()) root = tops.first();
                    }

                    if (root) {
                        result = widgetToJson(root, 0, depth);
                    }
                }
                // ── click ─────────────────────────────────────────────────
                else if (command == "click") {
                    QString target = params.value("target").toString();
                    QWidget* w = resolveSelector(target);
                    if (w && w->isVisible() && w->isEnabled()) {
                        if (auto* btn = qobject_cast<QAbstractButton*>(w)) {
                            // Use QAbstractButton::click() for proper signal emission
                            QPointer<QWidget> safe = w;
                            QTimer::singleShot(10, [safe]() {
                                if (!safe) return;
                                if (auto* b = qobject_cast<QAbstractButton*>(safe.data()))
                                    b->click();
                            });
                        } else {
                            QPointer<QWidget> safe = w;
                            QTimer::singleShot(10, [safe]() {
                                if (!safe) return;
                                QTest::mouseClick(safe, Qt::LeftButton, Qt::NoModifier,
                                                  QPoint(safe->width() / 2, safe->height() / 2));
                            });
                        }
                    } else {
                        success = false;
                        result["error"] = target.isEmpty()
                            ? QStringLiteral("No target specified")
                            : QStringLiteral("Widget not found or not interactive: ") + target;
                    }
                }
                // ── invoke ────────────────────────────────────────────────
                else if (command == "invoke") {
                    QString target = params.value("target").toString();
                    QString method = params.value("method").toString();
                    QWidget* w = resolveSelector(target);
                    if (w && !method.isEmpty()) {
                        bool invoked = QMetaObject::invokeMethod(w, method.toUtf8().constData(),
                                                                 Qt::DirectConnection);
                        if (!invoked) {
                            // Try with Q_ARG variants for common types
                            invoked = QMetaObject::invokeMethod(
                                w, method.toUtf8().constData(), Qt::DirectConnection,
                                Q_ARG(int, 0));
                        }
                        success = invoked;
                        if (!success)
                            result["error"] = QStringLiteral("Method not found: ") + method;
                    } else {
                        success = false;
                        result["error"] = QStringLiteral("Widget not found or method empty");
                    }
                }
                // ── unknown command ──────────────────────────────────────
                else {
                    success = false;
                    result["error"] = QStringLiteral("Unknown command: ") + command;
                }

                // ── send response ─────────────────────────────────────────
                QJsonObject resp;
                resp["id"] = cmdId;
                if (success)
                    resp["result"] = result;
                else
                    resp["error"] = result.value("error").toString(
                        QStringLiteral("Command failed: ") + command);
                resp["success"] = success;

                socket->sendTextMessage(
                    QJsonDocument(resp).toJson(QJsonDocument::Compact));
            });

            connect(socket, &QWebSocket::disconnected, this, [this, socket]() {
                d->clients.removeAll(socket);
                socket->deleteLater();
            });
        }
    });

    return true;
}

void BVInjectServer::stopServer() {
    for (auto* c : d->clients) c->close();
    d->clients.clear();
    if (d->server) {
        d->server->close();
        d->server.reset();
    }
}

bool BVInjectServer::isRunning() const {
    return d->server && d->server->isListening();
}

QString BVInjectServer::version() const {
    return QStringLiteral("bv_ui_control v0.1.0 — inspired by qt-widgeteer");
}
