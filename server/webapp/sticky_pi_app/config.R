CONFIG_ENV_FILE <- '/home/shiny/env.R'

# The default config . typically for testing offline with rstudio (no api)
# these are overwritten with environement variables in API testing and production
config_vars <- list(
                 STICKY_PI_TESTING_USER = NA,
                 STICKY_PI_TESTING_PASSWORD = NA, 
                 STICKY_PI_TESTING_RSHINY_AUTOLOGIN = FALSE,
                 STICKY_PI_TESTING_RSHINY_BYPASS_LOGGIN = FALSE,
                 STICKY_PI_TESTING_RSHINY_USE_MOCK_API = FALSE,
                 RSHINY_UPSTREAM_ROOT_URL = NA, #hostname, IP, domain name...
                 RSHINY_UPSTREAM_PORT = NA, #hostname, IP, domain name...
                 RSHINY_UPSTREAM_PROTOCOL = "http"
)

get_config<- function(){
    out <- config_vars
    #populate with accessible vars from sys
    sys_vars <- Sys.getenv(names(config_vars))
    
    sys_vars <- sys_vars[sys_vars != ""]
    out[names(sys_vars)] <- sys_vars
    
    #overwide from config file, if available (docker only)
    if(file.exists(CONFIG_ENV_FILE)){
      source(CONFIG_ENV_FILE)
      for(v in names(out)){
        try({
        out[[v]] <- get(v)
      }, silent=TRUE)
      }
    }
    out
}