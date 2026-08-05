"""Check whether UDP can actually reach this machine.

The game is peer-to-peer: whoever hosts must accept INBOUND UDP on the port.
If your friend can host but you can't, inbound traffic to your machine is
being blocked -- your firewall, not the game.

USAGE
-----
On the machine that wants to HOST:

    python netcheck.py --listen

It prints your LAN addresses and waits. On the other machine:

    python netcheck.py --ping 10.114.102.49

If the listener prints "GOT PACKET", the network path is fine and the game
will work. If it never does, inbound UDP is blocked -- see the hints it
prints at the end.
"""

import argparse
import socket
import sys
import time

PORT = 50007


def my_addresses():
    """Best-effort list of this machine's non-loopback IPv4 addresses."""
    addrs = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None,
                                       socket.AF_INET):
            addrs.add(info[4][0])
    except socket.gaierror:
        pass
    # the routing trick: what source IP would we use to reach the internet?
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        addrs.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return sorted(a for a in addrs if not a.startswith("127."))


def listen(port):
    addrs = my_addresses()
    print("This machine's addresses:")
    for a in addrs:
        tag = ""
        if a.startswith("172.17."):
            tag = "   <- Docker bridge, NOT reachable by your friend"
        elif a.startswith("169.254."):
            tag = "   <- link-local, network didn't assign properly"
        print(f"  {a}{tag}")
    usable = [a for a in addrs
              if not a.startswith(("172.17.", "169.254."))]
    if usable:
        print(f"\nTell your friend to run:")
        print(f"  python netcheck.py --ping {usable[0]}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", port))
    except OSError as e:
        print(f"\nFAILED to bind port {port}: {e}")
        print("Something else is already using it (an old game still running?)")
        return
    sock.settimeout(1.0)
    print(f"\nListening on UDP {port}. Waiting 60s... (Ctrl-C to stop)\n")

    start = time.time()
    got = 0
    while time.time() - start < 60:
        try:
            data, addr = sock.recvfrom(1024)
        except socket.timeout:
            continue
        except KeyboardInterrupt:
            break
        got += 1
        print(f"  GOT PACKET from {addr[0]}:{addr[1]} -> {data[:40]!r}")
        sock.sendto(b"reply", addr)
        if got >= 3:
            break

    print()
    if got:
        print("SUCCESS: inbound UDP works. You can host the game.")
    else:
        print("NO PACKETS RECEIVED. Inbound UDP is blocked. Try:")
        print()
        print("  Linux (ufw):   sudo ufw allow 50007/udp")
        print("  Linux (check): sudo ufw status")
        print("  Windows:       allow the app when prompted, and set the")
        print("                 network profile to Private, not Public")
        print("  Also check:    your friend used the right IP, and your")
        print("                 hotspot doesn't have AP/client isolation on")
    sock.close()


def ping(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    print(f"Sending 5 packets to {host}:{port} ...")
    replies = 0
    for i in range(5):
        try:
            sock.sendto(f"hello {i}".encode(), (host, port))
        except OSError as e:
            print(f"  send failed: {e}")
            break
        try:
            data, addr = sock.recvfrom(1024)
            replies += 1
            print(f"  reply from {addr[0]}: {data!r}")
        except socket.timeout:
            print(f"  packet {i}: no reply (may still have arrived)")
        time.sleep(0.3)
    print()
    if replies:
        print("SUCCESS: two-way UDP works between these machines.")
    else:
        print("No replies. Check the listener's output -- if it shows")
        print("'GOT PACKET' then only the return path is blocked; if it")
        print("shows nothing, the host's firewall is dropping inbound UDP.")
    sock.close()


def main():
    p = argparse.ArgumentParser(description="UDP connectivity check")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--listen", action="store_true",
                   help="run on the machine that wants to host")
    g.add_argument("--ping", metavar="HOST_IP",
                   help="run on the other machine")
    p.add_argument("--port", type=int, default=PORT)
    a = p.parse_args()
    if a.listen:
        listen(a.port)
    else:
        ping(a.ping, a.port)


if __name__ == "__main__":
    main()