#! /bin/sh

set -e

INDEX_FILE=/usr/share/nginx/html/index.html
export SPECS_URI=${URL:-/specs/openapi.yml}

if [ ! -f /usr/share/nginx/html/editor.html ]; then

  mv /usr/share/nginx/html/index.html /usr/share/nginx/html/editor.html
  cat <<EOF > /usr/share/nginx/html/index.html
  <!DOCTYPE html>
  <html>
    <head><meta http-equiv = "refresh" content = "0; url=/editor.html?url=${SPECS_URI}" /></head>
    <body></body>
  </html>
EOF

fi

exec nginx -g 'daemon off;'

