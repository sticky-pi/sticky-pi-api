
make_url <- function(state, entry_point, what=NULL){
  loc = paste(c(entry_point, what), collapse='/')
  url  =sprintf('%s://%s:%s/%s', state$config$RSHINY_UPSTREAM_PROTOCOL,
                state$config$RSHINY_UPSTREAM_ROOT_URL,
                state$config$RSHINY_UPSTREAM_PORT,loc)
  url
}

api_verify_passwd <- function(state, u, p){
  #url  =sprintf('%s://%s:%s/get_token', state$config$API_PROTOCOL, state$config$API_ROOT_URL,state$config$API_PORT)
  url = make_url(state, 'get_token')
  o = POST(url,  authenticate(u, p, type = "basic"), content_type("application/json"))
  if(o$status_code != 200){
    Sys.sleep(1)
    return("")
  }
  token <- content(o, as='parsed', encoding="UTF-8")
  # also has an `expiration field`
  return(token$token)
}

api_get_users <- function(state){
  state$updaters$api_fetch_time
  token <- state$user$auth_token
  print(token)
  url = make_url(state, 'get_users')
  payload = jsonlite::toJSON(list(list(username="%")))
  payload = "[{}]"
  print(url)
  print(payload)
  print(payload)
  o <- POST(url, body=payload,
            authenticate(token, "", type = "basic"), content_type("application/json"))
  print(o)
  ct <- content(o, as='text', encoding="UTF-8")
  print(ct)
  dt <- jsonlite::fromJSON(ct)
  users <- as.data.table(dt)
}
api_fetch_download_s3 <- function(state, ids, what_images="thumbnail", what_annotations="data"){

  state$updaters$api_fetch_time
  token <- state$user$auth_token
  dt <- get_comp_prop(state, all_images_data)

  query = dt[id %in% ids, .(device, datetime)]
  query[, datetime:=strftime(as.POSIXct(datetime), DATETIME_FORMAT, tz='GMT')]
  post <- jsonlite::toJSON(query)

  url = make_url(state, 'get_images', what_images)

  o <- POST(url, body=post,
            authenticate(token, "", type = "basic"), content_type("application/json"))
  ct <- content(o, as='text', encoding="UTF-8")

  dt <- jsonlite::fromJSON(ct)
  images <- as.data.table(dt)

  #api_entry = 'get_uid_annotations'
  #url  =sprintf('%s://%s:%s/%s/%s', state$config$API_PROTOCOL, state$config$API_ROOT_URL,state$config$API_PORT, api_entry, what_annotations)
  url = make_url(state, 'get_uid_annotations', what_annotations)
  o = POST(url, body=post, authenticate(token, "", type = "basic"), content_type("application/json"))
  ct <- content(o, as='text', encoding="UTF-8")
  dt <- jsonlite::fromJSON(ct)
  annotations <- as.data.table(dt)
  if(nrow(annotations) == 0){
    annotations <- data.table(parent_image_id=integer(0), n_objects=integer(0), json=character(0), algo_version=character(0))
  }

  annotations =  unique(annotations[order(algo_version),], by='parent_image_id', fromLast=TRUE)
  images =  merge(x=images, y=annotations, by.y="parent_image_id", by.x="id", all.x=TRUE, suffixes=c('','_annot'))[]

    # we convert all *datetime* to posixct. we assume the input timezone is UTC (from the API/database, all is in UTC)
  # We will then just convert timezone when rendering
  images <- images[match(ids, id)]
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
}

api_get_images <- function(state, dates, what_images="thumbnail-mini", what_annotations="metadata"){

  state$updaters$api_fetch_time
  token <- state$user$auth_token

  #fixme, here, nnotations, images and users can be retreived async. using future maybe?!
  users <- api_get_users(state)

  url = make_url(state, 'get_image_series', what_images)

  dates <- strftime(as.POSIXct(dates), DATETIME_FORMAT, tz='GMT')

  post <- jsonlite::toJSON(list(list(device="%",
                                     start_datetime=dates[1],
                                     end_datetime=dates[2] )),
                           auto_unbox = TRUE)


  o = POST(url, body=post,  authenticate(token, "", type = "basic"), content_type("application/json"))
  ct <- content(o, as='text', encoding="UTF-8")
  dt <- jsonlite::fromJSON(ct)
  images <- as.data.table(dt)


  if(nrow(images) == 0){
    return(data.table())
  }


  url = make_url(state, 'get_uid_annotations_series', what_annotations)
  o = POST(url, body=post,
          authenticate(token, "", type = "basic"), content_type("application/json"))
  ct <- content(o, as='text', encoding="UTF-8")
  dt <- jsonlite::fromJSON(ct)
  annotations <- as.data.table(dt)



    if(nrow(annotations) == 0){
      annotations <- data.table(parent_image_id=integer(0), n_objects=integer(0), json=character(0), algo_version=character(0))
    }

  #fixme we should only get the unique by algo name x version so we don't have multiple matches for annots
  annotations =  unique(annotations[order(algo_version),], by='parent_image_id', fromLast=TRUE)

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

  o <-  merge(x=o, y=users[, .(id, username)], by.x="api_user_id", by.y="id", all.x=TRUE)
  setnames(o,"username", "api_user")
  images <- o

  images
}



