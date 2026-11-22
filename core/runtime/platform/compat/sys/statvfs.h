#ifndef _SYS_STATVFS_H
#define _SYS_STATVFS_H

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <stdint.h>
#include <string.h>

struct statvfs {
    unsigned long f_bsize;
    unsigned long f_frsize;
    uint64_t      f_blocks;
    uint64_t      f_bfree;
    uint64_t      f_bavail;
    uint64_t      f_files;
    uint64_t      f_ffree;
    uint64_t      f_favail;
    unsigned long f_fsid;
    unsigned long f_flag;
    unsigned long f_namemax;
};

#define ST_NOEXEC 0

static inline int statvfs(const char *path, struct statvfs *buf) {
    if (!buf) return -1;
    memset(buf, 0, sizeof(*buf));
    buf->f_frsize = 4096;
    buf->f_bsize = 4096;
    ULARGE_INTEGER freeBytes, totalBytes, totalFree;
    if (GetDiskFreeSpaceExA(path, &freeBytes, &totalBytes, &totalFree)) {
        buf->f_bavail = freeBytes.QuadPart / 4096;
        buf->f_bfree  = totalFree.QuadPart / 4096;
        buf->f_blocks = totalBytes.QuadPart / 4096;
        return 0;
    }
    return -1;
}

#endif /* _WIN32 */
#endif /* _SYS_STATVFS_H */
