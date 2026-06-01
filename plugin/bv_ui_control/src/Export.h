#pragma once

#include <QtCore/qglobal.h>

#if defined(MYLIB_BUILDING_LIBRARY)
#  define MYLIB_EXPORT Q_DECL_EXPORT
#else
#  define MYLIB_EXPORT Q_DECL_IMPORT
#endif
