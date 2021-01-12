export API_ROOT_URL=api.sticky-pi.com
export API_PROTOCOL=https
export STICKY_PI_TESTING_RSHINY_BYPASS_LOGGIN=FALSE
export STICKY_PI_TESTING_USER=admin

#defined elsewhere
#export STICKY_PI_TESTING_PASSWORD=**************
source /tmp/.spi_webapp.secret.env

export STICKY_PI_TESTING_RSHINY_AUTOLOGIN=TRUE
export STICKY_PI_TESTING_RSHINY_USE_MOCK_API=FALSE
R -e "shiny::runApp('sticky_pi_app', port=4434)"
