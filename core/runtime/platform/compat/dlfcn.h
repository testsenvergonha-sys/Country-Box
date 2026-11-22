#ifndef _DLFCN_H
#define _DLFCN_H

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>

#define RTLD_NOW 0
#define RTLD_GLOBAL 0
#define RTLD_LOCAL 0
#define RTLD_LAZY 0

static inline void *dlopen(const char *filename, int flag) {
    (void)flag;
    if (!filename) return (void *)GetModuleHandleA(NULL);
    return (void *)LoadLibraryA(filename);
}

static inline void *dlsym(void *handle, const char *symbol) {
    return (void *)GetProcAddress((HMODULE)handle, symbol);
}

static inline int dlclose(void *handle) {
    return FreeLibrary((HMODULE)handle) ? 0 : -1;
}

static inline char *dlerror(void) {
    return (char *)"dlerror";
}

#endif /* _WIN32 */
#endif /* _DLFCN_H */
