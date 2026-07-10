"""Print one free TCP port the OS hands us. Used by Start_TomeMaster.bat to
claim a frontend port dynamically (zero hardcoded ports), mirroring run.py."""
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
