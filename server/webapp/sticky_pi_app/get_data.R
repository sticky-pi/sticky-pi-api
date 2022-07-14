

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

  dt[, temp := ifelse(between(temp, -50, 150), temp, NA_real_)]
  dt[, hum := ifelse(between(hum, 0, 100), hum, NA_real_)]

    dt[, temp := ifelse(temp ==0.0 & hum == 0.0 ,  NA_real_, temp)]
    dt[, hum := ifelse(temp ==0.0 & hum == 0.0 ,  NA_real_, hum)]

  dt[,is_dht_available := !is.na(temp)]

  
  dt[, temp:= na.approx(temp, x=datetime, rule=2)]
  dt[, hum:= na.approx(hum, x=datetime, rule=2)]
  dt[, lng := ifelse(lng < -1e+03, NA, lng)]
  dt[, lat := ifelse(lat < -1e+03, NA, lat)]
  dt[, light_intensity := lum]

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
