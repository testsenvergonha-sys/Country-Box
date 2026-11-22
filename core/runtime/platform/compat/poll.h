#ifndef _POLL_H
#define _POLL_H

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <io.h>

#define POLLIN   0x0001
#define POLLPRI  0x0002
#define POLLOUT  0x0004
#define POLLERR  0x0008
#define POLLHUP  0x0010
#define POLLNVAL 0x0020

struct pollfd {
    int   fd;
    short events;
    short revents;
};

typedef unsigned long nfds_t;

static inline int poll(struct pollfd *fds, nfds_t nfds, int timeout) {
    if (nfds == 0) {
        if (timeout > 0) Sleep(timeout);
        return 0;
    }
    DWORD t0 = GetTickCount();
    for (;;) {
        int ready = 0;
        for (nfds_t i = 0; i < nfds; i++) {
            fds[i].revents = 0;
            HANDLE h = (HANDLE)_get_osfhandle(fds[i].fd);
            if (h == INVALID_HANDLE_VALUE) {
                fds[i].revents = POLLNVAL;
                ready++;
                continue;
            }
            DWORD avail = 0;
            if (PeekNamedPipe(h, NULL, 0, NULL, &avail, NULL)) {
                if (avail > 0) {
                    fds[i].revents |= POLLIN;
                    ready++;
                }
            } else {
                DWORD err = GetLastError();
                if (err == ERROR_BROKEN_PIPE || err == ERROR_HANDLE_EOF) {
                    fds[i].revents |= POLLHUP;
                    ready++;
                }
            }
        }
        if (ready > 0) return ready;
        if (timeout == 0) return 0;
        if (timeout > 0 && (int)(GetTickCount() - t0) >= timeout) return 0;
        Sleep(5);
    }
}

#endif /* _WIN32 */
#endif /* _POLL_H */
