---
name: wireguard-vpn
description: >-
  Use when setting up a WireGuard VPN on a Linux server or client, when
  troubleshooting a WireGuard handshake, or when migrating from an
  OpenVPN / IPSec deployment. Applies when the user asks for "WireGuard
  setup", "wireguard endpoint", "wg-quick", or "kernel VPN tunnel". Do
  not use for IPSec tunnels, for managed SaaS VPN products (Tailscale,
  Cloudflare Tunnel), or for non-Linux platforms.
skill_type: domain-expert
domain_focus: networking
tags:
  - wireguard
  - vpn
  - networking
  - linux
  - kernel
version: 1.0.0
version_notes: Gallery reference for kernel-module WireGuard on Linux ≥ 5.6.
token_budget: 1500
---

## When to use

Use when you need a kernel-level mesh VPN between two or more Linux hosts
and the kernel module is available (Linux ≥ 5.6 ships `wireguard.ko` in
the mainline kernel). WireGuard is the right answer when you want:

- UDP-based tunnels with sub-millisecond overhead per packet.
- Modern cryptography only (Curve25519 for key exchange, ChaCha20 for
  symmetric, Poly1305 for MAC). No cipher negotiation, no downgrade
  surface.
- A configuration that fits in one file and can be diffed in version
  control.

It is the wrong answer when you need a managed SaaS connector, when the
hosts run operating systems without the kernel module, or when the
firewall at the perimeter blocks UDP outright — WireGuard does not
fall back to TCP.

## Examples

A minimal server-side `/etc/wireguard/wg0.conf`:

```ini
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <server-private-key-base64>
# Replace with your firewall rule before bringing the interface up
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = <client-public-key-base64>
AllowedIPs = 10.0.0.2/32
```

The corresponding client config:

```ini
[Interface]
Address = 10.0.0.2/24
PrivateKey = <client-private-key-base64>

[Peer]
PublicKey = <server-public-key-base64>
Endpoint = vpn.example.com:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
```

Bringing the interface up and confirming the handshake:

```bash
sudo wg-quick up wg0
sudo wg show
# expected: latest handshake within the last 2 minutes, transfer counters climbing
```

For example, generating keys with the `wg` utility:

```bash
wg genkey | tee privatekey | wg pubkey > publickey
```

## Pitfalls to avoid

- Do not commit the `PrivateKey` to a public repo; it is the long-term
  identity for the interface and revoking it requires redistributing a
  new key to every peer.
- Do not forget to open UDP `51820` (or your chosen port) on the cloud
  provider's security group; the kernel module loads fine without it,
  but no handshake ever arrives.
- Do not set `AllowedIPs = 0.0.0.0/0` on the client unless you intend
  the tunnel to be the default route; a misconfigured server `AllowedIPs`
  silently black-holes the client's traffic.
- Do not run WireGuard over TCP wrappers like `tcp_tunnel`; the kernel
  module speaks UDP only, and any TCP fallback you build is a separate
  application that does not benefit from the kernel fast path.
- Do not skip `PersistentKeepalive` on peers behind a NAT; without it
  the NAT mapping expires and the next inbound handshake fails
  silently.