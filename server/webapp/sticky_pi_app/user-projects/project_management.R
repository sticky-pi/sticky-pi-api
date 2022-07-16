library(lubridate)
library(data.table)
library(fasttime)

source(file.path("projects_table.R"))
source(file.path("permissions_table.R"))

CURRENT_USER_ID <- 0

####### non-API Functions #######
init_entries_table <- function() {
    data.table( series_id = numeric(0),
                device_id = numeric(0),
                # just POSIX time objects, value irrelevant
                start_datetime = .POSIXct(0)[0],
                end_datetime = .POSIXct(0)[0] )
}

#put_expmt_entry <- function(entries_table, series_id, dev_id, start_datetime, end_datetime) {
#    entries_table.rbind(list( series_id, dev_id, start_datetime, end_datetime ))
#}

# master projects table
PROJECTS_RECORD <- data.table(
                        project_id = numeric(0),
                        name = character(0),
                        description = character(0),
                        notes = character(0)
                     )
PERMISSIONS_TABLE <- data.table(
                        project_id = numeric(0),
                        username = character(0),
                        level = numeric(0)
                     )
