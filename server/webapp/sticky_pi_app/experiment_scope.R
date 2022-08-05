empty_exp_table <- {data.table(ID=numeric(0),
                  DEVICE_ID=character(0),
                  START_DATETIME=POSIXct(0),
                  END_DATETIME=POSIXct(0))}

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

handle_new_experiment_metavariable <- function(dt,  name, code){
  
  if(name %in% colnames(dt)){
    warning('Column already exists')
    return(NULL)
  }
  
  map <- list("lng"= function(name)list("LONGITUDE"=  "DECIMAL(11, 8)"),
              "lat"= function(name)list("LATITUDE"=  "DECIMAL(11, 8)"),
              "char"= function(name){
                out = list()
                if(check_var_name(name)){
                  out[[name]] <- "CHAR(64)"
                  return(out)
                }},
              "datetime"= function(name){
                out = list()
                if(check_var_name(name)){
                  out[[name]] <- "DATETIME"
                  return(out)
                }},
              
              "num"= function(name){
                out = list()
                if(check_var_name(name)){
                  out[[name]] <- "DOUBLE"
                  return(out)
                }})
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
    #fixme
    images <- api_get_images_id_for_experiment(state, sel)
    
  }
  images
}

datatable_options <- function(dt, excluded_names="project_id", header_names=NULL){
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

#LEVEL_TO_ROLE_MAP = c()
#LEVEL_TO_ROLE_MAP['1'] = "read-only"
#LEVEL_TO_ROLE_MAP['2'] = "read, write"
#LEVEL_TO_ROLE_MAP['3'] = "all, admin"
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

  #writeLines("\nexperiment_list_table():")
  #print(projs_table)
  
  all_permissions_table <- api_get_project_permissions(state, '%')
  #print(all_permissions_table)

  # first add a column, current user's permission level for each project
  # convert to role in render_...()
  curr_user_perms <- all_permissions_table[username == state$config$STICKY_PI_TESTING_USER, .(project_id, level)]
  #writeLines(" ")
  #print(curr_user_perms)

  # thanks to [merging in another table's column on common key](https://stackoverflow.com/a/34600831)
  # and [get data.table to use variable for name of **new** column]
  projs_table[curr_user_perms, on = "project_id", level := i.level]
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
  print("rendering")
  DT::renderDataTable({

    dt <- get_comp_prop(state, experiment_list_table)[, !"level"]
    # TODO: ensure experiment_list_table cannot be modified in between
    # *copy* perm. level col to preserve levels when converting to display text
    role_col <- get_comp_prop(state, experiment_list_table)[, .(project_id, role = permission_levels_to_roles(state, level))]
    print(role_col)
    role_header <- state$config$PERMISSIONS_TABLE_HEADERS[["level"]]
    dt[role_col, on = "project_id", c(role_header) := i.role]

    #exp_id <- state$data_scope$selected_experiment_persist
    #row <- which(dt[ ,EXPERIMENT_ID == exp_id])
    #if(length(row) == 1){
    #  state$data_scope$selected_image_ids <- unlist(dt[EXPERIMENT_ID == exp_id, .HIDDEN_image_ids])
    #}
    #else{
    #  row <- NULL
    #}
    # column headers renamed/"prettied" in fill_replace_colnames
    datatable = DT::datatable(dt,
                              selection = list(mode='single', selected = row),
                              editable = TRUE,
                              colnames = fill_replace_colnames(colnames(dt), state$config$PROJECTS_LIST_HEADERS),
                              options = datatable_options(dt,
                                                          excluded_names=c("project_id")
                                                         )
                              )
                               
                               
  })
}
show_create_project_form <- function(state, input, failed=FALSE) {
    # create/submit button in project_modal_ui() triggers experiment_list_table_add_row()
    showModal(project_modal_ui(state, failed))
}
experiment_list_table_add_row <- function(state, input){
    writeLines("\nuser submitted create project form")
    # should have been inputted by user in modal form
    #req(input$new_project_name)
    #req(input$new_project_description)
    #req(input$new_project_notes)
    print(input$new_project_name)
    if (is.null(input$new_project_name) || input$new_project_name == "") {
        print("no name entered")
        show_create_project_form(state, input, failed=TRUE)
    } else {
        name <- input$new_project_name
        description <- input$new_project_description
        notes <- input$new_project_notes

        data = list(name=name, description=description, notes=notes)
        writeLines("\nUser wants to create a project:")
        print(as.data.table(data))
        api_put_project(state, data)
        state$updaters$api_fetch_time <- Sys.time()

        removeModal()
    }
}

experiment_table <- function(state, input){
  dt_exp_list <- get_comp_prop(state, experiment_list_table)

  proj_id <- state$data_scope$selected_experiment
  if(proj_id<1)
    return(data.table())

  dt <- api_get_project_series(state, proj_id)
  #print( paste("Project", proj_id))
  #print(dt)
  # if no matching entries table, make a blank one
  if(is.null(dt))
    return(new_entries_table())
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
  print("rendering entries")
  DT::renderDataTable({
    # isn't \/ dt reactive?
    dt <- get_comp_prop(state, experiment_table)
    print(dt)
    # proj_id <- state$data_scope$selected_experiment
    # if(proj_id > 0){
    #   state$data_scope$selected_image_ids <- unlist(dt[EXPERIMENT_ID == proj_id, .HIDDEN_image_ids])
    # }
    # else{
    #   proj_id <- NULL
    # }
    datetime_colinds = c( match("start_datetime", colnames(dt)), match("end_datetime", colnames(dt)))

    datatable = DT::datatable(dt,
                              selection = list(mode='single'), #, selected = proj_id),
                              editable = TRUE,
                              colnames = fill_replace_colnames(colnames(dt), state$config$PROJECT_SERIES_HEADERS),
                              options = datatable_options(dt,
                                                          excluded_names=c("series_id", "device_id")
                                                          )
                            ) %>% formatDate( datetime_colinds,
                                          method = "toUTCString"
    )
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

#experiment_table_add_column <- function(state, input){
#  req(state$data_scope$selected_experiment != 0)
#    req(input$experiment_new_col_type)
#  req(input$experiment_new_col_type)
#  name <- input$experiment_new_col_name
#  type <- input$experiment_new_col_type
#
#  experiment_id <-state$data_scope$selected_experiment
#
#  data <- handle_new_experiment_metavariable(get_comp_prop(state, experiment_table), name, type)
#  if(!is.null(data)){
#    out <- api_alter_experiment_table(state,'add_column', experiment_id, data=data)
#    if(!is.null(out))
#      state$updaters$api_fetch_time <- Sys.time()
#  }
#
#}
#

#project_series_table_add_row <- function(state, input){
#  proj_id <-state$data_scope$selected_experiment
#  
#  out <- api_put_project_series(state, proj_id, data=list())
#  if(isTruthy(out))
#    state$updaters$api_fetch_time <- Sys.time()
#}
#
#
#experiment_table_alter_cell <- function(state, input){
#  req(state$data_scope$selected_experiment != 0)
#  req(input$experiment_table_cell_edit)
#  # proxy = dataTableProxy('experiment_table')
#  info = input$experiment_table_cell_edit
#  i = info$row
#  j = info$col
#  v = info$value
#  experiment_id <- state$data_scope$selected_experiment
#
#  dt <- get_comp_prop(state, experiment_table)
#
#  alteration <- list()
#  alteration[[colnames(dt)[j]]] = v
#  data = list(ID=dt[i,ID], alteration=alteration)
#  out <- api_alter_experiment_table(state, 'alter_cell', experiment_id, data=data)
#
#  # force API requery if table was actually modified upstream
#  if(!is.null(out))
#    state$updaters$api_fetch_time <- Sys.time()
#  else{
#    warning('Wrong entry in experiment table cell? API failed to modify it.')
#  }
#
#}
#

project_series_table_add_row <- function(state, input){
    proj_id <-state$data_scope$selected_experiment
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
        datestr <- strftime(input$new_series_start_date)
        timestr <- strftime(input$new_series_start_time, "%T")
        warning(paste("start:", datestr))
        warning(paste("start:", timestr))

        shinyFeedback::feedbackDanger("new_series_start_date", !isTruthy(datestr), "Required")
        req(input$new_series_start_date, cancelOutput=TRUE)
        shinyFeedback::feedbackDanger("new_series_start_time", !isTruthy(timestr), "Required")
        req(input$new_series_start_time, cancelOutput=TRUE)

        fastPOSIXct(ymd(datestr) + hms(timestr), tz="UTC")
    }
    user_inputs$end_datetime <- {
        datestr <- strftime(input$new_series_end_date)
        timestr <- strftime(input$new_series_end_time, "%T")
        warning(paste("end:", strftime(input$new_series_end_date)))
        warning(paste("end:", strftime(input$new_series_end_time, "%T")))

        shinyFeedback::feedbackDanger("new_series_end_date", !isTruthy(datestr), "Required")
        req(input$new_series_end_date, cancelOutput=TRUE)
        shinyFeedback::feedbackDanger("new_series_end_time", !isTruthy(timestr), "Required")
        req(input$new_series_end_time, cancelOutput=TRUE)

        end_datetime <- ymd(datestr) + hms(timestr)
        shinyFeedback::feedbackDanger("new_series_end_time", end_datetime < user_inputs$start_datetime, "Start must be before end")
        
        fastPOSIXct(end_datetime, tz="UTC")
    }
    user_inputs$dev_id <- {
        #warning(paste("dev ID:", input$new_series_device_id))
        # 8 char hexadec str
        valid <- grepl('^[0-9A-Fa-f]{8}$', input$new_series_device_id)
        shinyFeedback::feedbackDanger("new_series_device_id", !valid, "Must be 8-character hexadecimal")
        req(valid, cancelOutput=TRUE)
        input$new_series_device_id
    }
    #warning("got all vals")

    #if (end_datetime < start_datetime)
    #    validate("Start must be before end")

    data = list(device_id = user_inputs$dev_id,
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
