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

export STICKY_PI_TESTING_USER="wei"
export STICKY_PI_TESTING_PASSWORD="cbsfbyuekiw678sdhw"
#realpath /home/mxie/StickyPi/api_login.env
#source /home/mxie/StickyPi/api_login.env
#echo "$user"
#export STICKY_PI_TESTING_USER=$user
#echo "$pass"
#export STICKY_PI_TESTING_PASSWORD=$pass

export STICKY_PI_TESTING_RSHINY_AUTOLOGIN=TRUE
export STICKY_PI_TESTING_RSHINY_USE_MOCK_API=FALSE
# manually set time zone, only for Windows Subsystem for Linux because no real systemd --> can't run timedatectl
export TZ="America/Vancouver"
R -e "shiny::runApp('sticky_pi_app', port=4434)"
