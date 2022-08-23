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

api_get_images <- function(state, dates, dev = "%", what_images="thumbnail-mini", what_annotations="metadata"){
    # force reactive vals refresh
    state$updaters$api_fetch_time
    #token <- state$user$auth_token

    #warning("dates before:")
    #url = make_url(state, 'get_image_series', what_images)
    dates <- strftime(as.POSIXct(dates), DATETIME_FORMAT, tz='GMT')
    #warning("dates after:")

    dt <- jsonlite::fromJSON(MOCK_IMAGES_DATA_PATH)

    images <- as.data.table(dt)

   if(dev != "%"){
       print(images)
       images <- images[device == dev]
   }

    #warning("images(after):")
    #print(head(images))

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

# # returns a list of the image IDs in the current selected projet/experiment
# api_get_images_id_for_experiment <- function(state, selected_proj_id, what_images="thumbnail-mini", what_annotations="metadata") {
#     # look up all datetime stretches in series table
#     entry <- PROJECT_ENTRIES_TABLES_LIST[[selected_proj_id]]
#     # feed dates into api_get_images()
#     project_dates <- c(entry$start_datetime, entry$end_datetime)
#     # TODO: check correct device
#     images <- api_get_images(state, project_dates)
#     images
# }

########## Projects Management ###########

# initialize and return:
# either an empty master projects meta-info table, or
# if a JSON file provided, read it into a project table
new_projects_table <- function(db_file_path="") {
    if (db_file_path != "") {
        # TODO: check validity of file data
        #       force PROJECT_IDs to be imported as strings
        as.data.table(fromJSON(file.path(db_file_path)))
    }
    else {
        data.table(
                id = numeric(0),
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
        warning("below:")
        print(as.data.table(fromJSON(file.path(db_file_path))))
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
        dt <- as.data.table(fromJSON(file.path(db_file_path)))
        dt[, start_datetime := fastPOSIXct(start_datetime)]
        dt[, end_datetime := fastPOSIXct(end_datetime)]
        dt
    }
    else {
        data.table(
                id = character(0),
                device_id = character(0),
                # just POSIX time objects, value irrelevant
                start_datetime = .POSIXct(0)[0],
                end_datetime = .POSIXct(0)[0]
                )
    }
}
# initialize and return:
# either an empty project entries tables list, or
# if JSON files provided (one per project, all in one directory), read it into a project entries tables list,
# WHERE each element (a table) of the list is named the source data file's base-name
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

    PROJECTS_RECORD[id %in% accessible_projs_ids]
}

# get corresponding entries(sub-data.table) in perm. table
api_get_project_permissions <- function(state, proj_id) {
    if (proj_id == '%') {
        writeLines("\ngetting all projects' permissions")
        writeLines(paste( "user =", "testing"))
        PERMISSIONS_TABLE[username == "testing" & level > 0]
    } else if (is_member(proj_id, "testing")) {
        PERMISSIONS_TABLE[project_id == proj_id]
    }
}

.api_update_project <- function(proj_id, data) {
    print(PROJECTS_RECORD)
    n_match_entries <- PROJECTS_RECORD[id == proj_id, .N]
    warning(paste0("num matches = ", n_match_entries))
    if (n_match_entries == 1) {
        # only change fields/cols specified (in data)
        upd_cols <- names(data)
        # force updating permissions to special modal interface
        if ("level" %in% upd_cols) {
            upd_cols[["level"]] <- NULL
        }
        warning("upd_cols")
        print(data)
        warning("upd_cols of PROJECTS_RECORD")
        print(PROJECTS_RECORD[, (upd_cols)])
        # update join, [src](https://stackoverflow.com/questions/44433451/r-data-table-update-join)
        # fixme id on projects_dt and project_id on premission_dt
        out = PROJECTS_RECORD
        out[, "project_id" := id]
        out <-  out[data, on="project_id", (upd_cols) := mget(paste0("i.", upd_cols))]
        out[, project_id := NULL]
        out
    } else if (n_match_entries > 1) {
        warning(paste("multiple project metadata table entries found for project ID", proj_id))
    }
}

.api_put_new_project <- function(data) {
    # 1_dec == 1_hexadec
    proj_id <- 1
    if ((PROJECTS_RECORD[,.N]) != 0) {
        # ids all just increment by 1 each row
        proj_id <- PROJECTS_RECORD[, max(id)] + 1
    }
    # NOTE: below assignments use global <<-
    # when translate to Python, actually update orig SQL tables
    proj_row <- data.table(id = proj_id,
                           name = data[["name"]],
                           description = data[["description"]],
                           notes = data[["notes"]]
                        )
    PROJECTS_RECORD <<- rbindlist(list( PROJECTS_RECORD, proj_row ))

    # creator must be an admin
    PERMISSIONS_TABLE <<- rbindlist(list( PERMISSIONS_TABLE,
                                      data.table(id = proj_id,
                                                 username = "testing",
                                                 level = 3 )
                                      ))
    # init blank entries table
    PROJECT_ENTRIES_TABLES_LIST[[proj_id]] <<- new_entries_table()

}

# for all below, if proj_id specified, will try to update existing entry with data specified
# otherwise, arbitrary proj_id for now, real proj_id will be generated by SQL DB
#   do not include proj_id in "data" args
# add row to master projects record table: {proj_id, name, description, notes}
# add row to master permissions table: {proj_id, username, level}
#   level can be 0, 1, or 2,
#       0: read only,
#       1: read, write
#       2: read, write, admin(manage members, delete proj)
# will be back/mid-end for webapp create new project interface
# TODO: change to put_projects(state, <a list of "data"s>)
#api_put_project <- function(state, data, proj_id=NULL) {
#    if (!is.null(proj_id)) {
#        .api_update_project(state, proj_id, data)
#    } else {
#        .api_put_new_project(state, data)
#    }
#    PROJECTS_RECORD[project_id == proj_id]
#}
# datas_list a list of the data fields dictionaries each specifying a project metadata entry
#api_put_projects <- function(state, datas_list) {
api_put_projects <- function(datas_list) {
    added_rows <- lapply(datas_list, function(data) {
            #"project_id" %in% names(data) &&
        if (!is.null(data[["id"]]) )
        {
            warning("project ID:")
            print(data[["id"]])
            .api_update_project(data[["id"]], data)
        }
        else {
            .api_put_new_project(data)
        }
    })
    # combine into a vec
    #PROJECTS_RECORD[project_id == proj_id]
    warning("rows added:")
    print(added_rows)
    added_rows
}

# returns the all-data/series metadata data.table for the project specified by the given proj_id
# if none found, returns NULL
api_get_project_series <- function(state, proj_id) {
    if (! class(proj_id) %in% c("numeric", "integer")) {
        warning("`proj_id` must be an integer")
        warning(class(proj_id))
    }
    if (!(proj_id %in% names(PROJECT_ENTRIES_TABLES_LIST))) {
        warning(paste( "Entries/data table not found for project", proj_id))
        return(NULL)
    }
    PROJECT_ENTRIES_TABLES_LIST[[proj_id]]
}

# if `ser_id` found in the series metadata table, overwrites table entry with a row specified by `data`
# otherwise, adds to the series metadata table for the project specified by `ser_id`, a new row defined by argument `data`
.api_update_project_series <- function(state, ser_id, proj_id, data) {
    SERIESS_TABLE <- PROJECT_ENTRIES_TABLES_LIST[[proj_id]]
    if (SERIESS_TABLE[id == ser_id, .N] == 0) {
        warning(paste("no entry of series ID", ser_id, "found"))
        return(NULL)
    }
    # only change fields/cols specified (in data)
    upd_cols <- names(data)
    # update join, [src](https://stackoverflow.com/questions/44433451/r-data-table-update-join)
        PROJECT_ENTRIES_TABLES_LIST[[proj_id]][data, on="series_id", (upd_cols) := mget(paste0("i.", upd_cols))]

    # return added row
    PROJECT_ENTRIES_TABLES_LIST[[proj_id]][series_id == ser_id]
}

.api_put_new_project_series <- function(state, proj_id, data) {
    # generate ser_id
    if ((PROJECT_ENTRIES_TABLES_LIST[[proj_id]][,.N]) != 0) {
        # ids all just increment by 1 each row
        ser_id <- PROJECT_ENTRIES_TABLES_LIST[[proj_id]][, max(as.hexmode(series_id))] + 1
        ser_id <- as.character(as.hexmode(ser_id))
    } else {
        ser_id <- "00000001"
    }
    #data[["series_id"]] <- ser_id
    row <- as.data.table(data)
    row[1, series_id := ser_id]
    row[1, start_datetime := fastPOSIXct(start_datetime)]
    row[1, end_datetime := fastPOSIXct(end_datetime)]

    writeLines("putting")
    print(row)

    PROJECT_ENTRIES_TABLES_LIST[[proj_id]] <<- rbind(PROJECT_ENTRIES_TABLES_LIST[[proj_id]], row, fill=TRUE)

    # return added row
    PROJECT_ENTRIES_TABLES_LIST[[proj_id]][series_id == ser_id]
}

# adds to the series metadata table for the project specified by `proj_id`, a new row defined by argument `data`
# if no table found for the `proj_id`, returns NULL <- should at least be a null-initialized one from when the project was created
# if provided `data` is missing values, returns NULL
api_put_project_series <- function(state, proj_id, data, ser_id=NULL) {
    #proj_row <- data.table( series_id = numeric(0),
    #                        device_id = character(0),
    #                        # just POSIX time objects, value irrelevant
    #                        start_datetime = .POSIXct(0)[0],
    #                        end_datetime = .POSIXct(0)[0] )
    if (is.null( api_get_project_series(state, proj_id) )) {
        warning("can't add row if table to add to doesn't exist, aborting")
        return(NULL)
    }
    SERIESS_TABLE <- PROJECT_ENTRIES_TABLES_LIST[[proj_id]]

    # check if `data` valid
    mand_cnames <- c("device_id", "start_datetime", "end_datetime")
    lapply(mand_cnames, function(cname) {
                           if (!isTruthy( data[[cname]] )) {
                               warning(paste("api_put_project_series():", cname, "empty in supplied params"))
                               return(NULL)
                           }
    })
    #lapply(state$config$DATETIME_COLS_HEADERS, function(colhead) {
    #    data[[colhead]] <<- fastPOSIXct(data[[colhead]])
    #})
    
    writeLines("current column types")
    print(SERIESS_TABLE[, lapply(.SD, class)])

    writeLines("data")
    print(data)
    writeLines("data column types")
    print(lapply(data, class))

    if (!is.null(ser_id)) {
        return(.api_update_project_series(state, ser_id, proj_id, data))
    } else {
        matches <- SERIESS_TABLE[device_id == as.character(data[["device_id"]]) &&
                          start_datetime == data[["start_datetime"]] &&
                          end_datetime == data[["end_datetime"]] ]
            # check if entry for this series already exists
        if (matches[, .N] == 1) {
            warning("series with same dev ID, start and end as the one to add already in table:")
            #print(matches)
                                        # series ID of found/matching entry
            return(.api_update_project_series(state, matches[1, series_id], proj_id, data))
        } else {
            return(.api_put_new_project_series(state, proj_id, data))
        }
    }
    ## return added/updated row
    #PROJECT_ENTRIES_TABLES_LIST[[proj_id]][series_id == ser_id]
}

# TODO: use all columns in existing table including user-created
#put_project_series_columns <- function(...)?

####### in-mem DB #########
# current username in state
# master tables
# list, each elem is a project's entrie*s* ***table***
PROJECTS_RECORD <- new_projects_table(MOCK_PROJECTS_TABLE_PATH)
#print(PROJECTS_RECORD)
PERMISSIONS_TABLE <- new_permissions_table(MOCK_PERMISSIONS_TABLE_PATH)
#PERMISSIONS_TABLE[, username := ..state$config$STICKY_PI_TESTING_USER]
#print(PERMISSIONS_TABLE)
PROJECT_ENTRIES_TABLES_LIST <- new_entries_tables_list(MOCK_ENTRIES_TABLES_DIR_PATH)
#print(PROJECT_ENTRIES_TABLES_LIST)
#print(new_entries_table("www/1.json"))

###### Tests ######
TESTPROJ3_4_ENTRIES <- list(
    list(
        name = "Afer",
        description = "Exploring predators of aphids in Kananaskis",
        notes = "bring snowshoes from fall to early spring"
    ),
    list(
        notes = "bring snowshoes from fall to early spring"
    ),
    list(
        name = "Zambia local",
        description = "ecological study for local community smallholder farm in Zambia",
        notes = character(0)
    )
)
# api_put_projects(TESTPROJ3_4_ENTRIES)
