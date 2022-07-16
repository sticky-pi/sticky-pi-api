

set_comp_prop <- function(state, foo){
  #fixme won't work for anonymouse methods etc
  method_name <- deparse(substitute(foo))
  rct <- reactive({
    foo(state, state[["_input_"]])
    #TODO: how /\ above work when foo == api_get_images?
  })
  
  print(method_name)
  state[["_computed_props_"]][[method_name]] <- rct
  state
  
}

get_comp_prop <- function(state, prop_name){
  
  if(!is.character(prop_name))
    prop_name <- deparse(substitute(prop_name))
  # a react function stored in the state
  react <- state[["_computed_props_"]][[prop_name]]
  if(is.null(react))
    stop(sprintf("Could not find computed pro: %s\n props are: %s", prop_name, paste(names(state[["_computed_props_"]]))))
  react()
  
}
