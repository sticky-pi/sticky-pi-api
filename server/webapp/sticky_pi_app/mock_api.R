TEST_DATA_DIR_PATH <- "www/test"
MOCK_PROJECTS_TABLE_PATH <- file.path(TEST_DATA_DIR_PATH, "projects.json")
MOCK_PERMISSIONS_TABLE_PATH <- file.path(TEST_DATA_DIR_PATH, "permissions.json")
MOCK_ENTRIES_TABLES_DIR_PATH <- file.path(TEST_DATA_DIR_PATH, "project-entries-tables")
MOCK_IMAGES_DATA_PATH <- file.path(TEST_DATA_DIR_PATH, "data.json")

DATA_HEADERS <- list(
                     datetime = "datetime",
                     id = "id"
)
#PROJECT_SERIES_COLUMN_TO_R_TYPES_MAP <- list(
#          "lng" = numeric(0),
#          "lat" = numeric(0),
#          "char" = character(0),
#          "datetime" = .POSIXct(0)[0],
#          "num" = numeric(0)
#          )
# NOTE: use regex, %like%, etc to match SQL DECIMAL(...,...) types
SQL_TO_R_TYPES_MAP <- list(
          "DECIMAL\\([0-9]+(\\s?)+,(\\s?)+[0-9]+\\)" = numeric(0),
          "CHAR\\([0-9]+\\)" = character(0),
          "DATETIME" = .POSIXct(0)[0],
          "DOUBLE" = numeric(0)
          )
# given a SQL type specified as one of the names of SQL_TO_R_TYPES_MAP (a string), returns an "empty" instance of the corresponding R type
.SQLtoR_type <- function(SQLt) {
    matches_lgl <- sapply(names(SQL_TO_R_TYPES_MAP), function(match_to, match_str){ match_str %like% match_to }, match_str = SQLt)
    map_matches <- SQL_TO_R_TYPES_MAP[matches_lgl]
    if (length(map_matches) > 1) {
        warning("SQL type given matches more than one possibility:")
        print(map_matches)
    } else if (length(map_matches) == 0) {
        warning(paste("SQL type given,", SQLt, ", does not match any valid types:", names(SQL_TO_R_TYPES_MAP), '\n'))
    }
    return(map_matches[[1]])
}

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
    #url = make_url(state, 'get_image_series', what_images)
    dates <- strftime(as.POSIXct(dates), DATETIME_FORMAT, tz='UTC')
    #warning("dates after:")

    dt <- jsonlite::fromJSON(MOCK_IMAGES_DATA_PATH)
    warning(MOCK_IMAGES_DATA_PATH)

    images <- as.data.table(dt)

   if(dev != "%"){
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
        warning("TODEL: loaded permissions table")
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
                id = numeric(0),
                device = character(0),
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
can_write <- function(proj_id, usrnm) {
    PERMISSIONS_TABLE[project_id == proj_id & username == usrnm, level] >= 2
}

####### API Methods #######
# return meta-info of all the projects the user has read access to
api_get_projects <- function(state) {
    accessible_projs_ids <- PERMISSIONS_TABLE[username == state$config$STICKY_PI_TESTING_USER & level >= 1, project_id]

    PROJECTS_RECORD[id %in% accessible_projs_ids]
}

# get corresponding entries(sub-data.table) in perm. table
# TODO: simplify output 1-row data.table --> list
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
    n_match_entries <- PROJECTS_RECORD[id == proj_id, .N]
    warning(paste0("num matches = ", n_match_entries))
    if (n_match_entries == 1) {
        # only change fields/cols specified (in data)
        upd_cols <- names(data)
        # force updating permissions to special modal interface
        if ("level" %in% upd_cols) {
            upd_cols[["level"]] <- NULL
        }
        #warning("TODEL: upd_cols")
        #print(data)
        #warning("TODEL: upd_cols of PROJECTS_RECORD")
        #print(PROJECTS_RECORD[, (upd_cols)])
        # update join, [src](https://stackoverflow.com/questions/44433451/r-data-table-update-join)
        # fixme id on projects_dt and project_id on premission_dt
        PROJECTS_RECORD[data, on=c(id = "project_id"), (upd_cols) := mget(paste0("i.", upd_cols))]
    }
    else if (n_match_entries > 1) {
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
    PROJECTS_RECORD <<- rbind(PROJECTS_RECORD, proj_row )

    # creator must be an admin
    PERMISSIONS_TABLE <<- rbind(PERMISSIONS_TABLE,
                                data.table(project_id = proj_id,
                                           username = "testing",
                                           level = 3 )
    )
    # init blank entries table
    # list attribute names must be strings
    PROJECT_ENTRIES_TABLES_LIST[[as.character(proj_id)]] <<- new_entries_table()

    #warning("TODEL: new entries put in projects table, permissions table and series tables list")
    proj_row
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
# datas_list a list of the data fields dictionaries each specifying a project metadata entry
api_put_projects <- function(state, datas_list) {
    added_rows <- lapply(datas_list, function(data) {
            #"project_id" %in% names(data) &&
        if (!is.null(data[["id"]]) )
        {
            #warning("TODEL: project ID:")
            #print(data[["id"]])
            .api_update_project(data[["id"]], data)
        }
        else {
            .api_put_new_project(data)
        }
    })
    warning("TODEL: rows added:")
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
        PROJECT_ENTRIES_TABLES_LIST[[proj_id]][data, on = c(id="id"), (upd_cols) := mget(paste0("i.", upd_cols))]

    # return added row
    PROJECT_ENTRIES_TABLES_LIST[[proj_id]][id == ser_id]
}

.api_put_new_project_series <- function(state, proj_id, data) {
    # generate ser_id
    if ((PROJECT_ENTRIES_TABLES_LIST[[proj_id]][,.N]) != 0) {
        # ids all just increment by 1 each row
        ser_id <- PROJECT_ENTRIES_TABLES_LIST[[proj_id]][, max(id)] + 1
    } else {
        ser_id <- 1
    }
    row <- as.data.table(data)
    row[1, id := ser_id]
    row[1, start_datetime := fastPOSIXct(start_datetime)]
    row[1, end_datetime := fastPOSIXct(end_datetime)]

    writeLines("TODEL: putting")
    print(row)


    PROJECT_ENTRIES_TABLES_LIST[[proj_id]] <<- rbind(PROJECT_ENTRIES_TABLES_LIST[[proj_id]], row, fill=TRUE)

    # return added row
    PROJECT_ENTRIES_TABLES_LIST[[proj_id]][id == ser_id]
}

# adds to the series metadata table for the project specified by `proj_id`, a new row defined by argument `data`
# if no table found for the `proj_id`, returns NULL <- should at least be a null-initialized one from when the project was created
# if provided `data` is missing values, returns NULL
api_put_project_series <- function(state, proj_id, data, ser_id=NULL) {
    #proj_row <- data.table( id = numeric(0),
    #                        device = character(0),
    #                        # just POSIX time objects, value irrelevant
    #                        start_datetime = .POSIXct(0)[0],
    #                        end_datetime = .POSIXct(0)[0] )
    if (is.null( api_get_project_series(state, proj_id) )) {
        warning("can't add row if table to add to doesn't exist, aborting")
        return(NULL)
    }
    SERIESS_TABLE <- PROJECT_ENTRIES_TABLES_LIST[[proj_id]]

    # check if `data` valid
    mand_cnames <- c("device", "start_datetime", "end_datetime")
    put_rows <- data.table()
    lapply(mand_cnames, function(cname) {
                           if (!isTruthy( data[[cname]] )) {
                               warning(paste("api_put_project_series():", cname, "empty in supplied params"))
                               return(NULL)
                           }
    })
    #lapply(state$config$DATETIME_COLS_HEADERS, function(colhead) {
    #    data[[colhead]] <<- fastPOSIXct(data[[colhead]])
    #})
    
    #writeLines("current column types")
    #print(SERIESS_TABLE[, lapply(.SD, class)])

    #writeLines("data")
    #print(data)
    #writeLines("data column types")
    #print(lapply(data, class))

    if (!is.null(ser_id)) {
        return(.api_update_project_series(state, ser_id, proj_id, data))
    } else {
        matches <- SERIESS_TABLE[device == as.character(data[["device"]]) &&
                          start_datetime == data[["start_datetime"]] &&
                          end_datetime == data[["end_datetime"]] ]
            # check if entry for this series already exists
        if (matches[, .N] == 1) {
            warning("series with same dev ID, start and end as the one to add already in table:")
            #print(matches)
                                        # series ID of found/matching entry
            put_rows <- rbind(put_rows, .api_update_project_series(state, matches[1, id], proj_id, data))
        } else {
            put_rows <- rbind(put_rows, .api_put_new_project_series(state, proj_id, data))
        }
    }
    ## return added/updated row
    #PROJECT_ENTRIES_TABLES_LIST[[proj_id]][id == ser_id]
    put_rows
}

.api_delete_single_series <- function(data) {
    if (!isTruthy(data[["project_id"]])) {
        warning("project ID not specified, skipping")
        return(NULL)
    }
    if (! can_write(data[["project_id"]], state$config$STICKY_PI_TESTING_USER)) {
        warning("must have write-level permission to delete a series")
        return(NULL)
    }
    if (!isTruthy(data[["id"]])) {
        warning("series ID not specified, skipping")
        return(NULL)
    }
    proj_id <- data[["project_id"]]
    ser_id <- data[["id"]]
    SERIESS_TABLE <- PROJECT_ENTRIES_TABLES_LIST[[proj_id]]

    matches <- SERIESS_TABLE[id == ser_id]
    if (matches[, .N] == 0) {
        warning(paste("No series found for project ID", proj_id, ", series ID", ser_id, ", skipping"))
        return(NULL)
    }
    # delete rows, return deleted
    # ["[delete rows by reference]'s filed as an issue"](https://stackoverflow.com/a/10791729)
    #SERIESS_TABLE[id == ser_id, .SD := NULL, by=ser_id]
    PROJECT_ENTRIES_TABLES_LIST[[proj_id]] <<- PROJECT_ENTRIES_TABLES_LIST[[proj_id]][id != ser_id]
    return(matches)
}

#TODO: parallelize?
    # [subset remaining rows data.table-style](https://stackoverflow.com/a/28002448)
# deletes the series specified by datas
# datas is a list of lists, each with {"project_id", "id"}
api_delete_project_series <- function(state, datas) {
    deld <- data.table()
    lapply(datas, function(data) {
        warning("user wants to delete:")
        print(data)
        deld <- rbind(deld, .api_delete_single_series(data))
    })
    deld
}

# TODO: use all columns in existing table including user-created
.api_put_project_column <- function(data, state) {
    proj_id <- data$project_id
    proj_perm <- api_get_project_permissions(state, proj_id)
    # must have write access
    if (proj_perm[1, level] < 2) {
        return(data.table())
    }
    spec_col <- data$column_name
    # NOTE: .SQLtoR_type returns an "empty" *instance* of the R type
    spec_type_R <- .SQLtoR_type(data$column_type)
    seriess_table <- api_get_project_series(state, proj_id)
    # new col or update
    if (spec_col %in% names(seriess_table)) {
        warning("TODEL: TODO: edit existing col name")
    }
    else {
        seriess_table[, c(spec_col) := spec_type_R]
                                            # return SQL type as per specifications
        return( list(column_name = spec_col, column_type = data$column_type) )
    }
}

api_put_project_columns <- function(state, datas_list) {
    lapply(datas_list, .api_put_project_column, state)
}

####### in-mem DB #########
# current username in state

# master tables
#PROJECTS_RECORD <- new_projects_table(MOCK_PROJECTS_TABLE_PATH)
PROJECTS_RECORD <- data.table(
                      id = 1:2,
                      name = c("Light Trials",
                               "First Try"),
                      description = c("investigating effect of artificial lighting on insect communities",
                                      "standard experiments with humidity, temp data"),
                      notes = c("light data from external intensity sensor",
                                "")
)
#print(PROJECTS_RECORD)
#PERMISSIONS_TABLE <- new_permissions_table(MOCK_PERMISSIONS_TABLE_PATH)
PERMISSIONS_TABLE <- data.table(
                      project_id = 1:2,
                      username = c("testing", "testing"),
                      level = c(2, 3)
)
#PERMISSIONS_TABLE[, username := ..state$config$STICKY_PI_TESTING_USER]
#print(PERMISSIONS_TABLE)

# list, each elem is a project's entrie*s* ***table***
#PROJECT_ENTRIES_TABLES_LIST <- new_entries_tables_list(MOCK_ENTRIES_TABLES_DIR_PATH)
PROJECT_ENTRIES_TABLES_LIST <- list(
                            "2" = data.table(
                                    id = 1:4,
                                    device = c("c77dd32c", "74e9715b", "6ee9a123", "512858f4"),
                                    start_datetime = fastPOSIXct(
                                                        "2022-06-13T18:15:49Z",
                                                        "2022-06-12T19:42:19Z",
                                                        "2022-06-13T18:15:42Z",
                                                        "2022-05-25T00:03:33Z"
                                                    ),
                                    end_datetime = fastPOSIXct(
                                                        "2022-06-13T18:23:22Z",
                                                        "2022-06-21T18:19:51Z",
                                                        "2022-06-13T18:23:24Z",
                                                        "2022-05-26T00:15:46Z"
                                                    ),
                                    bait_strength = c(29.8303, 439.4434, 713.2804, 907.6277)
                            ),
                            "1" = data.table(
                                    id = 1:3,
                                    device = c("f090a1c2", "c77dd32c", "ca52767f"),
                                    start_datetime = fastPOSIXct(
                                                        "2022-06-10 21:12:48",
                                                        "2022-06-13 18:15:49",
                                                        "2022-05-25 00:45:33" ),
                                    end_datetime = fastPOSIXct(
                                                        "2022-06-21 18:09:44",
                                                        "2022-06-13 18:23:22",
                                                        "2022-06-20 21:20:20" ),
                                    height = c(42.6508, 29.8303, 61.9988),
                                    bait_strength = c(12.4906, 19.1173, 29.3656)
                            )
) 
print(PROJECT_ENTRIES_TABLES_LIST)
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
