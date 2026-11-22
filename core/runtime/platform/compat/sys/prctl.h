#pragma once
#define PR_SET_TIMERSLACK 29
#define PR_SET_NAME 15
#define PR_SET_PTRACER 0x59616d61
#define PR_SET_PTRACER_ANY ((unsigned long)-1)
static inline int prctl(int option, ...) { (void)option; return 0; }
