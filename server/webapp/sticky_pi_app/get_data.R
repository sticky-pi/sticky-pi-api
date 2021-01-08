

compute_light_intensity <- function(et, bv, iso){
  log10(1+bv)/et
}

all_image_data <- function(state, input){
  sel_ids <- get_comp_prop(state, image_ids_in_scope)
  dt <- api_fetch_image_data_for_ids(state, sel_ids)
  if(nrow(dt) < 1)
    req(FALSE)
  
  setkey(dt, DEVICE_ID)
  # fwrite(dt, '/home/shiny/test.csv')
  dt <- dt[order(-rank(DEVICE_ID), DATETIME)]
  previous_id <- function(ids){
      if(length(ids) == 1)
        return(NA_integer_)
      c(NA_integer_, ids[1:length(ids)-1])
  }
    next_id <- function(ids){
        if(length(ids) == 1)
            return(NA_integer_)
        c(ids[2:length(ids)], NA_integer_)
    }

  dt[, previous_ID := previous_id(ID), by=DEVICE_ID]
  dt[, next_ID := next_id(ID), by=DEVICE_ID]

  dt[, TEMPERATURE := ifelse(TEMPERATURE > -300, TEMPERATURE, NA_real_)]
  dt[, RELATIVE_HUMIDITY := ifelse(RELATIVE_HUMIDITY > 0, RELATIVE_HUMIDITY, NA_real_)]
  dt[,is_dht_available := !is.na(TEMPERATURE)]
  
  dt[, TEMPERATURE:= na.approx(TEMPERATURE, x=DATETIME, rule=2)]
  dt[, RELATIVE_HUMIDITY:= na.approx(RELATIVE_HUMIDITY, x=DATETIME, rule=2)]
  dt[, LONGITUDE := ifelse(LONGITUDE < -1e+03, NA, LONGITUDE)]
  dt[, LATITUDE := ifelse(LATITUDE < -1e+03, NA, LATITUDE)]
  dt[, light_intensity := compute_light_intensity(PREVIEW_EXPOSURE_TIME, PREVIEW_BRIGHTNESS_VALUE, PREVIEW_ISO)]

  if(!'N_OBJECTS' %in% colnames(dt)){
    n_insects_string = rep("", nrow(dt))
    }
  else{
    n_insects_string = sprintf("🦗🦟🐝🐞 %i<br>", dt[,N_OBJECTS])
  }
  dt[, .TOOLTIP := sprintf('📷<span> %s <br>🗓 %s<br>🌡 %0.2f°C<br>💦 %0.2f%%RH<br>💡 %0.2f AU<br>%s</span>',
                          DEVICE_ID,
                          as.character(DATETIME),
                          round(TEMPERATURE,2),
                          round(RELATIVE_HUMIDITY,2),
                          round(light_intensity,2),
                           n_insects_string
  )
  ]

  
  dt
}