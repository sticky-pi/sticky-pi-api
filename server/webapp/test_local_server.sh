#!/bin/bash

export STICKY_PI_TESTING_RSHINY_BYPASS_LOGGIN=FALSE

export API_ROOT_URL=api.sticky-pi.com
export API_PROTOCOL=https
export API_PORT=443

export RSHINY_UPSTREAM_ROOT_URL=api.sticky-pi.com
export RSHINY_UPSTREAM_PORT=443
export RSHINY_UPSTREAM_PROTOCOL=https

#defined elsewhere
#export STICKY_PI_TESTING_USER=admin
#export STICKY_PI_TESTING_PASSWORD=**************
#source /tmp/.spi_webapp.secret.env

#export STICKY_PI_TESTING_USER="wei"
#export STICKY_PI_TESTING_PASSWORD="cbsfbyuekiw678sdhw"
source /home/mxie/StickyPi/api_login.env
echo "$STICKY_PI_TESTING_USER"
echo "$STICKY_PI_TESTING_PASSWORD"

export STICKY_PI_TESTING_RSHINY_AUTOLOGIN=TRUE
export STICKY_PI_TESTING_RSHINY_USE_MOCK_API=TRUE
# manually set time zone, only for Windows Subsystem for Linux because no real systemd --> can't run timedatectl
export TZ="America/Vancouver"
R -e "shiny::runApp('sticky_pi_app', port=4434, display.mode='showcase')"
#
