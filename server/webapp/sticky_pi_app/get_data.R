

compute_light_intensity <- function(et, ag, dg){
  #fixme
  1e6 / et

}

all_images_data <- function(state, input){
  dt <- get_comp_prop(state, images_in_scope)

  if(nrow(dt) < 1)
    req(FALSE)

  setkey(dt, device)
  # fwrite(dt, '/home/shiny/test.csv')
  dt <- dt[order(-rank(device), datetime)]
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

  dt[, previous_ID := previous_id(id), by=device]
  dt[, next_ID := next_id(id), by=device]

  dt[, temp := ifelse(temp > -300, temp, NA_real_)]
  dt[, hum := ifelse(hum > 0, hum, NA_real_)]
  dt[,is_dht_available := !is.na(temp)]

  
  dt[, temp:= na.approx(temp, x=datetime, rule=2)]
  dt[, hum:= na.approx(hum, x=datetime, rule=2)]
  dt[, lng := ifelse(lng < -1e+03, NA, lng)]
  dt[, lat := ifelse(lat < -1e+03, NA, lat)]
  dt[, light_intensity := compute_light_intensity(no_flash_exposure_time, no_flash_analog_gain,  no_flash_digital_gain)]

  if(!'n_objects' %in% colnames(dt)){
    n_insects_string = rep("", nrow(dt))
    }
  else{
    n_insects_string = sprintf("🦗🦟🐝🐞 %i<br>", dt[,n_objects])
  }
  dt[, .tooltip := sprintf('📷<span> %s <br>🗓 %s<br>🌡 %0.2f°C<br>💦 %0.2f%%RH<br>💡 %0.2f AU<br>%s</span>',
                          device,
                          as.character(datetime),
                          round(temp,2),
                          round(hum,2),
                          round(light_intensity,2),
                           n_insects_string
  )
  ]

  
  dt
}