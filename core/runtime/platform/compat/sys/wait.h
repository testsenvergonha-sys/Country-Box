#pragma once
#define WNOHANG 1
#define WIFEXITED(status) 1
#define WEXITSTATUS(status) ((status) & 0xFF)
