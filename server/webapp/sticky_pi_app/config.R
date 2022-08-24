CONFIG_ENV_FILE <- '/home/shiny/env.R'


DATETIME_FORMAT <- '%Y-%m-%dT%H:%M:%SZ'

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
                 RSHINY_UPSTREAM_PROTOCOL = "http",
                 # map of column headers in real data to rendered user-facing webapp tables
                 PROJECTS_LIST_HEADERS = list(
                     name = "Name",
                     description = "Description",
                     notes = "Notes"
                 ),
                 PERMISSIONS_TABLE_HEADERS = list(
                     username = "Username",
                     level = "Role"
                 ),
                 PERMISSION_LEVELS_TO_ROLES = data.table(
                                level = 1:3,
                                role = c(
                                         "Viewer",
                                         "Editor",
                                         "Admin"
                                         )
                 ),
                 PROJECT_SERIES_HEADERS = list(
                     device = "Device ID",
                     start_datetime = "Start",
                     end_datetime = "End",
                     .COMP_N_MATCHES = "N_images"
                 ),
                 DATETIME_COLS_HEADERS = c(
                     "start_datetime",
                     "end_datetime"
                 )
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
