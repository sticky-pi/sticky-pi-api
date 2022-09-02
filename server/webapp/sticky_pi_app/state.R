
make_state <- function(input, config){
  rv <- reactiveValues
  state <- list(
    config = do.call(rv,config),
    data_scope=rv(selected_image_ids = numeric(0), 
                  selected_experiment=0,
                  selected_detector='universal-insect-detector',
                  selected_experiment_persist=0,
                  selected_dates=c(as.POSIXct(today()- 28), as.POSIXct(today())),
                  scope_test=1),
    user = rv(is_logged_in=FALSE,
              username="",
              user_id="",
              role="user",
              auth_token="",
              selected_timezone="UTC"),
    updaters = rv(api_fetch_time=Sys.time() # so we can force update on api requests
    ),
    "_computed_props_" = reactiveValues(),
    "_input_" = input
  )
  
  
}
