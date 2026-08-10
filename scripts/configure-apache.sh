#!/usr/bin/env bash
# Point fingers.ads-ai.in Apache vhosts at local Next/API without touching other sites.
set -euo pipefail

cat > /etc/apache2/sites-available/fingers.ads-ai.in.conf <<'CONF'
<VirtualHost *:80>
    ServerName fingers.ads-ai.in

    ProxyPreserveHost On
    ProxyPass /api http://127.0.0.1:8095/api
    ProxyPassReverse /api http://127.0.0.1:8095/api
    ProxyPass / http://127.0.0.1:3090/
    ProxyPassReverse / http://127.0.0.1:3090/

    ErrorLog ${APACHE_LOG_DIR}/fingers.ads-ai.in-error.log
    CustomLog ${APACHE_LOG_DIR}/fingers.ads-ai.in-access.log combined

    RewriteEngine on
    RewriteCond %{SERVER_NAME} =fingers.ads-ai.in
    RewriteRule ^ https://%{SERVER_NAME}%{REQUEST_URI} [END,NE,R=permanent]
</VirtualHost>
CONF

# Preserve existing Let's Encrypt cert paths if SSL vhost already exists
if [[ -f /etc/apache2/sites-available/fingers.ads-ai.in-le-ssl.conf ]]; then
  cat > /etc/apache2/sites-available/fingers.ads-ai.in-le-ssl.conf <<'CONF'
<IfModule mod_ssl.c>
<VirtualHost *:443>
    ServerName fingers.ads-ai.in

    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    ProxyPass /api http://127.0.0.1:8095/api
    ProxyPassReverse /api http://127.0.0.1:8095/api
    ProxyPass / http://127.0.0.1:3090/
    ProxyPassReverse / http://127.0.0.1:3090/

    ErrorLog ${APACHE_LOG_DIR}/fingers.ads-ai.in-error.log
    CustomLog ${APACHE_LOG_DIR}/fingers.ads-ai.in-access.log combined

    SSLCertificateFile /etc/letsencrypt/live/fingers.ads-ai.in/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/fingers.ads-ai.in/privkey.pem
    Include /etc/letsencrypt/options-ssl-apache.conf
</VirtualHost>
</IfModule>
CONF
fi

a2enmod proxy proxy_http headers rewrite ssl >/dev/null
a2ensite fingers.ads-ai.in.conf >/dev/null
a2ensite fingers.ads-ai.in-le-ssl.conf >/dev/null || true
apache2ctl configtest
systemctl reload apache2
echo "Apache fingers reverse proxy configured"
