empty_exp_table <- {data.table(id=numeric(0),
                  device=character(0),
                  start_datetime=POSIXct(0),
                  end_datetime=POSIXct(0))}

check_var_name <- function(string) {

  isValidName <- function(string) {
    grepl("^([[:alpha:]]|[.][._[:alpha:]])[._[:alnum:]]*$", string)
  }

  isValidAndUnreservedName <- function(string) {
    make.names(string) == string
  }

  valid <- isValidName(string)
  unreserved <- isValidAndUnreservedName(string)
  return(valid & unreserved)
}

# ensures user inputs valid col name and returns SQL type corresponding to selected type
handle_new_series_column_user_specs <- function(dt, name, code){
    col_dupli <- name %in% colnames(dt)
    shinyFeedback::feedbackDanger("series_new_col_name", col_dupli, "Column already exists")
    req(!col_dupli, cancelOutput=TRUE)
    #if (col_dupli) {
    #    warning('Column already exists')
    #    return(NULL)
    #}

    valid_name <- check_var_name(name)
    shinyFeedback::feedbackDanger("series_new_col_name", !valid_name, "Inputted column name invalid. Must start with a letter and only contain alphanumerics, '.'")
    req(valid_name, cancelOutput=TRUE)
    map <- list("lng"= function(name)list("LONGITUDE"=  "DECIMAL(11, 8)"),
              "lat"= function(name)list("LATITUDE"=  "DECIMAL(11, 8)"),
              "char"= function(name){
                out = list()
                if (valid_name){
                  out[[name]] <- "CHAR(64)"
                  return(out)
                }},
              "datetime"= function(name){
                out = list()
                if (valid_name){
                  out[[name]] <- "DATETIME"
                  return(out)
                }},

              "num"= function(name){
                out = list()
                if (valid_name){
                  out[[name]] <- "DOUBLE"
                  return(out)
                }}
            )
  return(map[[code]](name))
}

images_in_scope <- function(state, input){
  req(state$data_scope$selected_experiment)

  sel <- state$data_scope$selected_experiment

  if(sel == 0){
    req(input$data_scope_dates)
    dates <- as.Date(input$data_scope_dates)
    images <- api_get_images(state, dates)
  }
  else{
    # projs_table <- api_get_projects(state)
    project_series <- api_get_project_series(state, sel)
    images <- lapply(project_series$id, function(i){
      row <- project_series[id==i]
      api_get_images(state, c(row$start_datetime, row$end_datetime), dev = row$device )
    })

    images <- rbindlist(images)
    old_n <- nrow(images)
    images <- unique(images)

    if(old_n != nrow(images))
      warning("Mismatch between total number of images in scope and sum of all series images. Likely a duplicate")
  }
  images
}

datatable_options <- function(dt, excluded_names="id", header_names=NULL){
    cnames <- colnames(dt)
    hidden <- c(grep('^\\.HIDDEN.*$',cnames), which(cnames %in% excluded_names))
# hidden <- numeric(0)
    #if (!is.null(header_names)) {
    #    cnames <- fill_replace_colnames(cnames, header_names)
    #}
    list(scrollX=TRUE,
       columnDefs = list(list(visible=FALSE,
                              targets=hidden))
       #colnames = cnames
    )
}

# see permission_level_to_role() in `ui.R`

# currently table consists of
# all projects visible to current user and
# user's "role" in each
experiment_list_table <- function(state, input){
  # TODO: make separate temporary session-lifespan data.table for DataTable display (experiment list table)
  req(state$updaters$api_fetch_time)
  # API already automatically checks visibility of rows
  projs_table <- api_get_projects(state)
  req(projs_table)
  # we force recomputing the images in scope. we can use that to assess the number of image belonging to each series!
  images <- get_comp_prop(state, images_in_scope)
  req(images)


  all_permissions_table <- api_get_project_permissions(state, '%')

  # first add a column, current user's permission level for each project
  # convert to role in render_...()
  curr_user_perms <- all_permissions_table[username == state$config$STICKY_PI_TESTING_USER, .(project_id, level)]

  # thanks to [merging in another table's column on common key](https://stackoverflow.com/a/34600831)
  # and [get data.table to use variable for name of **new** column]
  #fixme
  projs_table[curr_user_perms, on=c(id = "project_id"), level := i.level]

  projs_table
#
#  im_id = lapply(dt[,EXPERIMENT_ID],
#                 function(eid){
#                   api_get_images_id_for_experiment(state, eid, row_id=NULL)$image_ids
#                   })
#  dt[,.HIDDEN_image_ids := im_id]
#  dt[,.COMP_N_MATCHES := length(unlist(.HIDDEN_image_ids)), by = EXPERIMENT_ID]
#
#  # list(dt=dt, datatable=datatable)
#  dt
}
#
render_experiment_list_table<- function(state){

  DT::renderDataTable({
    exp_id <- state$data_scope$selected_experiment
    proj_table <- get_comp_prop(state, experiment_list_table)
    dt <- proj_table[, !"level"]
    # TODO: ensure experiment_list_table cannot be modified in between
    # *copy* perm. level col to preserve levels when converting to display text
    role_col <- proj_table[, .(id, role = permission_levels_to_roles(state, level))]
    # print(role_col)
    role_header <- state$config$PERMISSIONS_TABLE_HEADERS[["level"]]
    #fixme
     dt[role_col, on="id", c(role_header) := i.role]

    row <- which(dt[ ,id == exp_id])
    # if(length(row) == 1 && row > 0){
    #  state$data_scope$selected_image_ids <- unlist(dt[id == exp_id, .HIDDEN_image_ids])
    # }
    # else{
    #  row <- NULL
    # }
    # column headers renamed/"prettied" in fill_replace_colnames
    
    datatable = DT::datatable(dt,
                              selection = list(mode='single', target="row", selected = row),
                              editable = FALSE,
                              colnames = fill_replace_colnames(colnames(dt), state$config$PROJECTS_LIST_HEADERS),
                              options = datatable_options(dt,
                                                          excluded_names=c("id")
                                                         )
                              )
  })
}
show_create_project_form <- function(state, input, failed=FALSE) {
    # create/submit button in project_modal_ui() triggers experiment_list_table_add_row()
    showModal(create_project_modal_ui(state, failed))
}
experiment_list_table_add_row <- function(state, input){
    warning("TODEL: user submitted create project form")
    # should have been inputted by user in modal form
    if (is.null(input$new_project_name) || input$new_project_name == "") {
        print("TODEL: no name entered")
        show_create_project_form(state, input, failed=TRUE)
    } else {
        name <- input$new_project_name
        description <- input$new_project_description
        notes <- input$new_project_notes

        data = list(list(name=name, description=description, notes=notes))

        rows <- api_put_projects(state, data)
        state$updaters$api_fetch_time <- Sys.time()
        state$data_scope$selected_experiment <- rows[[1]][["id"]]

        removeModal()
    }
}

experiment_table <- function(state, input){
  dt_exp_list <- get_comp_prop(state, experiment_list_table)
  images <- get_comp_prop(state, images_in_scope)
  req(images)

  proj_id <- state$data_scope$selected_experiment
  if (proj_id < 1)
    return(data.table())

  dt <- api_get_project_series(state, proj_id)
  #print( paste("Project", proj_id))
  #print(dt)
  # if no matching entries table, make a blank one

  if(is.null(dt))
    return(new_entries_table())

   comp_n_matches <- function(dev, start, end){
                nrow(images[device==dev & datetime >= start & datetime < end])
                    }

  if(nrow(images) > 0){
    dt[, .COMP_N_MATCHES := comp_n_matches(.SD$device, .SD$start_datetime, .SD$end_datetime),
                  by=id]
  }
  return(dt)

  # we fetch all ID for each experiment entry

  #l <- lapply(dt[, row_id], function(row_id) {
  #  out <- api_get_images_id_for_experiment(state, experiment_id=experiment_id, row_id=row_id)

  #  if(is.null(out) | length(out) < 1)
  #    return(NULL)

  #  out <- data.table(ID = id, .HIDDEN_image_ids=out)
  #  # warning(paste(id, length(unlist(out))))
  #  out
  #}
  #)

  #dd <- rbindlist(l)
  #if(nrow(dd) < 1)
  #  return(empty_exp_table) # fixme. should be populated with the default

  #dd[, .COMP_N_MATCHES := length(unlist(.HIDDEN_image_ids)), by=ID]
  #dt <- dd[dt, on="ID"]
}
#
render_experiment_table<- function(state){

  DT::renderDataTable({
    # isn't \/ dt reactive?
    dt <- get_comp_prop(state, experiment_table)
    #print(dt)
    # proj_id <- state$data_scope$selected_experiment
    # if(proj_id > 0){
    #   state$data_scope$selected_image_ids <- unlist(dt[EXPERIMENT_ID == proj_id, .HIDDEN_image_ids])
    # }
    # else{
    #   proj_id <- NULL
    # }
    #datetime_colinds = c( match("start_datetime", colnames(dt)), match("end_datetime", colnames(dt)))
    #datetime_colinds = c("start_datetime", "end_datetime")
    #disp_dt <- dt[, c(state$config$DATETIME_COLS_HEADERS) := lapply(.SD, strftime, DATETIME_FORMAT), .SDcols = state$config$DATETIME_COLS_HEADERS]

    datatable = DT::datatable(dt,
                              selection = list(mode='single'), #, selected = proj_id),
                              editable = TRUE,
                              colnames = fill_replace_colnames(colnames(dt), state$config$PROJECT_SERIES_HEADERS),
                              options = datatable_options(dt,
                                                          excluded_names=c("id")
                                                          )
                            )
                              #%>% formatDate( datetime_colinds,
                              #            method = "toUTCString")
  })
}

#render_available_annotators <- function(state, input){
#  renderUI({
#             avail_annot_vect <- api_available_annotators(state)[[1]]
#             avail_annot_vect <- c("None",avail_annot_vect)
#             selectInput('on_select_annotator', 'Insect detector',avail_annot_vect)
#
#      }
#  )
#
#  #print(o)
#  #render({selectInput("on_select_annotator", o[[1]])})
#  #render(o)
#  #stop(available_annotators)
#}

project_series_table_add_column <- function(state, input){
    req(state$data_scope$selected_experiment != 0)
    req(input$series_new_col_name)
    req(input$series_new_col_type)
    name <- input$series_new_col_name
    type <- input$series_new_col_type

    proj_id <- state$data_scope$selected_experiment

    SQL_type <- handle_new_series_column_user_specs(get_comp_prop(state, experiment_table), name, type)
    data <- list(project_id = proj_id,
                 column_name = name,
                 column_type = type )
    # shinyFeedback will block until valid user input
    #if(!is.null(data)){
    # fixme
    warning("TODEL: user wants to add a column:")
    print(as.data.table(data))
    out <- api_put_project_columns(state, data = list(data))
    if (!is.null(out))
        state$updaters$api_fetch_time <- Sys.time()
}


#project_series_table_add_row <- function(state, input){
#  proj_id <-state$data_scope$selected_experiment
#
#  out <- api_put_project_series(state, proj_id, data=list())
#  if(isTruthy(out))
#    state$updaters$api_fetch_time <- Sys.time()
#}
#
#
series_table_alter_cell <- function(state, input){
  req(state$data_scope$selected_experiment != 0)
  req(input$experiment_table_cell_edit)
  # proxy = dataTableProxy('experiment_table')
  edit_info = input$experiment_table_cell_edit
  #i = edit_info$row
  #j = edit_info$col
  #v = edit_info$value
  proj_id <- state$data_scope$selected_experiment

  dt <- get_comp_prop(state, experiment_list_table)
  proj_seriess <- api_get_project_series(state, proj_id)
  #print(proj_seriess)

  # keep all fields except edited same
  edit_col <- colnames(proj_seriess)[[edit_info$col]]
  edited_val <- edit_info$value
  warning("before edited val:")
  print(paste(edited_val, class(edited_val), sep='    '))

  ser_id <- proj_seriess[edit_info$row, id]
  #data[, id := NULL]

  # if a datetime col edited, force parsing
  if (edit_col %in% state$config$DATETIME_COLS_HEADERS) {
    edited_val <- fastPOSIXct(edited_val)
  }
  data <- proj_seriess[id == ser_id, (edit_info$col) := (edited_val)]
  warning("after edited val:")
  print(edited_val)

  valid_columns <- grep("^\\.COMP_", colnames(data), value=TRUE, invert=TRUE)
  data <- dt[ ,colnames(dt) %in% valid_columns, with=FALSE]
  # pass API the state$exp_table colname of index j, PROJECT_ID of index i
  out <- api_put_project_series(state, proj_id, data=data, ser_id=ser_id)
  #out <- api_alter_proj_table(state, 'alter_cell', proj_id, data=data)

  # force API requery if table was actually modified upstream
  if(!is.null(out))
    state$updaters$api_fetch_time <- Sys.time()
  else{
    warning('Wrong entry in proj table edit? API failed to modify it.')
  }
}


project_series_table_add_row <- function(state, input){
    proj_id <- state$data_scope$selected_experiment
    user_inputs <- reactiveValues()
    #                    dev_id = "",
    #                    date_range = NULL,
    #                    start_time = NULL,
    #                    end_time = NULL )
    warning(paste("now user_inputs", user_inputs))

    #user_inputs$date_range <- {
    #    warning(paste("date range:", strftime(input$new_series_daterange)))
    #    shinyFeedback::feedbackDanger("new_series_daterange", any(!isTruthy(strftime(input$new_series_daterange))), "Must enter a start and an end date")
    #    req(input$new_series_daterange, cancelOutput=TRUE)
    #    input$new_series_daterange
    #}

    user_inputs$start_datetime <- {
        warning(paste("start:", input$new_series_start_datetime))

        start_datetime <- fastPOSIXct(input$new_series_start_datetime)
        # when improper string passed, fastPOSIXct returns NA
        shinyFeedback::feedbackDanger("new_series_start_datetime", !isTruthy(start_datetime), "Must be ISO datetime format")
        req(input$new_series_start_datetime, cancelOutput=TRUE)

        start_datetime
    }
    user_inputs$end_datetime <- {
        warning(paste("end:", input$new_series_end_datetime))

        end_datetime <- fastPOSIXct(input$new_series_end_datetime)
        # when improper string passed, fastPOSIXct returns NA
        shinyFeedback::feedbackDanger("new_series_end_datetime", !isTruthy(end_datetime), "Must be ISO datetime format")
        req(input$new_series_end_datetime, cancelOutput=TRUE)

        shinyFeedback::feedbackDanger("new_series_end_datetime", end_datetime < user_inputs$start_datetime, "Start must be before end")
        req(end_datetime > user_inputs$start_datetime, cancelOutput=TRUE)

        end_datetime
    }
    user_inputs$dev_id <- {
        #warning(paste("dev ID:", input$new_series_device))
        # 8 char hexadec str
        valid <- grepl('^[0-9A-Fa-f]{8}$', input$new_series_device)
        shinyFeedback::feedbackDanger("new_series_device", !valid, "Must be 8-character hexadecimal")
        req(valid, cancelOutput=TRUE)
        input$new_series_device
    }
    #warning("got all vals")

    #if (end_datetime < start_datetime)
    #    validate("Start must be before end")

    data = list(device = user_inputs$dev_id,
                start_datetime = user_inputs$start_datetime,
                end_datetime = user_inputs$end_datetime
    )
    writeLines("\nUser wants to add a series:")
    print(as.data.table(data))
    out <- api_put_project_series(state, proj_id, data=data)
    if(isTruthy(out))
        state$updaters$api_fetch_time <- Sys.time()
}

download_metadata_handler <- function(state, input){
downloadHandler(
    filename = function() {
      'metadata.csv'
    },
    content = function(file) {
      metadata = get_comp_prop(state, 'experiment_table')
      req(metadata)
      # exclude .HIDDEN cols
      metadata = metadata[, grep('^\\.',colnames(metadata), invert=T), with=FALSE]
      fwrite(metadata, file, row.names = FALSE)
    }
  )
}

download_data_handler <- function(state, input){
downloadHandler(
    filename = function() {
      'data.csv.gz'
    },
    content = function(file) {
      data = get_comp_prop(state, 'all_images_data')
      req(data)
      data = data[, grep('^\\.',colnames(data), invert=T), with=FALSE]
      fwrite(data, file, row.names = FALSE)
    }
  )
}




#todo
# new empty experiment (modal)
# delete experiment
# delete experiment_field
# delete experiment_column


# import experiment as csv
# share experiment with other user

# make is impossible to edit certain fields?
# rename columns
# compute special read_only fields on experiments:
#       number of matching images
#       first/last updated image

# #fixme save resources using  setDT()
# no experiment -> use date ranger
# allow tickbox in experiment table to unselect experiment that should map a field in the upstream experiment table
# create a runjs-base alert + console + logs to display things like nor allowed to creat variables that already exists
# compute previous and next for each image withing a plotted series. this way we can fetch,browse through series!!
