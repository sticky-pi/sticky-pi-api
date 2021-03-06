

login_ui <- function(){
  # log on press enter
    js <- '
$(document).on("keyup", function(e) {
  if(e.keyCode == 13){
    Shiny.onInputChange("login", Math.round((new Date()).getTime() / 1000));
  }
});
'
    div(id = "loginpage",
     style = "width: 500px; max-width: 100%; margin: 0 auto; padding: 20px;",
    tags$script(js),
    wellPanel(
     tags$h2("LOG IN", class = "text-center", style = "padding-top: 0;color:#333; font-weight:600;"),
     textInput("userName", placeholder="Username", label = tagList(icon("user"), "Username")),
     passwordInput("passwd", placeholder="Password", label = tagList(icon("unlock-alt"), "Password")),
     br(),
     div(
       style = "text-align: center;",
       list(
         actionButton("login",
                    "SIGN IN",
                    style = "color: white; background-color:#3c8dbc;padding: 10px 15px; width: 150px; cursor: pointer;font-size: 18px; font-weight: 600;"),
         shinyjs::hidden(
           div(id = "nomatch",
               tags$p("Incorrect username or password!",
                      style = "color: red; font-weight: 600;
                              padding-top: 5px;font-size:16px;",
                      class = "text-center")))
       )
     )
     )
    )
}

login_fun <- function(state, input){
  is_logged_in <- state$user$is_logged_in
  no_password_test  <- state$config$STICKY_PI_TESTING_RSHINY_BYPASS_LOGGIN
  
        if (is_logged_in == FALSE) {
          # this is when running without a container for instance. no db, so no password
          if(no_password_test){
            state$user$is_logged_in <- TRUE
            state$user$username <- "MOCK USER"
            }
            
          # if STICKY_PI_TESTING_USER is defined at runtime of container, it logs in directly
            else if(state$config$STICKY_PI_TESTING_RSHINY_AUTOLOGIN){
                token <- api_verify_passwd(state, state$config$STICKY_PI_TESTING_USER, state$config$STICKY_PI_TESTING_PASSWORD)
                if(token != ""){
                  state$user$auth_token <- token
                  state$user$is_logged_in <- TRUE
                  state$user$username <- state$config$STICKY_PI_TESTING_USER
                  
                }
              }

          else if (!is.null(input$login)) {
            if (input$login > 0) {
                Username <- isolate(input$userName)
                Password <- isolate(input$passwd)
                token <- api_verify_passwd(state,Username, Password)
                
                if(token != ""){
                  state$user$auth_token <- token
                  state$user$is_logged_in <- TRUE
                  state$user$username <- Username
                  
                }
            else{
              shinyjs::toggle(id = "nomatch", anim = TRUE, time = 1, animType = "fade")
              shinyjs::delay(3000, shinyjs::toggle(id = "nomatch", anim = TRUE, time = 1, animType = "fade"))
            }
            }
          }
        }
    }