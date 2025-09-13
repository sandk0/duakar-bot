# REALITY Protocol Configuration Guide

## Overview
REALITY is an advanced obfuscation protocol for VLESS that helps bypass deep packet inspection (DPI) and network restrictions, particularly effective against mobile carrier blocking.

## Key Parameters for Bypassing Mobile Internet Blocks

### 1. Server Name Indication (SNI) - `serverNames`
The most critical parameter for bypassing blocks. Must contain domains that:
- Are popular and unlikely to be blocked by carriers
- Have high traffic volume (VK, YouTube, etc.)
- Are CDN endpoints that serve legitimate content

### 2. Destination (`dest`)
Should match one of the SNI domains and include port:
```json
"dest": "sun6-21.userapi.com:443"
```

### 3. Short IDs (`shortIds`)
Multiple short IDs provide flexibility:
```json
"shortIds": [
  "b03c9fcdbe2cee58",
  "ffffffffff",
  "ffffffffffff",
  "ffffffffffffffff"
]
```

## Configuration Examples

### Basic Configuration (Universal)
Located in: `configs/marzban_host_reality.json`
- Uses common VK domains
- Suitable for most carriers

### Megafon/MTS Optimized Configuration
Located in: `configs/marzban_host_reality_megafon.json`
- Extended list of userapi.com subdomains
- Specifically tested against Megafon and MTS blocking
- Includes multiple sun*.userapi.com variants

## Implementation in Marzban

1. **Update host configuration** in Marzban admin panel:
   - Navigate to Hosts settings
   - Select or create a new host
   - Replace the inbound configuration with one of the provided configs

2. **Client-side parameters** to include:
   - `sni`: One of the domains from serverNames list
   - `fp`: Fingerprint (chrome, firefox, safari, etc.)
   - `pbk`: Public key from the server
   - `sid`: One of the short IDs
   - `spx`: SpiderX path (usually "/")

## Testing Methodology

To verify bypass effectiveness:

1. **Test with different carriers**:
   - Megafon
   - MTS
   - Beeline
   - Tele2

2. **Test in different network conditions**:
   - Mobile data (4G/5G)
   - Public WiFi with restrictions
   - Corporate networks

3. **Monitor connection stability**:
   - Connection establishment time
   - Throughput consistency
   - Reconnection success rate

## Troubleshooting

### If connections are still blocked:

1. **Rotate SNI domains**:
   - Try different userapi.com subdomains
   - Use other popular services (YouTube, CloudFlare, etc.)

2. **Adjust fingerprints**:
   - Chrome is most common
   - Firefox for alternative
   - Safari for iOS devices

3. **Change ports**:
   - 443 (HTTPS standard)
   - 8443 (Alternative HTTPS)
   - 2053, 2083, 2087, 2096 (CloudFlare ports)

## Security Considerations

- Keep private keys secure and rotate periodically
- Monitor for unusual traffic patterns
- Use unique short IDs per deployment
- Regularly update SNI lists based on carrier blocking patterns

## Updates and Maintenance

This configuration should be reviewed and updated:
- When carriers update their blocking rules
- When new popular domains become available
- Based on user feedback about connection issues

Last updated: 2025-01-13