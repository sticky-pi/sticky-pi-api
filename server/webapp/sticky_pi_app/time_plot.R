render_time_plot <- function(state, input){
  renderPlotly({
    dt <- get_comp_prop(state, all_image_data)
    if(nrow(dt) <1)
      return()
    
    rng_temp = range(dt[, TEMPERATURE])
    rng_hum = range(dt[, RELATIVE_HUMIDITY])
    
    b <- diff(rng_temp)/diff(rng_hum)
    a <- (rng_temp -  rng_hum * b)[1]


    bottom = min(dt[,TEMPERATURE] - 2)
    top = max(dt[,TEMPERATURE] + 2)
    
    pl <- ggplot(dt , aes(DATETIME, key=ID, text= .TOOLTIP, group=DEVICE_ID)) +
      geom_point(aes(y=TEMPERATURE), colour='red',  size=.5) +
      geom_line(aes(y=TEMPERATURE,x = DATETIME, group=DEVICE_ID, key=ID), colour='red', inherit.aes = F) +
      geom_line(aes(y=RELATIVE_HUMIDITY * b + a, x = DATETIME, group=DEVICE_ID, key=ID), colour='blue', inherit.aes = F) +
      geom_point(aes(y=RELATIVE_HUMIDITY * b + a, x = DATETIME, group=DEVICE_ID, key=ID), colour='blue', size=.5,inherit.aes = F)

     if(state$data_scope$selected_detector != "None"){
      rng_obj = range(na.omit(dt[, N_OBJECTS]))
      b_obj <- diff(rng_temp)/diff(rng_obj)
      a_obj <- (rng_temp -  rng_obj * b_obj)[1]
       pl <- pl +
         geom_line(aes(y=N_OBJECTS * b_obj + a_obj, x = DATETIME, group=DEVICE_ID, key=ID), colour='black', inherit.aes = F) +
         geom_point(aes(y=N_OBJECTS * b_obj + a_obj, x = DATETIME, group=DEVICE_ID, key=ID), colour='black', size=.5,inherit.aes = F)
     }

     pl <- pl +
      geom_point( aes(x=DATETIME, colour=light_intensity), dt, y=bottom, shape=15, inherit.aes = F) +
      facet_grid( DEVICE_ID ~ .) +
      scale_y_continuous(limits = c(bottom, top), sec.axis = sec_axis(~(. - a)/b, name = "Relative humidity [%]")) + 
      scale_x_datetime(name ="" )  +
      theme_classic() +
      guides(color = FALSE) +
      scale_colour_distiller(palette = "Spectral")
    
    pl
  
    height = 80 * nrow(dt[, .N, by=DEVICE_ID]) + 200
    p <- plotly::toWebGL(plotly::ggplotly(pl, tooltip=NA, dynamicTicks = TRUE)) %>%
      rangeslider(thickness= 50/ height, bgcolor='#bbb') %>%
      layout(hovermode = "x unified",
             height = height,
             margin = list(l=100),
             hoverlabel=list(bgcolor="#777"))
    
    
    onRender(p, readLines("www/hover.js"))
    }
  )}



make_modal_text <- function(state, data_row){
  
  datetime = format(data_row[,DATETIME], "%Y-%m-%d %H:%M:%S (%Z)", tz = state$user$selected_timezone)
  lat_lng = paste0(' ', data_row[,LATITUDE], ', ',data_row[,LONGITUDE])
  datetime_for_id = format(data_row[,DATETIME], "%Y-%m-%d_%H-%M-%S", tz = 'GMT')
  im_id = paste0(data_row[,DEVICE_ID], '.', datetime_for_id)
  n_insects = "Select a detector"
  if('N_OBJECTS' %in% colnames(data_row)){
        n_insects = data_row[,N_OBJECTS]
  }
  div( 
      div(class='row',
          div(class='col-md-4',span(icon('camera'),data_row[,DEVICE_ID])),
          div(class='col-md-4',span(icon('calendar'),datetime)),
          div(class='col-md-4',span(icon('user'),data_row[,UPLOADER])),
      ),
      div(class='row',
          div(class='col-md-4',span(icon('thermometer-half'),round(data_row[,TEMPERATURE], 2), 'C')),
          div(class='col-md-4',span(icon('shower'),round(data_row[,RELATIVE_HUMIDITY], 2), '%RH')),
          div(class='col-md-4',span(icon('lightbulb'),round(data_row[,light_intensity], 2), 'AU')),
      ),
      div(class='row',
          div(class='col-md-4',span(icon('map'),lat_lng)),
          div(class='col-md-3',span(icon('bug'),n_insects)),
          div(class='col-md-3',span(id='image_ID', im_id)),
          div(class='col-md-2',
            tags$button(onclick='shinyjs.copy_to_clipboard()',"Copy image ID",
                   icon('copy')))
      )
  )
}

populate_thumbail_show <- function(state, input, val=NULL){
  if(is.null(val))
    val <- input$on_clicked_thumbnail_button

  req(val$id)
  current_id <- as.numeric(val$id)
  type <- val$type
  dt <- get_comp_prop(state, 'all_image_data')

  if(type == 1){ # next
    id <- dt[ID==current_id, next_ID]
  } 
  else if(type == -1){ # next
    id <- dt[ID==current_id, previous_ID]
  } 
  else if(type==0){
    id <- current_id
    req(id)
  }
  else(
    stop('invalid type')
  )
  previous_img_id <- dt[ID==id, previous_ID]
  next_img_id <- dt[ID==id, next_ID]

  thumbnail_urls <- list(api_fetch_download_s3_thumbnail(state, previous_img_id),
                         api_fetch_download_s3_thumbnail(state, id),
                         api_fetch_download_s3_thumbnail(state, next_img_id))
  raw_url= api_fetch_download_s3(state, id)


  text = as.character(make_modal_text(state, dt[ID==id]))

   thumbnail_urls <- sapply(thumbnail_urls, function(x)ifelse(is.null(x), NA, x))
  if('ANNOTATION_JSON' %in% colnames(dt))
     annot = dt[ID==id, ANNOTATION_JSON]
  else
     annot = NA
  if('IMG_WIDTH' %in% colnames(dt))
     raw_img_width = dt[ID==id, IMG_WIDTH]
  else
     raw_img_width = 0
  js$click_thumbnail_button(id=id,  urls=thumbnail_urls, text=text,
                            raw_url=raw_url,
                            annotation_json= annot,
                            raw_img_width =raw_img_width)


}

on_clicked_time_plot <- function(state, input){
  req(input$on_clicked_plot)
  id = as.numeric(input$on_clicked_plot$key)
  dt <- get_comp_prop(state, 'all_image_data')

  o = tags$div(class = 'container-fluid',
            tags$div(id="thumbnail_images", class='row  vertical-align',
              tags$div( class= 'col-md-3', tags$img(id="previous_thumbnail", width="100%")),
               #fixme, here, we are making an assumption on the 4:3 aspect ratio, this can be checked from dt[,IMG_WIDTH] ...
              tags$div( class= 'col-md-6',  tags$a(id="current_thumbnail",tags$canvas(id="current_thumbnail", width=1200, height=900),
                                                    #
                                                    #  tags$img(id="current_thumbnail", width="100%")
                                                      #)
                                                    )
                                                    ),
              tags$div( class= 'col-md-3', tags$img(id="next_thumbnail",  width="100%")),
              ),
            
             tags$div(id="thumbnail_browsing_arrows", class='row',
                        
                 tags$div(class= 'col-md-4',tags$button(id="previous_thumbnail_button",class='thumbnail_action_button',
                                 icon("arrow-left"))),
                 tags$div(class= 'col-md-4',
                            tags$button(id="play_thumbnail_button", class='thumbnail_action_button',
                                        onclick="shinyjs.play_pause_thumbnail_button(true)",
                                        icon("play")),
                            tags$button(id="pause_thumbnail_button", class='thumbnail_action_button', style="display: none",
                                        onclick="shinyjs.play_pause_thumbnail_button(false)",
                                        icon("pause"))
                            ),

                tags$div(class= 'col-md-4', tags$button(id="next_thumbnail_button",class='thumbnail_action_button',
                                 icon("arrow-right")))
               ),
            div(id='thumbnail_modal_text')
            )
               


  showModal(modalDialog(o,
                        easyClose = TRUE,
                        footer = NULL
  ))
    # populate tiw current image (0)
    populate_thumbail_show(state, input, val=list(id=id, type=0))
}

render_time_plot_tooltip <- function(state, input){
  renderText({
    return('<div id="time_plot_tooltip"><img id="thumbnail_mini""><div id="custom_tooltip_text"></div> </div>')
  })
}

on_thumbnail_mini_to_fetch <- function(state, input){
  req(input$thumbnail_mini_to_fetch)
  i <- input$thumbnail_mini_to_fetch
  im_id <- as.numeric(i$key)
  if(im_id >= 0){
    row = get_comp_prop(state, "all_image_data")[ID==im_id]
    url <- api_fetch_download_s3_thumbnail_mini(state, im_id)
    js_to_run <- paste( "clearTimeout(hide_thumbnail_mini_timer);",
                       sprintf("$('img#thumbnail_mini').attr('src', '%s');", url),
                       sprintf("$('div#custom_tooltip_text').html('%s');", row[,.TOOLTIP]))
    runjs(js_to_run)

  }
  else{
    runjs("hide_thumbnail_mini_timer = setTimeout(function(){$('div#time_plot_tooltip').css({visibility:'hidden'});}, 500);")
  }
}

