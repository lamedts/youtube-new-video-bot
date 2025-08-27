# OAuth Setup Guide

This guide covers different OAuth setup strategies for various deployment scenarios.

## Table of Contents

1. [Local Development (Default)](#local-development)
2. [Server with Custom Domain](#server-with-domain)
3. [SSL/HTTPS Setup](#ssl-setup)
4. [Google Cloud Console Setup](#google-console-setup)
5. [Troubleshooting](#troubleshooting)

## Local Development (Default)

For local development, no additional configuration is needed. The bot will use localhost callback URLs.

```bash
# Default configuration (no domain setup needed)
OAUTH_PORT_START=8080
OAUTH_TIMEOUT=300
OAUTH_AUTO_BROWSER=true
```

**How it works:**
- OAuth server runs on `http://localhost:8080/oauth2callback`
- Browser opens automatically for authorization
- Works great for development and testing

---

## Server with Custom Domain

For headless servers or production deployments, you can use your own domain for OAuth callbacks.

### Prerequisites

1. **Domain pointed to your server IP**
2. **Firewall configured** to allow access to OAuth port
3. **Google Console configured** with domain callback URL

### Configuration

Update your `.env` file:

```bash
# Basic domain setup (HTTP)
OAUTH_CALLBACK_DOMAIN=yourdomain.com
OAUTH_PORT_START=8080
OAUTH_USE_SSL=false
OAUTH_AUTO_BROWSER=false  # Usually false for servers
```

### How It Works

1. **Server starts OAuth server on**: `0.0.0.0:8080`
2. **Callback URL becomes**: `http://yourdomain.com:8080/oauth2callback` 
3. **User can authorize from anywhere**: Just visit the auth URL
4. **Google redirects to your domain**: Server receives the callback

### Firewall Configuration

**Ubuntu/Debian:**
```bash
sudo ufw allow 8080/tcp
```

**CentOS/RHEL:**
```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

**Cloud Providers:**
- **AWS**: Add inbound rule for port 8080 in Security Groups
- **GCP**: `gcloud compute firewall-rules create allow-oauth --allow tcp:8080`
- **Azure**: Add inbound port rule in Network Security Group

---

## SSL/HTTPS Setup

For production deployments, Google requires HTTPS for OAuth callbacks.

### Option 1: Direct SSL (Recommended for simple setups)

```bash
# HTTPS with SSL certificates
OAUTH_CALLBACK_DOMAIN=yourdomain.com
OAUTH_USE_SSL=true
OAUTH_SSL_CERT_PATH=/etc/ssl/certs/yourdomain.pem
OAUTH_SSL_KEY_PATH=/etc/ssl/private/yourdomain.key
OAUTH_PORT_START=8080
```

**Generate SSL Certificate with Let's Encrypt:**
```bash
# Install certbot
sudo apt update
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# Certificates will be in:
# Cert: /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# Key:  /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

### Option 2: Reverse Proxy (Recommended for production)

Use nginx/apache to handle SSL termination and proxy to the bot.

**Nginx Configuration (`/etc/nginx/sites-available/youtube-bot`):**
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location /oauth2callback {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Bot Configuration for Reverse Proxy:**
```bash
OAUTH_CALLBACK_DOMAIN=yourdomain.com
OAUTH_USE_SSL=false  # nginx handles SSL
OAUTH_PORT_START=8080  # Internal port
```

**Google Console Callback URL:**
```
https://yourdomain.com/oauth2callback
```

---

## Google Cloud Console Setup

### 1. Enable YouTube Data API v3

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project or create a new one
3. Navigate to **APIs & Services > Library**
4. Search for "YouTube Data API v3" and enable it

### 2. Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth 2.0 Client IDs**
3. Choose **Web application**
4. Add your callback URLs to **Authorized redirect URIs**

### 3. Callback URL Examples

**Localhost (Development):**
```
http://localhost:8080/oauth2callback
http://localhost:8081/oauth2callback
http://localhost:8082/oauth2callback
```

**Custom Domain (Production):**
```
https://yourdomain.com:8080/oauth2callback
https://yourdomain.com/oauth2callback  (if using reverse proxy)
```

**Important Notes:**
- URLs must be **exact matches** (including port numbers)
- HTTPS is **required** for production domains
- You can add multiple callback URLs for different environments

### 4. Download Credentials

1. Click the download icon next to your OAuth 2.0 Client ID
2. Save as `youtube-client-secret.json` in your project root
3. Keep this file secure and never commit it to version control

---

## Deployment Examples

### Example 1: Simple VPS with Domain

```bash
# .env configuration
OAUTH_CALLBACK_DOMAIN=bot.yourdomain.com
OAUTH_USE_SSL=true
OAUTH_SSL_CERT_PATH=/etc/letsencrypt/live/bot.yourdomain.com/fullchain.pem
OAUTH_SSL_KEY_PATH=/etc/letsencrypt/live/bot.yourdomain.com/privkey.pem
OAUTH_PORT_START=8080
OAUTH_AUTO_BROWSER=false
```

**Steps:**
1. Point `bot.yourdomain.com` to your server IP
2. Generate SSL certificate with Let's Encrypt
3. Open port 8080 in firewall
4. Add `https://bot.yourdomain.com:8080/oauth2callback` to Google Console
5. Run the bot - OAuth will work from any browser

### Example 2: Behind Load Balancer

```bash
# .env configuration  
OAUTH_CALLBACK_DOMAIN=yourdomain.com
OAUTH_USE_SSL=false  # Load balancer handles SSL
OAUTH_PORT_START=8080
OAUTH_AUTO_BROWSER=false
```

**Steps:**
1. Configure load balancer to forward `/oauth2callback` to bot server
2. Load balancer handles SSL termination
3. Add `https://yourdomain.com/oauth2callback` to Google Console
4. Bot runs on internal HTTP port

### Example 3: Docker with Traefik

```yaml
# docker-compose.yml
version: '3.8'
services:
  youtube-bot:
    build: .
    environment:
      - OAUTH_CALLBACK_DOMAIN=bot.yourdomain.com
      - OAUTH_USE_SSL=false  # Traefik handles SSL
      - OAUTH_PORT_START=8080
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.youtube-bot.rule=Host(`bot.yourdomain.com`) && Path(`/oauth2callback`)"
      - "traefik.http.routers.youtube-bot.tls.certresolver=letsencrypt"
    networks:
      - traefik

networks:
  traefik:
    external: true
```

---

## Troubleshooting

### Common Issues

**1. "redirect_uri_mismatch" Error**
- **Cause**: Callback URL doesn't match Google Console configuration
- **Solution**: Ensure exact URL match in Google Console (including protocol, domain, port, path)

**2. "SSL: CERTIFICATE_VERIFY_FAILED"**
- **Cause**: Invalid or expired SSL certificate
- **Solution**: Renew SSL certificate or check certificate paths

**3. "Connection refused" on callback**
- **Cause**: Firewall blocking port or server not binding to 0.0.0.0
- **Solution**: Open firewall port and ensure `OAUTH_CALLBACK_DOMAIN` is set

**4. Browser doesn't open automatically**
- **Cause**: Server environment doesn't support browser opening
- **Solution**: Set `OAUTH_AUTO_BROWSER=false` and visit URL manually

**5. "Permission denied" for SSL certificate files**
- **Cause**: Bot doesn't have read permissions for certificate files
- **Solution**: `sudo chown bot-user:bot-user /etc/ssl/certs/cert.pem` or copy to accessible location

### Debug Mode

Enable verbose OAuth logging:

```bash
# Add to your .env for debugging
OAUTH_DEBUG=true
```

This will show:
- Server binding details
- Callback URL construction
- SSL certificate loading
- Request details

### Testing Your Setup

**1. Test OAuth Server Manually:**
```bash
# Test if port is accessible
curl http://yourdomain.com:8080/health

# Or with HTTPS
curl https://yourdomain.com:8080/health
```

**2. Test Full OAuth Flow:**
```bash
# Remove existing token to force new OAuth
rm youtube-token.json

# Run bot - it will show the authorization URL
python main.py
```

**3. Verify Google Console Setup:**
- Visit your authorization URL
- Check that redirect goes to your domain
- Confirm authorization code is received

---

## Security Best Practices

1. **Always use HTTPS in production**
2. **Keep SSL certificates up to date**
3. **Restrict firewall rules to necessary ports**
4. **Store certificates securely with proper permissions**
5. **Never commit client secrets to version control**
6. **Use environment variables for sensitive configuration**
7. **Consider using a reverse proxy for SSL termination**
8. **Monitor certificate expiry dates**

---

## Quick Setup Checklist

### For Domain-based OAuth:

- [ ] Domain points to server IP
- [ ] Firewall allows OAuth port (default 8080)
- [ ] SSL certificate installed (for HTTPS)
- [ ] Google Console configured with callback URL
- [ ] Environment variables configured
- [ ] Bot has permissions to read SSL certificates
- [ ] Test OAuth flow works end-to-end

### Example Final Configuration:

```bash
# Production setup
OAUTH_CALLBACK_DOMAIN=yourdomain.com
OAUTH_USE_SSL=true
OAUTH_SSL_CERT_PATH=/etc/ssl/certs/yourdomain.pem
OAUTH_SSL_KEY_PATH=/etc/ssl/private/yourdomain.key
OAUTH_PORT_START=8080
OAUTH_TIMEOUT=300
OAUTH_AUTO_BROWSER=false
```

**Google Console Callback URL:**
```
https://yourdomain.com:8080/oauth2callback
```

This setup enables seamless OAuth from any browser, anywhere in the world! 🎉