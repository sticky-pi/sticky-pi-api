
mock_fetch <- function(image_id, url_base, dpi=200){
  api_entry = sprintf("%s/%i", url_base, image_id)
  if(url_base=='download_s3_thumbnail'){
    size = c(512, 384)
    suffix='jpg.thumbnail'
    # Sys.sleep(0.5)
  }
  else if(url_base=='download_s3_thumbnail_mini'){
    size = c(128, 96)  
    suffix='jpg.thumbnail-mini'
    # Sys.sleep(0.05)
  }
  else  if(url_base=='download_s3'){
     size = c(2592, 1944)
     # Sys.sleep(3)
     suffix='jpg'
  }
  else{
    stop( paste('Wrong api entry', url_base))
  }
  
  now_cs <- round(100 *seconds(Sys.time()))
  url <- sprintf("mock-image.%s_%i_%0.f", suffix,image_id,now_cs)
  g <- textGrob(sprintf('id=%s\napi_entry=%s\nurl=%s', 
                        image_id, 
                        api_entry,
                        url))
  # add a suffix like ?UNIX_TIME to avoid caching by the browser
  dir.create("./www/tmp", showWarnings = FALSE)
  save_location = sprintf("./www/tmp/%s", url)
  old_files <-  list.files('./www/tmp/', pattern=sprintf('mock-image\\.%s.*', suffix),full.names = TRUE)
  sapply(old_files, function(name){
    t <- as.numeric(strsplit(name, '_')[[1]][3])
    if((now_cs - t) > 60*100) # delete files older than 1min
      unlink(name)
  })
    
  
  ggsave(save_location,
         g,
         device = 'jpeg',
         width= size[1]/dpi,
         height= size[2]/dpi, 
         dpi=dpi)
  
  data.table(url=sprintf("tmp/%s",url))
    
}

api_fetch_download_s3_ <- function(state, image_id, url_base){
  if(!isTruthy(image_id))
    return()
  url = unlist(mock_fetch(image_id, url_base))
}

api_fetch_download_s3 <- function(state, image_id, url_base = "download_s3"){
  api_fetch_download_s3_(state, image_id, url_base)
}

api_fetch_download_s3_thumbnail <- function(state, image_id, url_base = "download_s3_thumbnail"){
  api_fetch_download_s3_(state, image_id, url_base)
}

api_fetch_download_s3_thumbnail_mini <- function(state, image_id, url_base = "download_s3_thumbnail_mini"){
  api_fetch_download_s3_(state, image_id, url_base)
}

#api_alter_experiment_list_table <- function(state, action,  api_root="set_experiment_list", data=list()){
#    req(data$name)
#    if(action == "add_row"){
#        list()
#
#    exp_id = MOCK_EXPERIMENT_TABLE[, max(EXPERIMENT_ID)] +1
#    MOCK_EXPERIMENT_ENTRIES[[exp_id]] <<- new_experiment()
#    warning(sprintf('creating experiment id %i', exp_id))
#
#
#    row <- data.table(EXPERIMENT_ID=exp_id ,
#                        USER_ID=CURRENT_USER_ID,
#                        NAME=data$name,
#                        TIME_CREATED= format(Sys.time()),
#                        NOTES="",
#                        CAN_ADMIN=1,
#                        CAN_WRITE=1,
#                        CAN_READ=1)
#
## warning(paste(colnames(row)))
## warning(paste(colnames(MOCK_EXPERIMENT_TABLE)))
#      MOCK_EXPERIMENT_TABLE <<- rbind(MOCK_EXPERIMENT_TABLE, row)
#  }
#
#  else{
#    stop("Action not implemented")
#  }
#
#}
#
#api_alter_experiment_table <- function(state, action, experiment_id,  api_root="set_experiment", data=list()){
#  if(MOCK_EXPERIMENT_TABLE[EXPERIMENT_ID != experiment_id, CAN_WRITE]){
#    warning(sprintf("No write permission onexperiment_id=%i",experiment_id))
#    return()
#  }
#  entry <- MOCK_EXPERIMENT_ENTRIES[[experiment_id]]
#
#
#  if(action == "alter_cell"){
#      alt <-data$alteration
#      if("POSIXct" %in% class(entry[[names(data$alteration)]]))
#          alt <- lubridate::as_datetime(unlist(alt),tz=state$user$selected_timezone)
#
#      entry[ID==data$ID, names(data$alteration) := alt]
#  }
#  else if (action == "add_column"){
#
#    type_map <- list("DECIMAL(11, 8)" = numeric,
#          "CHAR(64)" = character,
#          "DATETIME" = .POSIXct,
#          "DOUBLE" = numeric)
#
#
#    type <- type_map[unlist(data)]
#    data[[1]] <- type
#    l <- list(type(nrow(entry)))
#    names(l) <- names(data)
#    col <- as.data.table(l)
#    MOCK_EXPERIMENT_ENTRIES[[experiment_id]] <<- cbind(entry, col)
#
#  }
#  else{
#    stop("Action not implemented")
#  }
#
#}

api_verify_passwd <- function(state, u, p){
  return("abhjegwryuibfus")
}

#api_get_experiments <- function(state){
#  state$updaters$api_fetch_time
#    warning('getting experiment table')
#  MOCK_EXPERIMENT_TABLE
#}

api_users <- function(state){
  state$updaters$api_fetch_time
  dt <- data.table(USER_ID=c(1,2,3),
                   USERNAME=c('me','testing','someone random'))
  
}

api_fetch_image_data_for_ids <- function(state, ids){
  state$updaters$api_fetch_time
  if(length(ids) <1)
    return(data.table(ID=numeric(0)))
  MOCK_WHOLE_DATA[ID %in% unlist(ids)]
}

api_get_images_id_from_datetimes <- function(state, dates){
  state$updaters$api_fetch_time
  if(length(dates) < 2)
    return(numeric(0))
  
  out <-unique(MOCK_WHOLE_DATA[DATETIME > dates[1] & DATETIME < dates[2] ,ID])
}

api_get_images_id_for_experiment <- function(state, experiment_id, row_id=NULL){
  req(state$updaters$api_fetch_time)
  if(is.null(row_id)){
    out <- lapply(MOCK_EXPERIMENT_ENTRIES[[experiment_id]][,ID], 
                  api_get_images_id_for_experiment, 
                  experiment_id=experiment_id, state=state)
    out <- list(image_ids=unlist(out))
  }
  else{
    entry <- MOCK_EXPERIMENT_ENTRIES[[experiment_id]][ID==row_id]
    out <- list(MOCK_WHOLE_DATA[DEVICE_ID == entry$DEVICE_ID & 
                             DATETIME <= entry$END_DATETIME &
                             DATETIME >= entry$START_DATETIME, ID])
    names(out) <- "image_ids"
  }
  return(out)
}
#
#
#api_get_experiment <- function(state, experiment_id){
#  state$updaters$api_fetch_time
#  MOCK_EXPERIMENT_ENTRIES[[experiment_id]]
#}


api_available_annotators <- function(state){
  return(data.table('x'=""))
}



#######################in memory db #################################

make_mock_data <- function(start_datetime,
                           end_datetime,
                           n_dev,
                           mock_db_file=NULL,
                           samplin_freq = 20*60,
                           prop_NA = 0.05,# remove data randomly
                           seed=1 # break when seed=1

){

  if(!is.null(mock_db_file)){
    dt <- fread(mock_db_file)
    dt[,DATETIME := fastPOSIXct(DATETIME, 'UTC')]
    return(dt)
  }

  set.seed(seed)
  dt <- data.table(DEVICE_ID= replicate(n_dev, format(as.hexmode(round(runif(1, 0, 2e9))), 8)))
  foo <- function(){
    datetime = seq(from = start_datetime, to = end_datetime, by=samplin_freq)

    datetime = datetime + runif(length(datetime),
                                min = -samplin_freq / 20,
                                max = +samplin_freq / 20
    )

    datetime
  }

  dt <- dt[,.(DATETIME=foo()), by=DEVICE_ID]

  dt[, timediff := as.numeric(DATETIME - fastPOSIXct("2020-01-01T00:00:00Z"), units='secs'),
     by=DEVICE_ID]


  dt[, ID := 1:.N]
  dt[, TEMPERATURE := rnorm(.N, 0, 5) + 5 + 20* sin(pi * timediff/(3600* 24))^ 2 ]
  dt[, RELATIVE_HUMIDITY := rnorm(.N,0,20) + 100* cos(pi * timediff/(3600* 24))^ 2 ]
  dt[, RELATIVE_HUMIDITY := ifelse(RELATIVE_HUMIDITY<0, 0, RELATIVE_HUMIDITY) ]
  dt[, RELATIVE_HUMIDITY := ifelse(RELATIVE_HUMIDITY>100, 100, RELATIVE_HUMIDITY) ]

  dt[,UPLOADER := 'synthetic']
  dt[,TIME_UPLOADED := Sys.time()]
  dt[,UPLOAD_CONFIRMED := TRUE]
  dt[,MD5SUM := NA]
  dt[,PREVIEW_ISO:= 100]

  dt[,PREVIEW_BRIGHTNESS_VALUE := rnorm(.N, 0, 5) +  20000 * sin(pi * timediff/(3600* 24))^ 2]
  dt[,PREVIEW_EXPOSURE_TIME := rnorm(.N, 0, 5) +  5000  - 2000 * sin(pi * timediff/(3600* 24))^ 2 ]
  dt[,PREVIEW_SHUTTER_SPEED := PREVIEW_EXPOSURE_TIME]

  dt[, LATITUDE:=runif(1,48, 50),by=DEVICE_ID]
  dt[, LONGITUDE:=runif(1,-124, -122),by=DEVICE_ID]
  dt[, ALTITUDE:=runif(1,0, 1050),by=DEVICE_ID]


  mask <- runif(nrow(dt)) < prop_NA
  dt[mask, RELATIVE_HUMIDITY := NA]
  dt[mask, TEMPERATURE := NA]

  dt
}


new_experiment <- function(){
    data.table( ID = numeric(0),
                DEVICE_ID = character(0),
                START_DATETIME = .POSIXct(0)[0],
                END_DATETIME = .POSIXct(0)[0])
}

N_MOCK_DEV <- 12
#end <- fastPOSIXct("2020-09-04T21:10:06Z")
#start <- fastPOSIXct("2020-07-01T01:48:04Z")
end <- Sys.time()
start <- Sys.time()  -  24*3600*30
MOCK_WHOLE_DATA <- make_mock_data(start, end ,N_MOCK_DEV, mock_db_file = NULL)
CURRENT_USER_ID <- 1

MOCK_EXPERIMENT_TABLE <- data.table(EXPERIMENT_ID=c(2,3,5),
                                    USER_ID=c(1,1,2),
                                    NAME=LETTERS[1:3],
                                    TIME_CREATED= '2012-10-20T12:12:33Z',
                                    NOTES=letters[3:1],
                                    CAN_ADMIN=1,
                                    CAN_WRITE=c(1,0,1),
                                    CAN_READ=1)


MOCK_EXPERIMENT_ENTRIES <- list(5)
set.seed(4)
spl <- sample(unique(MOCK_WHOLE_DATA[,DEVICE_ID]))


start <- fastPOSIXct("2020-07-01T01:48:04Z")
end <- fastPOSIXct("2020-09-04T21:10:06Z")


MOCK_EXPERIMENT_ENTRIES[[2]] <- data.table(ID = 2:3,
                                           DEVICE_ID=spl[1:2],
                                           START_DATETIME= c(fastPOSIXct("2020-08-08T01:48:04Z"), fastPOSIXct("2020-07-08T01:48:04Z")),
                                           END_DATETIME= c(fastPOSIXct("2020-09-02T01:48:04Z"), fastPOSIXct("2020-12-08T01:48:04Z"))
                                           )


MOCK_EXPERIMENT_ENTRIES[[3]] <- new_experiment()
MOCK_EXPERIMENT_ENTRIES[[5]] <- new_experiment()
