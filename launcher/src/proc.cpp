// Country-Box launcher: child processes (proc.h).
#include "proc.h"

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <io.h>
#include <fcntl.h>
#include <chrono>
#include <map>
#include <mutex>
#include <vector>
#include <string>

static std::string build_cmdline(const std::vector<std::string> &argv) {
    std::string s;
    for (size_t i = 0; i < argv.size(); i++) {
        if (i > 0) s += ' ';
        const std::string &arg = argv[i];
        bool need_quote = arg.empty() || arg.find_first_of(" \t\n\v\"") != std::string::npos;
        if (!need_quote) {
            s += arg;
        } else {
            s += '"';
            for (auto it = arg.begin(); ; ++it) {
                unsigned nback = 0;
                while (it != arg.end() && *it == '\\') {
                    ++it;
                    ++nback;
                }
                if (it == arg.end()) {
                    s.append(nback * 2, '\\');
                    break;
                } else if (*it == '"') {
                    s.append(nback * 2 + 1, '\\');
                    s.push_back(*it);
                } else {
                    s.append(nback, '\\');
                    s.push_back(*it);
                }
            }
            s += '"';
        }
    }
    return s;
}

static std::mutex g_proc_mu;
static std::map<pid_t, HANDLE> g_procs;

int proc_run(const std::vector<std::string> &argv, const std::string &cwd, const std::vector<std::string> &env,
             std::string &out, int timeout_ms) {
    out.clear();
    if (argv.empty()) return -1;

    SECURITY_ATTRIBUTES sa = {sizeof(sa), NULL, TRUE};
    HANDLE hRead = NULL, hWrite = NULL;
    if (!CreatePipe(&hRead, &hWrite, &sa, 0)) return -1;
    SetHandleInformation(hRead, HANDLE_FLAG_INHERIT, 0);

    STARTUPINFOA si = {sizeof(si)};
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdOutput = hWrite;
    si.hStdError = GetStdHandle(STD_ERROR_HANDLE);
    si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);

    PROCESS_INFORMATION pi = {0};
    std::string cmd = build_cmdline(argv);

    for (const auto &e : env) {
        _putenv(e.c_str());
    }

    const char *work_dir = cwd.empty() ? NULL : cwd.c_str();
    BOOL ok = CreateProcessA(NULL, cmd.data(), NULL, NULL, TRUE, 0, NULL, work_dir, &si, &pi);
    CloseHandle(hWrite);
    if (!ok) {
        CloseHandle(hRead);
        return -1;
    }
    CloseHandle(pi.hThread);

    DWORD t0 = GetTickCount();
    char buf[16384];
    bool timed_out = false;
    for (;;) {
        DWORD avail = 0;
        if (PeekNamedPipe(hRead, NULL, 0, NULL, &avail, NULL)) {
            if (avail > 0) {
                DWORD bytesRead = 0;
                DWORD toRead = sizeof(buf) < avail ? (DWORD)sizeof(buf) : avail;
                if (ReadFile(hRead, buf, toRead, &bytesRead, NULL) && bytesRead > 0) {
                    out.append(buf, bytesRead);
                    continue;
                }
            }
        }
        DWORD wait = WaitForSingleObject(pi.hProcess, 10);
        if (wait == WAIT_OBJECT_0) {
            DWORD bytesRead = 0;
            while (ReadFile(hRead, buf, sizeof(buf), &bytesRead, NULL) && bytesRead > 0) {
                out.append(buf, bytesRead);
            }
            break;
        }
        if (timeout_ms > 0 && (int)(GetTickCount() - t0) >= timeout_ms) {
            timed_out = true;
            TerminateProcess(pi.hProcess, 1);
            break;
        }
    }
    CloseHandle(hRead);

    DWORD exit_code = 0;
    GetExitCodeProcess(pi.hProcess, &exit_code);
    CloseHandle(pi.hProcess);
    return timed_out ? -1 : (int)exit_code;
}

pid_t proc_spawn(const std::vector<std::string> &argv, const std::string &cwd, const std::string &log) {
    if (argv.empty()) return -1;

    STARTUPINFOA si = {sizeof(si)};
    HANDLE hLog = INVALID_HANDLE_VALUE;
    if (!log.empty()) {
        SECURITY_ATTRIBUTES sa = {sizeof(sa), NULL, TRUE};
        hLog = CreateFileA(log.c_str(), FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
        if (hLog != INVALID_HANDLE_VALUE) {
            si.dwFlags |= STARTF_USESTDHANDLES;
            si.hStdOutput = hLog;
            si.hStdError = hLog;
            si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
        }
    }

    PROCESS_INFORMATION pi = {0};
    std::string cmd = build_cmdline(argv);
    const char *work_dir = cwd.empty() ? NULL : cwd.c_str();

    BOOL ok = CreateProcessA(NULL, cmd.data(), NULL, NULL, hLog != INVALID_HANDLE_VALUE, CREATE_NEW_PROCESS_GROUP, NULL, work_dir, &si, &pi);
    if (hLog != INVALID_HANDLE_VALUE) CloseHandle(hLog);
    if (!ok) return -1;

    CloseHandle(pi.hThread);
    pid_t pid = (pid_t)pi.dwProcessId;
    {
        std::lock_guard<std::mutex> lock(g_proc_mu);
        g_procs[pid] = pi.hProcess;
    }
    return pid;
}

int proc_poll(pid_t pid, int *status) {
    HANDLE hProcess = NULL;
    {
        std::lock_guard<std::mutex> lock(g_proc_mu);
        auto it = g_procs.find(pid);
        if (it != g_procs.end()) {
            hProcess = it->second;
        }
    }
    if (!hProcess) {
        hProcess = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_INFORMATION, FALSE, (DWORD)pid);
        if (!hProcess) return -1;
    }

    DWORD wait = WaitForSingleObject(hProcess, 0);
    if (wait == WAIT_TIMEOUT) return 1;

    DWORD exit_code = 0;
    GetExitCodeProcess(hProcess, &exit_code);
    if (status) *status = (int)exit_code;

    {
        std::lock_guard<std::mutex> lock(g_proc_mu);
        g_procs.erase(pid);
    }
    CloseHandle(hProcess);
    return 0;
}

#else /* !_WIN32 */

#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstring>
#include <fcntl.h>
#include <poll.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

static std::vector<char *> cargv(const std::vector<std::string> &v) {
    std::vector<char *> a;
    for (auto &s : v) a.push_back(const_cast<char *>(s.c_str()));
    a.push_back(nullptr);
    return a;
}

int proc_run(const std::vector<std::string> &argv, const std::string &cwd, const std::vector<std::string> &env,
             std::string &out, int timeout_ms) {
    out.clear();
    int fds[2];
    if (argv.empty() || pipe2(fds, O_CLOEXEC)) return -1;
    auto args = cargv(argv);
    pid_t pid = fork();
    if (pid < 0) {
        close(fds[0]), close(fds[1]);
        return -1;
    }
    if (pid == 0) {
        dup2(fds[1], 1);
        int null = open("/dev/null", O_WRONLY);
        if (null >= 0) dup2(null, 2);
        if (!cwd.empty() && chdir(cwd.c_str())) _exit(127);
        for (auto &e : env) putenv(const_cast<char *>(e.c_str()));
        execv(args[0], args.data());
        _exit(127);
    }
    close(fds[1]);
    auto t0 = std::chrono::steady_clock::now();
    char buf[16384];
    bool timed_out = false;
    for (;;) {
        int left = timeout_ms - (int)std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
        if (left <= 0) {
            timed_out = true;
            break;
        }
        struct pollfd p = {fds[0], POLLIN, 0};
        int r = poll(&p, 1, left);
        if (r < 0 && errno == EINTR) continue;
        if (r <= 0) {
            timed_out = r == 0;
            break;
        }
        ssize_t n = read(fds[0], buf, sizeof buf);
        if (n <= 0) break;
        out.append(buf, (size_t)n);
    }
    close(fds[0]);
    if (timed_out) kill(pid, SIGKILL);
    int st = 0;
    while (waitpid(pid, &st, 0) < 0 && errno == EINTR) {
    }
    if (timed_out) return -1;
    return WIFEXITED(st) ? WEXITSTATUS(st) : -1;
}

pid_t proc_spawn(const std::vector<std::string> &argv, const std::string &cwd, const std::string &log) {
    if (argv.empty()) return -1;
    auto args = cargv(argv);
    pid_t pid = fork();
    if (pid != 0) return pid;
    setsid();
    int fd = open(log.c_str(), O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (fd >= 0) dup2(fd, 1), dup2(fd, 2);
    int null = open("/dev/null", O_RDONLY);
    if (null >= 0) dup2(null, 0);
    if (!cwd.empty() && chdir(cwd.c_str())) _exit(127);
    execv(args[0], args.data());
    _exit(127);
}

int proc_poll(pid_t pid, int *status) {
    int st = 0;
    pid_t r = waitpid(pid, &st, WNOHANG);
    if (r == 0) return 1;
    if (r < 0) return -1;
    if (status) *status = WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st);
    return 0;
}

#endif /* _WIN32 */
