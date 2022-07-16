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

datatable_options <- function(d, excluded_names="ID"){
  cname <- colnames(d)
  hidden <- c(grep('^\\.HIDDEN.*$',cname), which(cname  %in% excluded_names))
  # hidden <- numeric(0)
  list(scrollX=TRUE, columnDefs = list(list(visible=FALSE,
                                            targets=hidden)))
}
#
experiment_list_table <- function(state, input){
  req(state$updaters$api_fetch_time)
  projs_table <- api_get_projects(state)
  req(projs_table)

  print(projs_table)
  projs_table
#
#  users_table <- api_get_users(state)
#  dt <- dt_users[dt, on='USER_ID']
#  setnames(dt, c('USERNAME')
#           ,c('OWNER'))
#  dt[, PERMISSION := paste(ifelse(CAN_ADMIN, "A", ""),
#                           ifelse(CAN_WRITE, "W", ""),
#                           ifelse(CAN_READ, "R", ""))
#     ]
#  dt <- dt[, .(EXPERIMENT_ID, NAME, OWNER, TIME_CREATED, PERMISSION,NOTES)]
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

    dt <- get_comp_prop(state, experiment_list_table)
    #exp_id <- state$data_scope$selected_experiment_persist
    #row <- which(dt[ ,EXPERIMENT_ID == exp_id])
    #if(length(row) == 1){
    #  state$data_scope$selected_image_ids <- unlist(dt[EXPERIMENT_ID == exp_id, .HIDDEN_image_ids])
    #}
    #else{
    #  row <- NULL
    #}

    datatable = DT::datatable(dt,
                              selection = list(mode='single', selected = row),
                              editable = TRUE,
                              options = datatable_options(dt,
                                                          excluded_names=c("project_id")
                                                         )
                              )
  })
}
#
#experiment_table <- function(state, input){
#
#  dt_exp_list <- get_comp_prop(state, experiment_list_table)
#
#  row <- state$data_scope$selected_experiment
#  if(row<1)
#    return(data.table())
#
#  experiment_id <- row
#
#  dt <- api_get_experiment(state, experiment_id)
#  if(is.null(dt))
#    return(empty_exp_table)
#
#  # we fetch all ID for each experiment entry
#
#  l <- lapply(dt[, ID],function(id){
#    out <- api_get_images_id_for_experiment(state, row_id=id,experiment_id=experiment_id)
#
#    if(is.null(out) | length(out) < 1)
#      return(NULL)
#
#    out <- data.table(ID = id, .HIDDEN_image_ids=out)
#    # warning(paste(id, length(unlist(out))))
#    out
#  }
#  )
#
#  dd <- rbindlist(l)
#  if(nrow(dd) < 1)
#    return(empty_exp_table) # fixme. should be populated with the default
#
#  dd[, .COMP_N_MATCHES := length(unlist(.HIDDEN_image_ids)), by=ID]
#  dt <- dd[dt, on="ID"]
#}
#
#render_experiment_table<- function(state){
#  DT::renderDataTable({
#
#    dt <- get_comp_prop(state, experiment_table)
#    # row <- state$data_scope$selected_experiment
#    # if(row > 0){
#    #   state$data_scope$selected_image_ids <- unlist(dt[EXPERIMENT_ID == row, .HIDDEN_image_ids])
#    # }
#    # else{
#    #   row <- NULL
#    # }
#    datatable = DT::datatable(dt,
#                              selection = list(mode='single'), #, selected = row),
#                              editable = TRUE,
#                              options = datatable_options(dt,
#                                                          excluded_names=c("ID"))
#    )
#  })
#}
#

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
#experiment_table_add_row <- function(state, input){
#  experiment_id <-state$data_scope$selected_experiment
#  out <- api_alter_experiment_table(state,'add_row', experiment_id, data=list())
#  if(isTruthy(out))
#    state$updaters$api_fetch_time <- Sys.time()
#
#
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
#experiment_list_table_add_row <- function(state, input){
#  req(input$new_experiment_name)
#  name <- input$new_experiment_name
#  data = list(name=name)
#  api_alter_experiment_list_table(state, action='add_row', data=data)
#  state$updaters$api_fetch_time <- Sys.time()
#
#}

#download_metadata_handler <- function(state, input){
#downloadHandler(
#    filename = function() {
#      'metadata.csv'
#    },
#    content = function(file) {
#      metadata = get_comp_prop(state, 'experiment_table')
#      req(metadata)
#      metadata = metadata[, grep('^\\.',colnames(metadata), invert=T), with=FALSE]
#      fwrite(metadata, file, row.names = FALSE)
#    }
#  )
#}
#
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
