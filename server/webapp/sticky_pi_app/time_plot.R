render_time_plot <- function(state, input){
  renderPlotly({
    dt <- get_comp_prop(state, all_images_data)

    if(nrow(dt) <1)
      return()
    pl <- ggplot(dt , aes(x=datetime, y=device, text= .tooltip, group=device, key=id)) +
      geom_point(aes_string(colour=input$time_plot_colour_axis),  size=3, shape=15) +
      scale_colour_distiller(palette = "Spectral")
    height = 30 * nrow(dt[, .N, by=device]) + 60
    p <- plotly::toWebGL(plotly::ggplotly(pl, tooltip=NA, dynamicTicks = TRUE)) %>%
      rangeslider(thickness= 50/ height, bgcolor='#bbb') %>%
      layout(hovermode = "closest",
#              height = height,
             margin = list(l=100),
             hoverlabel=list(bgcolor="#777"))


    onRender(p, readLines("www/hover.js"))
    }
  )}



make_modal_text <- function(state, data_row){
  
  datetime = format(data_row[,datetime], "%Y-%m-%d %H:%M:%S (%Z)", tz = state$user$selected_timezone)
  lat_lng = paste0(' ', data_row[,lat], ', ',data_row[,lng])
  datetime_for_id = format(data_row[,datetime], DATETIME_FORMAT, tz = 'GMT')
  im_id = paste0(data_row[,device], '.', datetime_for_id)
  n_insects = "Select a detector"
  if('n_objects' %in% colnames(data_row)){
        n_insects = data_row[,n_objects]
  }
  div( 
      div(class='row',
          div(class='col-md-4',span(icon('camera'),data_row[,device])),
          div(class='col-md-4',span(icon('calendar'),datetime)),
          div(class='col-md-4',span(icon('user'),data_row[,api_user])),
      ),
      div(class='row',
          div(class='col-md-4',span(icon('thermometer-half'),round(data_row[,temp], 2), 'C')),
          div(class='col-md-4',span(icon('shower'),round(data_row[,hum], 2), '%RH')),
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
  dt <- get_comp_prop(state, 'all_images_data')

  if(type == 1){ # next
    id_clicked <- dt[id==current_id, next_ID]
  } 
  else if(type == -1){ # next
    id_clicked <- dt[id==current_id, previous_ID]
  } 
  else if(type==0){
    id_clicked <- current_id
    req(id_clicked)
  }
  else(
    stop('invalid type')
  )
  previous_img_id <- dt[id==current_id, previous_ID]
  next_img_id <- dt[id==current_id, next_ID]

  thumbnails <- api_fetch_download_s3(state, c(previous_img_id, current_id, next_img_id))
  thumbnail_urls = as.list(thumbnails$url)
  raw_url= api_fetch_download_s3(state, current_id, what_images = 'image', what_annotations = 'data')$url

  text = as.character(make_modal_text(state, dt[id==current_id]))

  thumbnail_urls <- sapply(thumbnail_urls, function(x)ifelse(is.null(x), NA, x))

  if(!is.na(thumbnails[ id == current_id, json])){
    annot = thumbnails[ id == current_id, json]
  }
  else
     annot = NA

   if('width' %in% colnames(dt))
     raw_img_width = dt[id==current_id, width]
  else
     raw_img_width = 0

  js$click_thumbnail_button(id=id_clicked,  urls=thumbnail_urls, text=text,
                            raw_url=raw_url,
                            annotation_json= annot,
                            raw_img_width =raw_img_width)


}

on_clicked_time_plot <- function(state, input){
  req(input$on_clicked_plot)
  id = as.numeric(input$on_clicked_plot$key)
  dt <- get_comp_prop(state, 'all_images_data')
  o = tags$div(class = 'container-fluid',
            tags$div(id="thumbnail_images", class='row  vertical-align',
              tags$div( class= 'col-md-3', tags$img(id="previous_thumbnail", width="100%")),
               #fixme, here, we are making an assumption on the 4:3 aspect ratio, this can be checked from dt[,IMG_WIDTH] ...
              tags$div( class= 'col-md-6',  tags$a(id="current_thumbnail",tags$canvas(id="current_thumbnail", width=1200, height=900),
                                                   target="_blank"
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
    row = get_comp_prop(state, "all_images_data")[id==im_id]
    url <- row[,url]
    js_to_run <- paste( "clearTimeout(hide_thumbnail_mini_timer);",
                       sprintf("$('img#thumbnail_mini').attr('src', '%s');", url),
                       sprintf("$('div#custom_tooltip_text').html('%s');", row[,.tooltip]))
    runjs(js_to_run)

  }
  else{
    runjs("hide_thumbnail_mini_timer = setTimeout(function(){$('div#time_plot_tooltip').css({visibility:'hidden'});}, 500);")
  }
}

