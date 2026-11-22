#pragma once
#include <windows.h>
static inline int backtrace(void **buffer, int size) {
    return CaptureStackBackTrace(1, size, buffer, NULL);
}
