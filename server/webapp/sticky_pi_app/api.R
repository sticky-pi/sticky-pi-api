
api_verify_passwd <- function(state, u, p){
  url  =sprintf('%s://%s/get_token', state$config$API_PROTOCOL, state$config$API_ROOT_URL)
  o = POST(url,
          authenticate(u, p, type = "basic"), content_type("application/json"))
  if(o$status_code != 200){
    Sys.sleep(1)
    return("")
  }
  token <- content(o, as='parsed')
  # also has an `expiration field`
  return(token$token)
}


api_fetch_download_s3<- function(state, ids, what_images="thumbnail", what_annotations="data"){

  state$updaters$api_fetch_time
  token <- state$user$auth_token
  dt <- get_comp_prop(state, all_images_data)

  query = dt[id %in% ids, .(device, datetime)]
  query[, datetime:=strftime(as.POSIXct(datetime), '%Y-%m-%d_%H-%M-%S', tz='GMT')]
  post <- jsonlite::toJSON(query)
  api_entry = "get_images"
  url =sprintf('%s://%s/%s/%s', state$config$API_PROTOCOL,
                state$config$API_ROOT_URL, api_entry,
                what_images)
  o = POST(url, body=post,
          authenticate(token, "", type = "basic"), content_type("application/json"))
  ct <- content(o, as='text')

  dt <- jsonlite::fromJSON(ct)

  out = as.list( dt$url)

  out

}


api_get_images <- function(state, dates, what_images="thumbnail-mini", what_annotations="metadata"){

  state$updaters$api_fetch_time
  token <- state$user$auth_token
  api_entry = "get_image_series"
  url  =sprintf('%s://%s/%s/%s', state$config$API_PROTOCOL,
                state$config$API_ROOT_URLT, api_entry,
                what_images)

  dates <- strftime(as.POSIXct(dates), '%Y-%m-%d_%H-%M-%S', tz='GMT')

  post <- jsonlite::toJSON(list(list(device="%",
                                     start_datetime=dates[1],
                                     end_datetime=dates[2] )),
                           auto_unbox = TRUE)

  o = POST(url, body=post,
          authenticate(token, "", type = "basic"), content_type("application/json"))

  ct <- content(o, as='text')

  dt <- jsonlite::fromJSON(ct)
  images <- as.data.table(dt)


  if(nrow(images) == 0){
    return(data.table())
  }



  post <- jsonlite::toJSON(images[, .(device, datetime)])
  api_entry = 'get_uid_annotations'
  url  =sprintf('%s://%s/%s/%s', state$config$API_PROTOCOL, state$config$API_ROOT_URL, api_entry, what_annotations)
  o = POST(url, body=post,
          authenticate(token, "", type = "basic"), content_type("application/json"))

  ct <- content(o, as='text')
  dt <- jsonlite::fromJSON(ct)
  annotations <- as.data.table(dt)
  if(nrow(annotations) == 0){
    annotations <- data.table(parent_image_id=integer(0), n_objects=integer(0))
  }
  images =  merge(x=images, y=annotations, by.y="parent_image_id", by.x="id", all.x=TRUE, suffixes=c('','_annot'))[]
    # we convert all *datetime* to posixct. we assume the input timezone is UTC (from the API/database, all is in UTC)
  # We will then just convert timezone when rendering

  o <- as.data.table(
    lapply(names(images),function(x){
      if(x %like% "*datetime*")
        fasttime::fastPOSIXct(images[[x]], tz='UTC')
      else
        images[[x]]
    })
  )
  setnames(o, colnames(images))
  images <- o

  images
}


# api_fetch_table_ <- function(state, api_entry){
#  # this allows to rerun api calls on demand by setting this state var to the current time
#  state$updaters$api_fetch_time
#
#  ip <- state$config$API_ROOT_URL
#  port <- state$config$API_PORT
#  req(state$user$auth_token)
#  token <- state$user$auth_token
#  url <- sprintf("http://%s:%s/api/%s",
#                 ip,
#                 port,
#                 api_entry)
#  # logjs(url)
#  o = post(url,
#          authenticate(token, "", type = "basic"))
#  if(o$status_code != 200){
#    warning(sprintf("Cannot retrieve data for %s", api_entry))
#    return()
#  }
#  ct <- content(o, as='text')
#  dt <- jsonlite::fromJSON(ct)
#  out <- as.data.table(dt)
#
#  if(nrow(out) == 0)
#    return()
#  # we convert all *DATETIME* to posixct. we assume the input timezone is UTC (from the API/database, all is in UTC)
#  # We will then just convert timezone when rendering
#
#  o <- as.data.table(
#    lapply(names(out),function(x){
#      if(x %like% "*DATETIME*")
#        fasttime::fastPOSIXct(out[[x]], tz='UTC')
#      else
#        out[[x]]
#    })
#  )
#  setnames(o, colnames(out))
#  out <- o
#  return(out)
#}
#
#api_fetch_download_s3_ <- function(state, image_id, url_base){
#  if(!isTruthy(image_id))
#    return()
#  api_entry = sprintf("%s/%i", url_base, image_id)
#  url = unlist(api_fetch_table_(state, api_entry))
#  names(url) <- NULL
#  url
#}
#
#api_fetch_download_s3 <- function(state, image_id, url_base = "download_s3"){
#  api_fetch_download_s3_(state, image_id, url_base)
#}
#
#api_fetch_download_s3_thumbnail <- function(state, image_id, url_base = "download_s3_thumbnail"){
#  api_fetch_download_s3_(state, image_id, url_base)
#}
#api_fetch_download_s3_thumbnail_mini <- function(state, image_id, url_base = "download_s3_thumbnail_mini"){
#  api_fetch_download_s3_(state, image_id, url_base)
#}

#api_alter_experiment_list_table <- function(state, action,  api_root="set_experiment_list", data=list()){
#  req(state$updaters$api_fetch_time)
#
#
#  dt_exp_list <- get_comp_prop(state, experiment_table_list)
#
#  api_entry = sprintf("%s/%s", api_root,action)
#  ip <- state$config$API_ROOT_URL
#  port <- state$config$API_PORT
#  req(state$user$auth_token)
#  token <- state$user$auth_token
#
#    # changing a cell that is datetime returns a character! we fix it with lubridate if no
#    # timezone is provided by user (explicitely), we use the state's
#
#  if(action == "alter_cell"){
#      if("POSIXct" %in% class(dt_exp_list[[names(data$alteration)]]))
#         data$alteration<- lubridate::as_datetime(unlist(alt),tz=state$user$selected_timezone)
#  }
#
#  url <- sprintf("http://%s:%s/api/%s",
#                 ip,
#                 port,
#                 api_entry)
#
#  post <- jsonlite::toJSON(list(data=data), auto_unbox = TRUE)
#  o <- POST(url,
#            body=post,
#            content_type("application/json"),
#            authenticate(token, "", type = "basic")
#            )
#  if(o$status_code != 200){
#    warning(sprintf("Cannot retrieve data for %s", api_entry))
#    return()
#  }
#    ct = content(o, as='text')
#  return(jsonlite::fromJSON(ct))
#}
#
#api_alter_experiment_table <- function(state, action, experiment_id,  api_root="set_experiment", data=list()){
#  api_entry = sprintf("%s/%i/%s", api_root,experiment_id,action)
#
#  ip <- state$config$API_IP
#  port <- state$config$API_PORT
#  req(state$user$auth_token)
#  token <- state$user$auth_token
#
#  url <- sprintf("http://%s:%s/api/%s",
#                 ip,
#                 port,
#                 api_entry)
#    dt_exp <- get_comp_prop(state, experiment_table)
#
#
#    if(action == "alter_cell"){
#        if("POSIXct" %in% class(dt_exp[[names(data$alteration)]])){
#          n <- names(data$alteration)
#          data$alteration <- list(lubridate::as_datetime(unlist(data$alteration ),tz=state$user$selected_timezone))
#          names(data$alteration) <- n
#
#        }
#    }
#
#  post <- jsonlite::toJSON(list(data=data), auto_unbox = TRUE)
#  o <- POST(url,
#            body=post,
#            content_type("application/json"),
#            authenticate(token, "", type = "basic")
#            )
#  if(o$status_code != 200){
#    warning(sprintf("Cannot retrieve data for %s", api_entry))
#    return()
#  }
#  ct = content(o, as='text')
#  return(jsonlite::fromJSON(ct))
#}
#
#api_get_images_id_for_experiment <- function(state, experiment_id, row_id=NULL){
#  if(is.null(row_id))
#    api_entry = sprintf("get_images_id_for_experiment/%i", experiment_id)
#  else
#    api_entry = sprintf("get_images_id_for_experiment/%i/%i", experiment_id, row_id)
#  out <- api_fetch_table_(state, api_entry)
#  out <- unlist(out)
#  if(!isTruthy(out))
#      return(list(image_ids=numeric(0)))
#  list(image_ids=out)
#}

#api_users <- function(state){
#  api_fetch_table_(state, "users")
#}


#api_available_annotators <- function(state){
#  api_fetch_table_(state, "available_annotators")
#}
#
#api_get_experiments <- function(state){
#  api_entry='get_experiments'
#  api_fetch_table_(state, api_entry)
#}
#
#api_get_experiment <- function(state, experiment_id){
#  api_entry=sprintf('get_experiment/%i', experiment_id)
#  api_fetch_table_(state, api_entry)
#}
#
#api_fetch_image_data_for_ids <- function(state, ids){
#  req(state)
#  # here, we use a direct call to mysql in readonly mode. that avoid a lot of stress on the API
#  if(length(ids) <1)
#    return(data.table())
#
#  command <- sprintf("SELECT * FROM IMAGES WHERE ID IN (%s)",  paste(ids, collapse=', '))
#  con <- DBI::dbConnect(RMariaDB::MariaDB(),
#                        host = state$config$MYSQL_SERVER_IP,
#                        user = state$config$MYSQL_READER,
#                        password = state$config$MYSQL_READER_PASSWORD,
#                        dbname = state$config$MYSQL_DATABASE)
#  on.exit(DBI::dbDisconnect(con))
#
#
#  tb <- RMariaDB::dbGetQuery(con, command)
#  dt <- as.data.table(tb)
#  if(state$data_scope$selected_detector != "None"){
#    command <- sprintf("SELECT * FROM `PROCESSED_%s` WHERE IMAGE_ID IN (%s)",
#                       state$data_scope$selected_detector,
#                           paste(ids, collapse=', '))
#    tb <- RMariaDB::dbGetQuery(con, command)
#    dt_annotations  <- as.data.table(tb)
#    dt_annotations[, ID:=NULL]
#    setnames(dt_annotations, c('IMAGE_ID','DATETIME', 'UPLOADER'), c('ID', 'ANNOTATION_DATETIME', 'ANNOTATION_UPLOADER'))
#    dt = dt_annotations[dt, on="ID"]
#  }
#  dt
#
#}
#
#api_get_images_id_from_datetimes <- function(state, dates){
#  dates <- strftime(as.POSIXct(dates), '%Y-%m-%d_%H-%M-%S', tz='GMT')
#  api_entry=sprintf('get_images_id_from_datetimes/%s/%s', dates[1], dates[2] )
#  api_fetch_table_(state, api_entry)
#}






