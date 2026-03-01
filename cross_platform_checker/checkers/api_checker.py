"""
Platform-specific API checks.
"""

import re
from typing import List

from ..checker_base import BaseChecker
from ..issue import Severity
from ..utils import position_inside_string_literal


class APIChecker(BaseChecker):
    """Checks for platform-specific API usage."""
    
    def _run_checks(self):
        """Run API-related checks."""
        self._check_platform_specific_apis()
        self._check_library_imports()
        self._check_threading_apis()
        self._check_network_code()
        self._check_gui_code()
    
    def _check_platform_specific_apis(self):
        """Check for platform-specific API usage."""
        platform_apis = {
            'win32': [
                'win32api', 'win32con', 'win32file', 'win32gui',
                'win32process', 'win32service', 'win32security',
                'CreateFile', 'ReadFile', 'WriteFile', 'CloseHandle',
                'GetModuleHandle', 'GetProcAddress', 'LoadLibrary',
            ],
            'unix': [
                'fork', 'exec', 'pthread_', 'sigaction', 'signal',
                'fcntl', 'ioctl', 'unlink', 'link', 'symlink',
            ],
            'macos': [
                'Cocoa', 'NSApplication', 'NSWindow', 'AppKit',
                'CoreFoundation', 'CFBundle', 'CFString',
            ],
        }
        
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
                
            for platform, apis in platform_apis.items():
                for api in apis:
                    # Python's high-level file APIs like Path.unlink / os.unlink are
                    # available on all major platforms, so don't treat "unlink" as a
                    # Unix-only primitive when analyzing Python source.
                    if self.language == 'python' and api == 'unlink':
                        continue
                    if api.endswith('_'):
                        pattern = r'\b' + re.escape(api)
                    else:
                        pattern = r'\b' + re.escape(api) + r'\s*\('
                    for m in re.finditer(pattern, line, re.IGNORECASE):
                        if position_inside_string_literal(line, m.start()):
                            continue
                        # Python's exec() runs code strings and is cross-platform; only flag Unix-style exec in other languages
                        if api == 'exec' and self.language == 'python':
                            continue
                        # C/C++ exec may be Qt's cross-platform exec(); send to pruner to drop Qt context
                        if api == 'exec' and self.language in ('c', 'cpp') and self.candidates is not None:
                            self._add_candidate(
                                Severity.ERROR, i, m.start(),
                                f"Platform-specific API detected: {api} ({platform})",
                                line.strip(),
                                "Use cross-platform alternatives or add platform-specific guards (#ifdef, if platform.system(), etc.)",
                                "PLATFORM_API",
                                "exec_call",
                                {},
                            )
                        else:
                            self._add_issue(
                                Severity.ERROR, i, m.start(),
                                f"Platform-specific API detected: {api} ({platform})",
                                line.strip(),
                                "Use cross-platform alternatives or add platform-specific guards (#ifdef, if platform.system(), etc.)",
                                "PLATFORM_API",
                            )
                        break
    
    def _check_library_imports(self):
        """Check for platform-specific library imports."""
        platform_libs = {
            'python': [
                'win32api', 'win32con', 'win32file', 'win32gui',
                'pyobjc', 'Cocoa', 'AppKit',  # macOS
            ],
            'cpp': [
                '<windows.h>', '<winsock.h>', '<winsock2.h>',
                '<sys/socket.h>', '<unistd.h>', '<pthread.h>',
                '<Cocoa/Cocoa.h>', '<AppKit/AppKit.h>',
            ],
            'c': [
                '<windows.h>', '<winsock.h>', '<winsock2.h>',
                '<sys/socket.h>', '<unistd.h>', '<pthread.h>',
                '<Cocoa/Cocoa.h>', '<AppKit/AppKit.h>',
            ],
            'rust': [],  # handled by pattern-based check below
            'csharp': [],  # handled by pattern-based check below
        }
        
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            libs = platform_libs.get(self.language, [])
            for lib in libs:
                idx = line.find(lib)
                if idx != -1 and not position_inside_string_literal(line, idx):
                    self._add_issue(
                        Severity.ERROR, i, idx,
                        f"Platform-specific library import: {lib}",
                        line.strip(),
                        "Use cross-platform libraries or add platform guards",
                        "LIBRARY_IMPORT",
                    )
                    break
            # C/C++: pattern-based includes for OS and display-server (Linux, Wayland, X11)
            if self.language in ('c', 'cpp'):
                m = re.search(r'#include\s*<([^>]+)>', line)
                if m and not position_inside_string_literal(line, m.start()):
                    header = m.group(1).strip()
                    if header.startswith('linux/'):
                        self._add_issue(
                            Severity.WARNING, i, m.start(),
                            "Linux kernel / OS-specific include",
                            line.strip(),
                            "Add platform guards or use portable abstractions for cross-OS compatibility",
                            "LIBRARY_IMPORT",
                        )
                    elif header.startswith('wayland-') or header.startswith('wayland/'):
                        self._add_issue(
                            Severity.WARNING, i, m.start(),
                            "Wayland-specific include; not available on X11-only or other display servers",
                            line.strip(),
                            "Use conditional compilation or abstraction for X11/Wayland portability",
                            "LIBRARY_IMPORT",
                        )
                    elif header.startswith('X11/'):
                        self._add_issue(
                            Severity.WARNING, i, m.start(),
                            "X11-specific include; not available on Wayland-only systems",
                            line.strip(),
                            "Consider X11/Wayland portability or abstraction layer",
                            "LIBRARY_IMPORT",
                        )
                    elif header.startswith('xcb/'):
                        self._add_issue(
                            Severity.WARNING, i, m.start(),
                            "X11 XCB include; not available on Wayland-only systems",
                            line.strip(),
                            "Consider X11/Wayland portability or abstraction layer",
                            "LIBRARY_IMPORT",
                        )
            # Rust: OS-associated crates (use ...:: or extern crate ...)
            if self.language == 'rust':
                use_match = re.search(r'\buse\s+([a-zA-Z0-9_]+)(?:::|;)', line)
                if use_match and not position_inside_string_literal(line, use_match.start()):
                    crate = use_match.group(1)
                    if crate in ('winapi', 'windows_sys', 'libc', 'nix') or crate.startswith('linux_'):
                        self._add_issue(
                            Severity.WARNING, i, use_match.start(),
                            f"OS-associated crate: {crate}",
                            line.strip(),
                            "Add cfg(target_os) guards or document target platforms for cross-platform compatibility",
                            "LIBRARY_IMPORT",
                        )
                extern_match = re.search(r'\bextern\s+crate\s+([a-zA-Z0-9_]+)\s*;', line)
                if extern_match and not position_inside_string_literal(line, extern_match.start()):
                    crate = extern_match.group(1)
                    if crate in ('winapi', 'libc', 'nix') or crate.startswith('linux_'):
                        self._add_issue(
                            Severity.WARNING, i, extern_match.start(),
                            f"OS-associated crate: {crate}",
                            line.strip(),
                            "Add cfg(target_os) guards or document target platforms for cross-platform compatibility",
                            "LIBRARY_IMPORT",
                        )
            # C#: platform-specific namespaces and DllImport
            if self.language == 'csharp':
                for pattern, msg in (
                    (r'\busing\s+Microsoft\.Win32\s*;', "Windows-specific namespace: Microsoft.Win32"),
                    (r'\busing\s+Mono\.Unix\s*;', "Mono/Unix-specific namespace"),
                    (r'\busing\s+Mono\.Posix\s*;', "Mono/Unix-specific namespace"),
                    (r'DllImport\s*\(\s*["\'][^"\']*kernel32', "Windows-specific DllImport (kernel32)"),
                    (r'DllImport\s*\(\s*["\'][^"\']*ntdll', "Windows-specific DllImport (ntdll)"),
                ):
                    m = re.search(pattern, line)
                    if m and not position_inside_string_literal(line, m.start()):
                        self._add_issue(
                            Severity.WARNING, i, m.start(),
                            msg,
                            line.strip(),
                            "Use cross-platform APIs or RuntimeInformation.IsOSPlatform guards",
                            "LIBRARY_IMPORT",
                        )
                        break
            # Go: syscall and platform-specific packages (import "path" - path is in quotes, so match the import line)
            if self.language == 'go':
                m_syscall = re.search(r'import\s+(?:\s*[a-zA-Z0-9_]*\s+)?["\']syscall["\']', line)
                if m_syscall:
                    self._add_issue(
                        Severity.WARNING, i, m_syscall.start(),
                        "Platform-specific package: syscall",
                        line.strip(),
                        "Use build tags or runtime.GOOS guards for cross-platform compatibility",
                        "LIBRARY_IMPORT",
                    )
                m_sys = re.search(r'["\'](golang\.org/x/sys/(?:windows|unix|plan9)[^"\']*)["\']', line)
                if m_sys:
                    self._add_issue(
                        Severity.WARNING, i, m_sys.start(1),
                        "Platform-specific package: golang.org/x/sys",
                        line.strip(),
                        "Use build tags or runtime.GOOS guards for cross-platform compatibility",
                        "LIBRARY_IMPORT",
                    )
    
    def _check_threading_apis(self):
        """Check for threading API issues."""
        threading_patterns = [
            (r'pthread_', 'Unix-specific pthread API'),
            (r'CreateThread', 'Windows-specific thread API'),
            (r'_beginthread', 'Windows-specific thread API'),
        ]
        
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            for pattern, desc in threading_patterns:
                m = re.search(pattern, line)
                if m and not position_inside_string_literal(line, m.start()):
                    self._add_issue(
                        Severity.ERROR, i, m.start(),
                        f"{desc} detected",
                        line.strip(),
                        "Use std::thread (C++11+), threading module (Python), or cross-platform threading libraries",
                        "THREADING",
                    )
                    break
    
    def _check_network_code(self):
        """Check for network-related issues."""
        for i, line in enumerate(self.lines, 1):
            idx = line.find("WSAStartup")
            if idx != -1 and not position_inside_string_literal(line, idx):
                self._add_issue(
                    Severity.ERROR, i, idx,
                    "Windows-specific socket initialization (WSAStartup) detected",
                    line.strip(),
                    "Use cross-platform socket APIs (BSD sockets work on all platforms)",
                    "NETWORK",
                )
    
    def _check_gui_code(self):
        """Check for GUI framework issues."""
        gui_frameworks = {
            'windows_specific': ['win32gui', 'MFC', 'WPF', 'WinForms'],
            'macos_specific': ['Cocoa', 'AppKit', 'NSApplication'],
        }
        
        for i, line in enumerate(self.lines, 1):
            if self._is_comment(line):
                continue
            for category, frameworks in gui_frameworks.items():
                for framework in frameworks:
                    idx = line.find(framework)
                    if idx != -1 and not position_inside_string_literal(line, idx):
                        self._add_issue(
                            Severity.ERROR, i, idx,
                            f"Platform-specific GUI framework: {framework}",
                            line.strip(),
                            "Use cross-platform GUI frameworks (Qt, wxWidgets, Tkinter, etc.)",
                            "GUI",
                        )
