import qrcode
from io import BytesIO
from typing import Optional
import base64
import json
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)


def generate_unique_username(telegram_id: int) -> str:
    """Generate unique username for Marzban based on Telegram ID"""
    import time
    timestamp = int(time.time())
    return f"tg_{telegram_id}_{timestamp}"


def format_traffic(bytes_value: int) -> str:
    """Format traffic bytes to human readable format"""
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.2f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"


def parse_vless_url(vless_url: str) -> Optional[dict]:
    """Parse VLESS URL to extract configuration details"""
    try:
        parsed = urlparse(vless_url)
        if parsed.scheme != "vless":
            return None
        
        # Extract UUID (user part)
        uuid = parsed.username
        
        # Extract server and port
        server = parsed.hostname
        port = parsed.port
        
        # Extract parameters
        params = parse_qs(parsed.query)
        
        # Extract fragment (remarks/name)
        remarks = parsed.fragment
        
        config = {
            "uuid": uuid,
            "server": server,
            "port": port,
            "remarks": remarks,
            "params": {k: v[0] if len(v) == 1 else v for k, v in params.items()}
        }
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to parse VLESS URL: {str(e)}")
        return None


def generate_config_qr(config_url: str) -> BytesIO:
    """Generate QR code for VPN configuration"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        qr.add_data(config_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        return bio
        
    except Exception as e:
        logger.error(f"Failed to generate QR code: {str(e)}")
        raise


def create_clash_config(vless_url: str, server_name: str = "VPN Server") -> str:
    """Create Clash configuration from VLESS URL"""
    config = parse_vless_url(vless_url)
    if not config:
        return ""
    
    clash_config = {
        "proxies": [
            {
                "name": server_name,
                "type": "vless",
                "server": config["server"],
                "port": config["port"],
                "uuid": config["uuid"],
                "cipher": "auto",
                "tls": config["params"].get("security", "tls") == "tls",
                "skip-cert-verify": False,
                "network": config["params"].get("type", "tcp")
            }
        ],
        "proxy-groups": [
            {
                "name": "Proxy",
                "type": "select",
                "proxies": [server_name, "DIRECT"]
            }
        ],
        "rules": [
            "MATCH,Proxy"
        ]
    }
    
    # Add additional parameters based on network type
    proxy = clash_config["proxies"][0]
    
    if proxy["network"] == "ws":
        proxy["ws-opts"] = {
            "path": config["params"].get("path", "/"),
            "headers": {"Host": config["params"].get("host", config["server"])}
        }
    elif proxy["network"] == "grpc":
        proxy["grpc-opts"] = {
            "grpc-service-name": config["params"].get("serviceName", "")
        }
    
    return json.dumps(clash_config, indent=2)


def create_v2ray_config(vless_url: str) -> str:
    """Create V2Ray configuration from VLESS URL"""
    config = parse_vless_url(vless_url)
    if not config:
        return ""
    
    v2ray_config = {
        "log": {
            "loglevel": "warning"
        },
        "inbounds": [
            {
                "port": 10808,
                "protocol": "socks",
                "settings": {
                    "auth": "noauth",
                    "udp": True
                }
            }
        ],
        "outbounds": [
            {
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": config["server"],
                            "port": config["port"],
                            "users": [
                                {
                                    "id": config["uuid"],
                                    "encryption": "none",
                                    "flow": config["params"].get("flow", "")
                                }
                            ]
                        }
                    ]
                },
                "streamSettings": {
                    "network": config["params"].get("type", "tcp"),
                    "security": config["params"].get("security", "tls")
                }
            }
        ]
    }
    
    # Add TLS settings if needed
    if v2ray_config["outbounds"][0]["streamSettings"]["security"] == "tls":
        v2ray_config["outbounds"][0]["streamSettings"]["tlsSettings"] = {
            "serverName": config["params"].get("sni", config["server"]),
            "allowInsecure": False
        }
    
    # Add network-specific settings
    network = v2ray_config["outbounds"][0]["streamSettings"]["network"]
    
    if network == "ws":
        v2ray_config["outbounds"][0]["streamSettings"]["wsSettings"] = {
            "path": config["params"].get("path", "/"),
            "headers": {"Host": config["params"].get("host", config["server"])}
        }
    elif network == "grpc":
        v2ray_config["outbounds"][0]["streamSettings"]["grpcSettings"] = {
            "serviceName": config["params"].get("serviceName", "")
        }
    elif network == "tcp" and config["params"].get("headerType") == "http":
        v2ray_config["outbounds"][0]["streamSettings"]["tcpSettings"] = {
            "header": {
                "type": "http",
                "request": {
                    "path": [config["params"].get("path", "/")],
                    "headers": {"Host": [config["params"].get("host", config["server"])]}
                }
            }
        }
    
    return json.dumps(v2ray_config, indent=2)


def encode_base64_config(config_str: str) -> str:
    """Encode configuration to base64 for sharing"""
    return base64.b64encode(config_str.encode()).decode()


def decode_base64_config(encoded_str: str) -> str:
    """Decode base64 configuration"""
    try:
        return base64.b64decode(encoded_str).decode()
    except Exception as e:
        logger.error(f"Failed to decode base64 config: {str(e)}")
        return ""