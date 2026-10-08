import json
import urllib.parse
from typing import List, Dict, Optional, Tuple


def parse_proxy_link(link: str) -> Optional[Dict]:
    """Разбирает ссылку vless:// или hysteria2:// на составляющие компоненты."""
    try:
        url = urllib.parse.urlsplit(link.strip())
        proto = url.scheme.lower()
        if proto not in ("vless", "hysteria2"):
            return None

        # User / UUID / Password
        uuid_or_pw = url.username or ""
        if not uuid_or_pw and "@" in url.netloc:
            uuid_or_pw = url.netloc.split("@")[0]

        host = url.hostname or ""
        port = url.port or 443

        query = urllib.parse.parse_qs(url.query)
        params = {k: v[0] for k, v in query.items()}

        tag = urllib.parse.unquote(url.fragment) if url.fragment else f"{proto}_{host}"

        return {
            "proto": proto,
            "uuid": uuid_or_pw,
            "host": host,
            "port": port,
            "params": params,
            "tag": tag,
        }
    except Exception:
        return None


def convert_to_clash_proxy(proxy: Dict) -> Optional[Dict]:
    """Конвертирует распарсенный прокси в структуру Clash Meta (Mihomo)."""
    proto = proxy["proto"]
    tag = proxy["tag"]
    host = proxy["host"]
    port = proxy["port"]
    uuid_or_pw = proxy["uuid"]
    params = proxy["params"]

    if proto == "hysteria2":
        return {
            "name": tag,
            "type": "hysteria2",
            "server": host,
            "port": port,
            "password": uuid_or_pw,
            "sni": params.get("sni", host),
            "skip-cert-verify": False,
        }

    if proto == "vless":
        item = {
            "name": tag,
            "type": "vless",
            "server": host,
            "port": port,
            "uuid": uuid_or_pw,
            "udp": True,
        }

        # Network transport
        net_type = params.get("type", "tcp")
        item["network"] = net_type

        # Flow (xtls-rprx-vision)
        flow = params.get("flow")
        if flow:
            item["flow"] = flow

        # Security (reality / tls)
        security = params.get("security", "")
        if security in ("reality", "tls"):
            item["tls"] = True
            sni = params.get("sni") or params.get("host") or host
            item["servername"] = sni

            fp = params.get("fp")
            if fp:
                item["client-fingerprint"] = fp

            if security == "reality":
                reality_opts = {}
                if "pbk" in params:
                    reality_opts["public-key"] = params["pbk"]
                if "sid" in params:
                    reality_opts["short-id"] = params["sid"]
                item["reality-opts"] = reality_opts

        # xhttp / http options
        if net_type in ("xhttp", "http"):
            opts = {}
            if "path" in params:
                opts["path"] = urllib.parse.unquote(params["path"])
            if "host" in params:
                opts["host"] = params["host"]
            if "mode" in params:
                opts["mode"] = params["mode"]
            item[f"{net_type}-opts"] = opts

        # ALPN
        if "alpn" in params:
            item["alpn"] = [a.strip() for a in params["alpn"].split(",") if a.strip()]

        return item

    return None


def convert_to_singbox_outbound(proxy: Dict) -> Optional[Dict]:
    """Конвертирует распарсенный прокси в структуру Sing-Box outbound."""
    proto = proxy["proto"]
    tag = proxy["tag"]
    host = proxy["host"]
    port = proxy["port"]
    uuid_or_pw = proxy["uuid"]
    params = proxy["params"]

    if proto == "hysteria2":
        return {
            "type": "hysteria2",
            "tag": tag,
            "server": host,
            "server_port": port,
            "password": uuid_or_pw,
            "tls": {
                "enabled": True,
                "server_name": params.get("sni", host),
            },
        }

    if proto == "vless":
        outbound = {
            "type": "vless",
            "tag": tag,
            "server": host,
            "server_port": port,
            "uuid": uuid_or_pw,
        }

        # Flow
        flow = params.get("flow")
        if flow:
            outbound["flow"] = flow

        # Network transport
        net_type = params.get("type", "tcp")
        if net_type in ("xhttp", "http", "ws", "grpc"):
            transport_opts = {
                "type": net_type,
            }
            if "path" in params:
                transport_opts["path"] = urllib.parse.unquote(params["path"])
            if "host" in params:
                transport_opts["host"] = params["host"]
            if "mode" in params:
                transport_opts["mode"] = params["mode"]
            outbound["transport"] = transport_opts
        else:
            outbound["network"] = "tcp"

        # Security (TLS / Reality)
        security = params.get("security", "")
        if security in ("reality", "tls"):
            tls_opts = {
                "enabled": True,
                "server_name": params.get("sni") or params.get("host") or host,
            }

            if "fp" in params:
                tls_opts["utls"] = {
                    "enabled": True,
                    "fingerprint": params["fp"],
                }

            if "alpn" in params:
                tls_opts["alpn"] = [a.strip() for a in params["alpn"].split(",") if a.strip()]

            if security == "reality":
                reality_opts = {
                    "enabled": True,
                }
                if "pbk" in params:
                    reality_opts["public_key"] = params["pbk"]
                if "sid" in params:
                    reality_opts["short_id"] = params["sid"]
                tls_opts["reality"] = reality_opts

            outbound["tls"] = tls_opts

        return outbound

    return None


def generate_clash_yaml(servers: List[Dict]) -> str:
    """Генерирует готовый валидный профиль Clash Meta (Mihomo) в формате YAML."""
    proxies = []
    names = []

    for srv in servers:
        parsed = parse_proxy_link(srv["link"])
        if not parsed:
            continue
        clash_item = convert_to_clash_proxy(parsed)
        if clash_item:
            # Устраняем дубликаты имён для Clash
            base_name = clash_item["name"]
            unique_name = base_name
            counter = 1
            while unique_name in names:
                counter += 1
                unique_name = f"{base_name} ({counter})"
            clash_item["name"] = unique_name
            names.append(unique_name)
            proxies.append(clash_item)

    if not proxies:
        return ""

    lines = [
        "# Clash Meta / Mihomo Configuration",
        "# Сгенерировано Happ Subscription Converter Bot",
        "mixed-port: 7890",
        "allow-lan: false",
        "mode: rule",
        "log-level: info",
        "ipv6: false",
        "",
        "dns:",
        "  enable: true",
        "  enhanced-mode: fake-ip",
        "  nameserver:",
        "    - 1.1.1.1",
        "    - 8.8.8.8",
        "",
        "proxies:",
    ]

    for p in proxies:
        lines.append(f"  - name: {json.dumps(p['name'], ensure_ascii=False)}")
        lines.append(f"    type: {p['type']}")
        lines.append(f"    server: {p['server']}")
        lines.append(f"    port: {p['port']}")
        if "uuid" in p:
            lines.append(f"    uuid: {p['uuid']}")
        if "password" in p:
            lines.append(f"    password: {p['password']}")
        if "network" in p:
            lines.append(f"    network: {p['network']}")
        if "flow" in p:
            lines.append(f"    flow: {p['flow']}")
        if p.get("tls"):
            lines.append("    tls: true")
        if "servername" in p:
            lines.append(f"    servername: {p['servername']}")
        if "sni" in p:
            lines.append(f"    sni: {p['sni']}")
        if "client-fingerprint" in p:
            lines.append(f"    client-fingerprint: {p['client-fingerprint']}")
        if "alpn" in p:
            lines.append("    alpn:")
            for a in p["alpn"]:
                lines.append(f"      - {a}")
        if "reality-opts" in p:
            lines.append("    reality-opts:")
            for rk, rv in p["reality-opts"].items():
                lines.append(f"      {rk}: {rv}")
        if "xhttp-opts" in p:
            lines.append("    xhttp-opts:")
            for xk, xv in p["xhttp-opts"].items():
                lines.append(f"      {xk}: {xv}")
        if p.get("udp"):
            lines.append("    udp: true")
        lines.append("")

    lines.append("proxy-groups:")
    lines.append("  - name: PROXY")
    lines.append("    type: select")
    lines.append("    proxies:")
    for n in names:
        lines.append(f"      - {json.dumps(n, ensure_ascii=False)}")
    lines.append("      - DIRECT")
    lines.append("")
    lines.append("rules:")
    lines.append("  - GEOIP,LAN,DIRECT")
    lines.append("  - MATCH,PROXY")

    return "\n".join(lines)


def generate_singbox_json(servers: List[Dict]) -> str:
    """Генерирует готовый валидный профиль Sing-Box (JSON)."""
    outbounds = []
    tags = []

    for srv in servers:
        parsed = parse_proxy_link(srv["link"])
        if not parsed:
            continue
        sb_item = convert_to_singbox_outbound(parsed)
        if sb_item:
            base_tag = sb_item["tag"]
            unique_tag = base_tag
            counter = 1
            while unique_tag in tags:
                counter += 1
                unique_tag = f"{base_tag} ({counter})"
            sb_item["tag"] = unique_tag
            tags.append(unique_tag)
            outbounds.append(sb_item)

    if not outbounds:
        return ""

    selector_group = {
        "type": "selector",
        "tag": "select",
        "outbounds": tags + ["direct"],
    }

    full_outbounds = [selector_group] + outbounds + [
        {"type": "direct", "tag": "direct"},
        {"type": "block", "tag": "block"},
        {"type": "dns", "tag": "dns-out"},
    ]

    config = {
        "log": {
            "level": "info",
        },
        "dns": {
            "servers": [
                {"tag": "dns-remote", "address": "https://1.1.1.1/dns-query", "detour": "select"},
                {"tag": "dns-direct", "address": "https://8.8.8.8/dns-query", "detour": "direct"},
            ]
        },
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080,
            }
        ],
        "outbounds": full_outbounds,
        "route": {
            "auto_detect_interface": True,
            "rules": [
                {"outbound": "dns-out", "protocol": "dns"},
                {"outbound": "direct", "ip_is_private": True},
            ],
        },
    }

    return json.dumps(config, indent=2, ensure_ascii=False)


def outbound_to_link(ob: Dict) -> Optional[str]:
    """Конвертирует один outbound Sing-Box в ссылку vless://, hysteria2://, trojan:// или ss://."""
    if not isinstance(ob, dict):
        return None

    t = ob.get("type", "").lower()
    tag = ob.get("tag", "").strip() or f"{t}_{ob.get('server', 'proxy')}"
    quoted_tag = urllib.parse.quote(tag)

    if t == "vless":
        uuid = ob.get("uuid") or ob.get("password")
        server = ob.get("server") or ob.get("server_address")
        port = ob.get("server_port") or ob.get("port") or 443
        if not uuid or not server:
            return None

        params = {"encryption": ob.get("encryption", "none")}

        if "flow" in ob and ob["flow"]:
            params["flow"] = ob["flow"]

        tr = ob.get("transport") or {}
        if tr and isinstance(tr, dict):
            params["type"] = tr.get("type", "tcp")
            if "path" in tr:
                params["path"] = tr["path"]
            if "host" in tr:
                params["host"] = tr["host"]
            if "mode" in tr:
                params["mode"] = tr["mode"]
        elif "network" in ob:
            params["type"] = ob["network"]

        tls = ob.get("tls") or {}
        if isinstance(tls, dict) and (tls.get("enabled") or "reality" in tls or "server_name" in tls):
            reality = tls.get("reality") or ob.get("reality") or {}
            if reality and (reality.get("enabled") or "public_key" in reality):
                params["security"] = "reality"
                if "public_key" in reality:
                    params["pbk"] = reality["public_key"]
                if "short_id" in reality:
                    params["sid"] = reality["short_id"]
            else:
                params["security"] = "tls"

            sni = tls.get("server_name") or ob.get("server_name")
            if sni:
                params["sni"] = sni

            utls = tls.get("utls") or {}
            if isinstance(utls, dict) and "fingerprint" in utls:
                params["fp"] = utls["fingerprint"]
            elif "fingerprint" in tls:
                params["fp"] = tls["fingerprint"]

            alpn = tls.get("alpn")
            if isinstance(alpn, list):
                params["alpn"] = ",".join(alpn)
            elif isinstance(alpn, str):
                params["alpn"] = alpn

        qs = urllib.parse.urlencode(params)
        return f"vless://{uuid}@{server}:{port}?{qs}#{quoted_tag}"

    elif t == "hysteria2":
        pw = ob.get("password") or ob.get("uuid") or ""
        server = ob.get("server") or ob.get("server_address") or ""
        port = ob.get("server_port") or ob.get("port") or 443
        if not server:
            return None

        tls = ob.get("tls") or {}
        sni = ""
        if isinstance(tls, dict):
            sni = tls.get("server_name", "")
        if not sni:
            sni = ob.get("sni") or server

        return f"hysteria2://{pw}@{server}:{port}/?sni={sni}#{quoted_tag}"

    elif t == "trojan":
        pw = ob.get("password", "")
        server = ob.get("server") or ""
        port = ob.get("server_port") or ob.get("port") or 443
        if not pw or not server:
            return None

        tls = ob.get("tls") or {}
        sni = tls.get("server_name", "") if isinstance(tls, dict) else (ob.get("sni") or server)
        params = {"security": "tls"}
        if sni:
            params["sni"] = sni
        qs = urllib.parse.urlencode(params)
        return f"trojan://{pw}@{server}:{port}?{qs}#{quoted_tag}"

    elif t == "shadowsocks":
        method = ob.get("method", "")
        password = ob.get("password", "")
        server = ob.get("server", "")
        port = ob.get("server_port") or ob.get("port") or 8388
        if not method or not password or not server:
            return None
        import base64
        user_info = base64.b64encode(f"{method}:{password}".encode()).decode()
        return f"ss://{user_info}@{server}:{port}#{quoted_tag}"

    return None


def convert_singbox_json_to_links(data) -> List[Dict[str, str]]:
    """Принимает Sing-Box конфиг (dict, list или JSON-строку) и возвращает список ссылок с тегами."""
    if isinstance(data, str):
        data = json.loads(data)

    outbounds = []
    if isinstance(data, dict):
        if "outbounds" in data and isinstance(data["outbounds"], list):
            outbounds = data["outbounds"]
        elif "type" in data:
            outbounds = [data]
    elif isinstance(data, list):
        outbounds = data

    results = []
    for ob in outbounds:
        if not isinstance(ob, dict):
            continue
        ob_type = ob.get("type", "").lower()
        if ob_type in ("direct", "block", "dns", "selector", "urltest"):
            continue

        link = outbound_to_link(ob)
        if link:
            tag = ob.get("tag", "").strip() or f"{ob_type}_{ob.get('server', 'server')}"
            results.append({
                "tag": tag,
                "proto": ob_type,
                "link": link,
            })

    return results


