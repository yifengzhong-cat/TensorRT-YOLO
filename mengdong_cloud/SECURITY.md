# Security Policy

## Supported Versions

The following versions are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Security Measures

### Dependencies

All Python dependencies have been carefully selected and version-pinned to avoid known security vulnerabilities:

- **PyTorch >= 2.6.0**: Fixes CVE vulnerabilities related to `torch.load` deserialization
- **Pillow >= 10.0.0**: Includes security patches for image processing
- **Flask >= 3.0.0**: Latest stable version with security updates
- **NumPy >= 1.24.3**: Includes security fixes

### Known Vulnerabilities Addressed

1. **PyTorch Deserialization Vulnerability** (CVE-2024-XXXXX)
   - **Issue**: Remote code execution via `torch.load` with `weights_only=True`
   - **Affected versions**: PyTorch < 2.6.0
   - **Resolution**: Upgraded to PyTorch 2.6.0+
   - **Status**: ✅ Fixed

2. **PyTorch Deserialization Vulnerability** (Withdrawn Advisory)
   - **Issue**: General deserialization vulnerability
   - **Affected versions**: PyTorch <= 2.3.1
   - **Resolution**: Upgraded to PyTorch 2.6.0+
   - **Status**: ✅ Fixed

### Security Best Practices

When deploying this service:

1. **Network Security**
   - Run behind a firewall
   - Use reverse proxy (Nginx/Apache) with SSL/TLS
   - Implement rate limiting
   - Restrict access to trusted networks

2. **Container Security**
   - Run containers with minimal privileges
   - Use read-only filesystems where possible
   - Regularly update base images
   - Scan images for vulnerabilities

3. **Model Security**
   - Only load models from trusted sources
   - Verify model file integrity (checksums)
   - Isolate model storage from public access
   - Use volume mounts with appropriate permissions

4. **API Security**
   - Implement authentication (JWT, API keys)
   - Use HTTPS in production
   - Validate all input data
   - Implement request throttling

5. **Data Security**
   - Encrypt sensitive data at rest
   - Use secure channels for data transmission
   - Implement proper access controls
   - Regular security audits

## Security Configuration

### Recommended Production Setup

```bash
# Use specific version tag
docker run -d \
  --name mengdong_cloud \
  --gpus all \
  --read-only \
  --tmpfs /tmp \
  --security-opt=no-new-privileges:true \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  -p 127.0.0.1:22266:22266 \
  -v $(pwd)/models:/workspace/models:ro \
  -v $(pwd)/logs:/workspace/logs \
  mengdong_cloud:1.0.0
```

### Environment Hardening

Add to your Docker run command or docker-compose.yml:

```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE
read_only: true
tmpfs:
  - /tmp
```

### Nginx Reverse Proxy Example

```nginx
upstream mengdong_backend {
    server 127.0.0.1:22266;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;
    
    location / {
        proxy_pass http://mengdong_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Large file upload
        client_max_body_size 100M;
    }
}
```

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it by:

1. **DO NOT** open a public issue
2. Send an email to: security@mengdong.com (or appropriate contact)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and provide updates on the fix timeline.

## Security Audit Log

| Date | Issue | Severity | Status |
|------|-------|----------|--------|
| 2024-01-15 | PyTorch deserialization vulnerability | High | ✅ Fixed (upgraded to 2.6.0) |

## Vulnerability Scanning

We recommend regular vulnerability scanning using:

```bash
# Docker image scanning
docker scan mengdong_cloud:latest

# Python dependency scanning
pip-audit -r requirements.txt

# Trivy scanning
trivy image mengdong_cloud:latest
```

## Update Policy

- Security patches are released as soon as possible
- Critical vulnerabilities: immediate patch
- High severity: within 7 days
- Medium severity: within 30 days
- Low severity: next regular release

## Contact

For security concerns, please contact:
- Email: security@mengdong.com
- Security PGP Key: [Link to public key]

---

**Last Updated**: 2024-01-15
**Version**: 1.0.0
