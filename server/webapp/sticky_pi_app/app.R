rm(list=ls())
library(shiny)
library(shinydashboard)
library(DT)
library(shinyjs)
library(sodium)
library(RMariaDB)
library(httr)
library(lubridate)
library(data.table)
library(plotly)
library(ggplot2)
library(htmlwidgets)
library(fasttime)
library(zoo)
library(jsonlite)
library(gridExtra) # 
library(grid)
library(shinyBS)
# 

source("login.R")
source("experiment_scope.R")
source("get_data.R")
source("ui.R")
source("config.R")
source("shiny_helpers.R")
source('state.R')
source("time_plot.R")

server <- function(input, output, session) {
  config <- get_config()

  # make mock API calls and make mock data
  if(config$STICKY_PI_TESTING_RSHINY_USE_MOCK_API){
    warning("USING MOCK API CALLS")
    source("mock_api.R")
  } else{
    source("api.R")
  }
    
    state <- make_state(input, config)

    state <- set_comp_prop(state, experiment_table)
    state <- set_comp_prop(state, experiment_list_table)
    state <- set_comp_prop(state, images_in_scope)
    state <- set_comp_prop(state, all_images_data)

    observe({login_fun(state, input)})

    #observeEvent(input$experiment_table_cell_edit, experiment_table_alter_cell(state, input))
    #observeEvent(input$experiment_table_add_row, experiment_table_add_row(state, input))
    #observeEvent(input$experiment_table_add_column, experiment_table_add_column(state, input))
    #
    #observeEvent(input$create_experiment, experiment_list_table_add_row(state, input))


    #observeEvent(input$experiment_list_table_rows_selected, ignoreNULL = FALSE,{
    #  sel <- input$experiment_list_table_rows_selected
    #  persist_sel <- input$experiment_list_table_rows_selected
    #  if(is.null(sel))
    #    sel <- 0
    #  else{
    #    sel <- as.numeric(sel)
    #    # we want the ID of the selected experiment, not the row!
    #    dt <- get_comp_prop(state, experiment_list_table)
    #    sel <- dt[sel, EXPERIMENT_ID]
    #  }
    #  state$data_scope$selected_experiment_persist  <- isolate(sel)
    #  state$data_scope$selected_experiment  <- sel
    #
    #})

    observeEvent(input$thumbnail_mini_to_fetch, on_thumbnail_mini_to_fetch(state, input))
    observeEvent(input$on_clicked_plot, on_clicked_time_plot(state,input))
    observeEvent(input$on_clicked_thumbnail_button,populate_thumbail_show(state, input))
    observeEvent(input$on_refresh_scope,{state$updaters$api_fetch_time <- Sys.time()})
    #observeEvent(input$on_select_annotator,{state$data_scope$selected_detector <- input$on_select_annotator})

    ## in ui.R
    output$header <- header(state)
    output$sidebarpanel <- side_panel(state)
    output$body <- body(state)
    
    #output$experiment_list_table = render_experiment_list_table(state)
    #output$experiment_table =   render_experiment_table(state)

    output$all_imagess_data = DT::renderDataTable(get_comp_prop(state, all_image_data))
    output$time_plot = render_time_plot(state, input)
    
    output$time_plot_tooltip_widget <- render_time_plot_tooltip(state, input)
    #output$available_annotators <- render_available_annotators(state, input)
    #output$download_metadata_handler <-  download_metadata_handler(state, input)
    output$download_data_handler <-  download_data_handler(state, input)

}

ui <- make_ui()
shinyApp(ui = ui, server = server)

