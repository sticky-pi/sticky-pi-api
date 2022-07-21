library(lubridate)
library(data.table)
library(fasttime)

# for debugging
options(error = function() {
            traceback(2)
            if(!interactive())
                quit("no", status = 1, runLast = FALSE)
        })

source(file.path("project_management.R"))

######## Mock Data ########
# simple sinusoid generator
gen_time_series <- function(n_entries, scale_fac=500, offset=0, stdev=10) {
    series <- offset + scale_fac * (1 + sin(seq(-pi/5, by=(pi/6), length=n_entries)))
    series = series + rnorm(n_entries, sd=stdev)
    series
}

    ### Light Project ###
LIGHT_PROJ_DETAILS <- data.table(
                        name = "Light Trials",
                        description = "investigating effect of artificial lighting on insect communities",
                        notes = "light data from external intensity sensor"
                    )
put_project(LIGHT_PROJ_DETAILS)

START_DATETIMES <- fastPOSIXct(
                    c("2016-05-30 09:45",
                      "2017-02-10 17:30",
                      "2008-06-20 14:45",
                      "2022-01-21 11:47")
                    )
END_DATETIMES <- fastPOSIXct(
                    c("2016-07-10 09:45",
                      "2020-02-10 17:30",
                      "2009-06-20 14:45",
                      "2022-03-28 11:47")
                    )
LIGHT_EXPMT_ENTRIES <- init_entries_table()
LIGHT_EXPMT_ENTRIES <- data.table(
                series_id = 10:13,
                device_id = 7:10,
                # just POSIX time objects, value irrelevant
                start_datetime = START_DATETIMES,
                end_datetime = END_DATETIMES )
LIGHT_EXPMT_ENTRIES[, light_intensity := .(gen_time_series((.N)))]
#   ====================

CURRENT_USERNAME <- 'a'
CURRENT_USERNAME

    ### Simple Proj ###
SIMPLE_PROJ_DETAILS <- data.table(
                        name = "First Try",
                        description = "standard experiments with humidity, temp data",
                        notes = ""
                    )
put_project(SIMPLE_PROJ_DETAILS)
SIMPLE_PROJ_ENTRIES <- init_entries_table()
SIMPLE_PROJ_ENTRIES <- data.table(
                series_id = 7:2,
                device_id = 1:6,
                # just POSIX time objects, value irrelevant
                start_datetime = c(START_DATETIMES, rep(fastPOSIXct(2022-05-13), 2)),
                end_datetime = c(END_DATETIMES, rep(fastPOSIXct(2022-06-25), 2)) )
# add temp, humidity data
SIMPLE_PROJ_ENTRIES[, temperature := .(gen_time_series(.N, scale_fac=10, offset=30, stdev=8))]
SIMPLE_PROJ_ENTRIES[, humidity := .(gen_time_series(.N, scale_fac=8, offset=12, stdev=4))]
#   ====================

# save tables to file for future use
DATA_DIR_ROOT = "data-tables/"
write(jsonlite::toJSON(PERMISSIONS_TABLE), paste(DATA_DIR_ROOT, "permissions.json"))
fwrite(PERMISSIONS_TABLE, paste(DATA_DIR_ROOT, "permissions.csv"))

write(jsonlite::toJSON(PROJECTS_RECORD), paste(DATA_DIR_ROOT, "projects.json"))
fwrite(PROJECTS_RECORD, paste(DATA_DIR_ROOT, "projects.csv"))

write(jsonlite::toJSON(LIGHT_EXPMT_ENTRIES), paste(DATA_DIR_ROOT, "test_light_entries.json"))
fwrite(LIGHT_EXPMT_ENTRIES, paste(DATA_DIR_ROOT, "test_light_entries.csv"))
write(jsonlite::toJSON(SIMPLE_PROJ_ENTRIES), paste(DATA_DIR_ROOT, "test_entries.json"))
fwrite(SIMPLE_PROJ_ENTRIES, paste(DATA_DIR_ROOT, "test_entries.csv"))

writeLines("\n====== All Projects ======")
get_projects()
CURRENT_USERNAME <- 'b'
get_projects()

writeLines("\n====== All Project Permissions ======")
get_project_permissions('a')
get_project_permissions('b')
CURRENT_USERNAME <- 'a'
get_project_permissions('a')
get_project_permissions('b')

CURRENT_USERNAME <- 'b'

writeLines("\n====== Experiments Entries ======")
LIGHT_EXPMT_ENTRIES
SIMPLE_PROJ_ENTRIES

writeLines("\ndeleting project:")
PROJECTS_RECORD[1]
delete_project(PROJECTS_RECORD[1, project_id])

writeLines("\n====== All Project Permissions ======")
PERMISSIONS_TABLE

writeLines("\n====== All Projects ======")
writeLines(paste("\tUser ", CURRENT_USERNAME))
get_projects()

writeLines("all projects")
PROJECTS_RECORD

SIMPLE_PROJ_DETAILS <- data.table(
                        project_id = 1,
                        name = "Generic Campus Lawn",
                        description = "standard experiments with humidity, temp data",
                        notes = "over grass"
                    )
writeLines(paste("\ntrying to update project of ID ", PROJECTS_RECORD[1, project_id], " to "))
SIMPLE_PROJ_DETAILS
update_project(SIMPLE_PROJ_DETAILS)

writeLines("\n====== All Projects ======")
PROJECTS_RECORD

CURRENT_USERNAME <- 'a'
writeLines("\nswitched to user 1")
writeLines("\ntrying again")
update_project(SIMPLE_PROJ_DETAILS)

writeLines("\n====== All Projects ======")
PROJECTS_RECORD

writeLines("\nadding user 0 to this project")
put_project_permissions(list(
                       data.table( project_id = 1,
                             user_id = 'b',
                             level = 1 ))
                )
writeLines("\n====== All Project Permissions ======")
PERMISSIONS_TABLE

CURRENT_USERNAME <- 'b'
writeLines("\nswitched to user 0")
SIMPLE_PROJ_DETAILS[1, notes := "over grass, under a tree"]
writeLines("\ntrying again")
update_project(SIMPLE_PROJ_DETAILS)

writeLines("\n====== All Projects ======")
get_projects()

CURRENT_USERNAME <- 'b'
writeLines("\nswitched to user 1")
writeLines("\nmaking user 0 admin as well")
update_project_user(data.table( project_id = 1,
                                user_id = 'b',
                                level = 3 ))
writeLines("\n====== All Project Permissions ======")
PERMISSIONS_TABLE

writeLines("\nremoving user 0 from project 1")
delete_project_user(1, 'b')
get_project_permissions(1)

writeLines("\ndemoting self to read and write")
update_project_user(data.table( project_id = 1,
                                user_id = 'a',
                                level = 2 ))

writeLines("\nremoving self from project")
delete_project_user(1, 'a')
