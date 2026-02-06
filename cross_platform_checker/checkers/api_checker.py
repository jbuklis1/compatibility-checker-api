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
                    if api.endswith('_'):
                        pattern = r'\b' + re.escape(api)
                    else:
                        pattern = r'\b' + re.escape(api) + r'\s*\('
                    for m in re.finditer(pattern, line, re.IGNORECASE):
                        if position_inside_string_literal(line, m.start()):
                            continue
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
