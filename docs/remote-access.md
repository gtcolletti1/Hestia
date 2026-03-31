# Remote Access Setup

This guide covers how to access your Family Hub securely from outside your home network.

---

## Option 1: Tailscale (Recommended)

[Tailscale](https://tailscale.com/) creates a private WireGuard mesh network with zero configuration.

1. **Install Tailscale** on the Family Hub host:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
2. **Install Tailscale** on your phone/laptop.
3. **Access the hub** via the Tailscale IP shown in `tailscale status`, e.g.:
   ```
   http://100.x.y.z
   ```
4. (Optional) Enable [MagicDNS](https://tailscale.com/kb/1081/magicdns/) to access via hostname:
   ```
   http://family-hub
   ```

**Pros:** No port forwarding, automatic key rotation, works behind CGNAT.

---

## Option 2: Cloudflare Tunnel

[Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) exposes your hub through Cloudflare's edge network without opening ports.

1. **Install cloudflared:**
   ```bash
   # macOS
   brew install cloudflared

   # Debian/Ubuntu
   curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg
   echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
   sudo apt update && sudo apt install cloudflared
   ```
2. **Authenticate and create a tunnel:**
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create family-hub
   ```
3. **Configure the tunnel** (`~/.cloudflared/config.yml`):
   ```yaml
   tunnel: family-hub
   credentials-file: ~/.cloudflared/<TUNNEL_ID>.json

   ingress:
     - hostname: hub.yourdomain.com
       service: http://localhost:80
     - service: http_status:404
   ```
4. **Route DNS and start:**
   ```bash
   cloudflared tunnel route dns family-hub hub.yourdomain.com
   cloudflared tunnel run family-hub
   ```

**Pros:** Free, automatic HTTPS, DDoS protection.

---

## Option 3: Manual Reverse Proxy (nginx + Let's Encrypt)

Use this if you have a static IP or dynamic DNS and want full control.

1. **Port-forward** port 80 and 443 on your router to the hub host.
2. **Install nginx and Certbot:**
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   ```
3. **Create an nginx site** (`/etc/nginx/sites-available/family-hub`):
   ```nginx
   server {
       listen 80;
       server_name hub.yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
4. **Enable the site and obtain a certificate:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/family-hub /etc/nginx/sites-enabled/
   sudo certbot --nginx -d hub.yourdomain.com
   sudo systemctl reload nginx
   ```

**Pros:** Full control, widely documented.
**Cons:** Requires port forwarding, certificate renewal management.

---

## Security Recommendations

- **Always use HTTPS** — all three options above provide or support TLS encryption.
- **Enable authentication** — the Family Hub PIN-based auth prevents unauthorized access, but consider adding HTTP Basic Auth or Cloudflare Access as an additional layer.
- **Limit network access** — with Tailscale, only devices on your tailnet can connect. With Cloudflare, use Access policies. With nginx, use `allow`/`deny` directives or fail2ban.
- **Keep software updated** — regularly update the hub, OS packages, and tunnel software.
- **Use strong PINs** — avoid simple PINs like `0000` or `1234`.
- **Monitor access logs** — review nginx or Cloudflare analytics for unexpected traffic.
