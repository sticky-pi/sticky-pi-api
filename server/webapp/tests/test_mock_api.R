library(shiny)
library(data.table)
library(fasttime)

# go to source directory
setwd("../sticky_pi_app")
source("mock_api.R")
# #PLS work
state <- list(config = list(STICKY_PI_TESTING_USER = "testing"))

# for debugging
traceback()

test_api_delete_project_series <- function(state, test_datas) {
    warning(paste("initial series of project of ID", test_datas[[1]][["project_id"]]))
    print(api_get_project_series(state, test_datas[[1]][["project_id"]]))
    warning("removing:")
    print(api_delete_project_series(state, test_datas))
    warning("all project series now:")
    print(api_get_project_series(state, test_datas[[1]][["project_id"]]))
}

del_test_datas <- list(
                     list(project_id = 2, id = 3)
)
test_api_delete_project_series(state, del_test_datas)
