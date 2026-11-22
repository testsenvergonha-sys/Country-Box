#pragma once
#include <string.h>
#define PRIO_PROCESS 0
#define RUSAGE_SELF 0
typedef unsigned int id_t;
typedef unsigned long rlim_t;
#define RLIM_INFINITY ((rlim_t)-1)
#define RLIMIT_NICE 13
struct rlimit {
    rlim_t rlim_cur;
    rlim_t rlim_max;
};
struct rusage {
    struct { long tv_sec; long tv_usec; } ru_utime;
    struct { long tv_sec; long tv_usec; } ru_stime;
    long ru_maxrss;
    long ru_minflt;
    long ru_majflt;
};
static inline int getpriority(int which, int who) { (void)which; (void)who; return 0; }
static inline int setpriority(int which, int who, int prio) { (void)which; (void)who; (void)prio; return 0; }
static inline int getrlimit(int resource, struct rlimit *rl) { (void)resource; if (rl) { rl->rlim_cur = RLIM_INFINITY; rl->rlim_max = RLIM_INFINITY; } return 0; }
static inline int getrusage(int who, struct rusage *r) { (void)who; if (r) memset(r, 0, sizeof *r); return 0; }
static inline int geteuid(void) { return 0; }
