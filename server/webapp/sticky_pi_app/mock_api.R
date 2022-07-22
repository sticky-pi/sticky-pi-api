MOCK_PROJECTS_TABLE_PATH <- "www/projects.json"
MOCK_PERMISSIONS_TABLE_PATH <- "www/permissions.json"
MOCK_ENTRIES_TABLES_DIR_PATH <- "www/project-entries-tables"
MOCK_IMAGES_DATA_PATH <- "www/data.json"

DATA_HEADERS <- list(
                     datetime = "datetime",
                     id = "id"
)
# fixme, this is completely broken due to the new api
trim_ext_json <- function(path) {
	sub('\\.json$', '', path) 
}


api_verify_passwd <- function(state, u, p){
  return("abhjegwryuibfus")
}

make_rand_img_url <- function(state, width){
  # found this random image web API: https://picsum.photos/
  url = sprintf('%s://%s/%s', state$config$RSHINY_UPSTREAM_PROTOCOL,
                "picsum.photos", width)
  url
}

api_fetch_download_s3 <- function(state, ids, what_images="thumbnail", what_annotations="data") {
    state$updaters$api_fetch_time
    dt <- get_comp_prop(state, all_images_data)

    if (what_images == "thumbnail")
        width <- 4056
    else if (what_images == "thumbnail-mini")
        width <- 128
    else {
        print("invalid value of 'what_images', setting width 128 for now")
        width <- 128
    }
    # insert random image URLs
    images <- dt[, url := make_rand_img_url(..state, ..width)]

    annotations <- data.table(parent_image_id=integer(0), n_objects=integer(0), json=character(0), algo_version=character(0))
    images =  merge(x=images, y=annotations, by.y="parent_image_id", by.x="id", all.x=TRUE, suffixes=c('','_annot'))[]

    writeLines("before filter ids")
    print(images)
    # we convert all *datetime* to posixct. we assume the input timezone is UTC (from the API/database, all is in UTC)
    # We will then just convert timezone when rendering
    images <- images[id %in% ids]
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
    writeLines("after filter ids")
    print(images)
    images
}

api_get_images <- function(state, dates, what_images="thumbnail-mini", what_annotations="metadata"){
    # force reactive vals refresh
    state$updaters$api_fetch_time
    #token <- state$user$auth_token

    #url = make_url(state, 'get_image_series', what_images)
    dates <- strftime(as.POSIXct(dates), DATETIME_FORMAT, tz='GMT')

    dt <- jsonlite::fromJSON(MOCK_IMAGES_DATA_PATH)
    images <- as.data.table(dt)

    if(nrow(images) == 0){
        return(data.table())
    }

    # skip annotations for now
    #annotations <- as.data.table(dt)
    #if(nrow(annotations) == 0){
    annotations <- data.table(parent_image_id=integer(0), n_objects=integer(0), json=character(0), algo_version=character(0))
    #images =  merge(x=images, y=annotations, by.y="parent_image_id", by.x="id", all.x=TRUE, suffixes=c('','_annot'))[]
    
# we convert all *datetime* to posixct. we assume the input timezone is UTC (from the API/database, all is in UTC)
# We will then just convert timezone when rendering
    o <- as.data.table(
    lapply(names(images),function(x){
      if(x %like% paste('*',"datetime",'*', sep=''))
      {
        fasttime::fastPOSIXct(images[[x]], tz='UTC')
      }
      else
        images[[x]]
    })
    )
    setnames(o, colnames(images))
    images <- o

    # limit to datetimes range
    if(length(dates) < 2)
        return(numeric(0))
    # last 5 rows(captures)
    #print(images[.N])
    # TODO: get data.table to recognize entire `DATA_HEADERS$...` with `..` (using pre-defined vars)
    #print(unique(images[datetime > dates[1] & datetime < dates[2], datetime]))
    images <-unique(images[datetime > dates[1] & datetime < dates[2]])

    images
}

# returns a list of the image IDs in the current selected projet/experiment
api_get_images_id_for_experiment <- function(state, selected_proj_id, what_images="thumbnail-mini", what_annotations="metadata") {
    # look up all datetime stretches in series table
    entry <- PROJECT_ENTRIES_TABLES_LIST[[selected_proj_id]]
    # feed dates into api_get_images()
    project_dates <- c(entry$start_datetime, entry$end_datetime)
    # TODO: check correct device
    images <- api_get_images(state, project_dates)
    images
}

########## Projects Management ###########
put_project_series <- function() {
    data.table( series_id = numeric(0),
                device_id = character(0),
                # just POSIX time objects, value irrelevant
                start_datetime = .POSIXct(0)[0],
                end_datetime = .POSIXct(0)[0] )
}

# initialize and return:
# either an empty master projects meta-info table, or
# if a JSON file provided, read it into a project table
new_projects_table <- function(db_file_path="") {
    if (db_file_path != "") {
        # TODO: check validity of file data
        as.data.table(fromJSON(file.path(db_file_path)))
    }
    else {
        data.table(
                project_id = numeric(0),
                name = character(0),
                description = character(0),
                notes = character(0)
     )}
}

# initialize and return:
# either an empty permissions table, or
# if a JSON file provided, read it into a permissions table
new_permissions_table <- function(db_file_path="") {
    if (db_file_path != "") {
        # TODO: check validity of file data
        as.data.table(fromJSON(file.path(db_file_path)))
    }
    else {
        data.table(
                project_id = numeric(0),
                username = character(0),
                level = numeric(0)
     )}
}

# initialize and return:
# either an empty project entries table, or
# if a JSON file provided, read it into a project entries table
new_entries_table <- function(db_file_path="") {
    if (db_file_path != "") {
        # TODO: check validity of file data
        as.data.table(fromJSON(file.path(db_file_path)))
    }
    else {
        data.table(
                series_id = numeric(0),
                device_id = character(0),
                # just POSIX time objects, value irrelevant
                start_datetime = .POSIXct(0)[0],
                end_datetime = .POSIXct(0)[0]
                )
    }
}
# initialize and return:
# either an empty project entries tables list, or
# if JSON files provided (one per project, all in one directory), read it into a project entries tables list
new_entries_tables_list <- function(db_files_dir_path="") {
    JSONs_paths <- list.files( path = db_files_dir_path,
								pattern = "\\.json$",
								full.names = TRUE,
								ignore.case = TRUE )
	writeLines(JSONs_paths)
    if (length(JSONs_paths) == 0) {
        list()
    }
    else {
		# TODO: convert to for loop,
		# need to *ensure* names pair data correctly
        entries_tables_list <- lapply(JSONs_paths, new_entries_table)
        names(entries_tables_list) <- lapply( lapply(JSONs_paths, basename), trim_ext_json)
		entries_tables_list
	}
}

# permission check utils
is_admin <- function(proj_id, usrnm) {
    PERMISSIONS_TABLE[project_id == proj_id & username == usrnm, level] >= 3
}
is_member <- function(proj_id, usrnm) { 
    PERMISSIONS_TABLE[project_id == proj_id & username == usrnm, level] > 0
}
####### API Methods #######
# return meta-info of all the projects the user has read access to
api_get_projects <- function(state) {
    accessible_projs_ids <- PERMISSIONS_TABLE[username == state$config$STICKY_PI_TESTING_USER & level >= 1, project_id]
    PROJECTS_RECORD[project_id %in% accessible_projs_ids]
}

# get corresponding entries(sub-data.table) in perm. table
api_get_project_permissions <- function(state, proj_id) {
    if (proj_id == '%') {
        writeLines("\ngetting all projects' permissions")
        writeLines(paste( "user =", state$config$STICKY_PI_TESTING_USER))
        PERMISSIONS_TABLE[username == state$config$STICKY_PI_TESTING_USER & level > 0]
    } else if (is_member(proj_id, state$config$STICKY_PI_TESTING_USER)) {
        PERMISSIONS_TABLE[project_id == proj_id]
    }
}

api_get_project_series <- function(state, proj_id) {
    PROJECT_ENTRIES_TABLES_LIST[[proj_id]]
}

####### in-mem DB #########
# current username in state
# master tables
# list, each elem is a project's entrie*s* ***table***
PROJECTS_RECORD <- new_projects_table(MOCK_PROJECTS_TABLE_PATH)
#print(PROJECTS_RECORD)
PERMISSIONS_TABLE <- new_projects_table(MOCK_PERMISSIONS_TABLE_PATH)
#PERMISSIONS_TABLE[, username := ..state$config$STICKY_PI_TESTING_USER]
#print(PERMISSIONS_TABLE)
PROJECT_ENTRIES_TABLES_LIST <- new_entries_tables_list(MOCK_ENTRIES_TABLES_DIR_PATH)
#print(PROJECT_ENTRIES_TABLES_LIST)
#print(new_entries_table("www/1.json"))
