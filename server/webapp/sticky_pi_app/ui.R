header <- function(state){renderUI({
  req(state$user$is_logged_in)
  tags$li(
    a(icon("fa fa-sign-out"), "Logout",
          href="javascript:window.location.reload(true)"),
        class = "dropdown",
        style = "background-color: #eee !important; border: 0;
                font-weight: bold; margin:5px; padding: 10px;")
})}

side_panel <- function(state){renderUI({
    if (state$user$is_logged_in == TRUE ){
        # scope <- h2(sprintf("Scope:\n%i images\n%i devices", user$scope$n_images, user$scope$n_devices))
        # scope <- h2(sprintf("\n%i images in scope", length(state$data_scope$selected_image_ids)))
        data <- get_comp_prop(state, "images_in_scope") # fixme, canno tcall by deparsing...?
        scope <- h3(id='scope_title', sprintf(" %i", nrow(data)), br()," images in scope")
      # scope <- h2("images in scope")
      sidebarMenu(
        scope,
        tags$hr(),
        menuItem("Experiments", tabName = "experiments", icon = icon("flask")),
        menuItem("Images", tabName = "images", icon = icon("calendar-alt")),
        menuItem("Tuboids", tabName = "tuboids", icon = icon("map")),
        menuItem("Data", tabName = "data", icon = icon("table")),
        tags$hr(),
        downloadButton("download_data_handler", "Download data")
      )
    }
  })}

make_ui <- function(){
    header <- dashboardHeader( title = tags$a(href='https://doc.sticky-pi.com', target="blank_",
                                       tags$img(src='sticky_logo.png', width="100%", height="auto")),
                               uiOutput("header")
    )
    sidebar <- dashboardSidebar(uiOutput("sidebarpanel"))

    body <- dashboardBody(shinyjs::useShinyjs(),
                          shinyjs::extendShinyjs('script.js', functions='click_thumbnail_button'),
                          tags$head(tags$link(rel = "shortcut icon", href = "favicon.ico")),
                          tags$head(
                            tags$link(rel = "stylesheet", type = "text/css", href = "style.css")
                            ),
                          uiOutput("body"))
    dashboardPage(header, sidebar, body, skin = "blue", title="Sticky Pi Web App")
}


date_selector <- function(state){
    dates <-  state$data_scope$selected_dates
    o <- dateRangeInput("data_scope_dates", "Date range", start = dates[1], end = dates[2], min = NULL,
                       max = today()+1, format = "yyyy-mm-dd", startview = "month", weekstart = 0,
                       language = "en", separator = " to ", width = NULL)
    message <- "Scoping all devices in:"
    if(state$data_scope$selected_experiment > 0){
        o <- disabled(o)
        message <- "Unselect experiment to use date range"
    }
    div(h3(message),o)
}
experiment_tables_ui <- function(state){
#
#    if(state$data_scope$selected_experiment > 0){
#        exp_table <- column(6,
#            box(width = 12,
#            tags$h2('Experimental metadata'),
#            fluidRow(
#              column(3, tags$h4('New metavariable')),
#              column(3, textInput('experiment_new_col_name', "Name", value = "")),
#              column(3, selectInput('experiment_new_col_type', "Type", choices =
#                   list(
#                        "longitude (override)" = 'lng',
#                        "latitude (override)" = 'lat',
#                        "character" = 'char',
#                        "numeric" = 'num',
#                        "datetime" = 'datetime'
#                        ), selected='char'
#              )),
#
#              column(3, actionButton("experiment_table_add_column", "+"))
#            ),
#              DTOutput('experiment_table'),
#              actionButton("experiment_table_add_row", "Add row"),
#              downloadButton('download_metadata_handler', 'Download metadata')
#              ))
#        }
#        else{
#            exp_table = column(6 ,h2('Select and experiment'))
#        }
#
    exp_list_table <-
        column(6,
            box(width = 12,
                tags$h2('My experiments'),
                fluidRow(
                    column(5, h4('New Experiment')),
                    column(5, textInput('new_experiment_name', "Name", value = "")),
                    column(2, actionButton("create_experiment", "+"))
                ),
                DTOutput('experiment_list_table')
            )
    )

    fluidRow(
        #exp_table,
        exp_list_table
        )
     }

body <- function(state){
renderUI({
  state$data_scope$selected_experiment
  
    if (state$user$is_logged_in == TRUE ) {
      o <- tabItems(
        tabItem(tabName ="experiments", class = "active",
            fluidRow(
                column(2, actionButton('on_refresh_scope', icon('refresh'))),
                #column(5, uiOutput('available_annotators')),
                column(10, date_selector(state))),
            fluidRow(experiment_tables_ui(state)),
                ),
        tabItem(tabName ="images",
                fluidRow(
                  # box(width = 12,uiOutput('time_plot')),

                  box(width = 12, style='min-height:800px; overflow-y: scroll; position: relative',
                        selectInput("time_plot_colour_axis", "Variable displayed as colour",
                              list(`light intensity` = "light_intensity",
                                   `humidity` = "hum",
                                   `temperature` = "temp",
                                   `insect number` = "n_objects"
                                   )),
                      plotlyOutput('time_plot')
                  ),
                  htmlOutput('time_plot_tooltip_widget')
                ),
                # htmlOutput('thumbnail_mini')
                ),
        tabItem(tabName ="tuboids"
        ),
        tabItem(tabName ="data",
                fluidRow(
                  box(width = 12, dataTableOutput('all_images_data'))
                )
              )
      )
    }
    else {
      o <- login_ui()
    }
  o
  })
  
}
