is_admin <- function(proj_id, usrnm) {
    PERMISSIONS_TABLE[project_id == proj_id & username == usrnm, level] >= 3
}
is_member <- function(proj_id, usrnm) { 
    PERMISSIONS_TABLE[project_id == proj_id & username == usrnm, .N] > 0
}

# initial register user for project in permissions table
# takes a data.table row, {"username" : str, "project_id" : num, "level" : num 0 - 3}
put_project_user <- function(data) {
    proj_id <- data$project_id
    if (! (is_admin(proj_id, CURRENT_USERNAME))) {
        cat("you must be admin to add users to a project")
    }
    else if (is_member(proj_id, data$username)) {
        cat("user already added to project, current permission level ")
        print(PERMISSIONS_TABLE[project_id == proj_id & username == data$project_id, level])
    }
    else {
        PERMISSIONS_TABLE <<- rbind(PERMISSIONS_TABLE, data)
    }
}
# takes a list of user data lists/data.table rows as specified in put_project_user()
put_project_users <- function(user_datas) {
    lapply(user_datas, put_project_user)
}

# get corresponding entry in perm. table
get_project_users <- function(proj_id) {
    if (is_member(proj_id, CURRENT_USERNAME))
        PERMISSIONS_TABLE[project_id == proj_id]
}

update_project_user <- function(data) {
    to_admin <- (data$level >= 2)
    # check that >= 1 admin will remain
    if ((to_admin + PERMISSIONS_TABLE[project_id == data$project_id & username != data$username & level >= 2, .N]) > 0 &
        is_admin(data$project_id, CURRENT_USERNAME) &
        is_member(data$project_id, data$username))
    {
        PERMISSIONS_TABLE[project_id == data$project_id & username == data$username,
                          names(PERMISSIONS_TABLE) := data]
    }
    else {
        cat("user not part of project and/or no access to project and/or project doesn't exist")
    }
}

delete_project_user <- function(proj_id, usrnm) {
    # check that >= 1 admin will remain
    if ((PERMISSIONS_TABLE[project_id == proj_id & username != usrnm & level >= 2, .N]) > 0 &
        is_admin(proj_id, CURRENT_USERNAME) &
        is_member(proj_id, usrnm))
    {
        PERMISSIONS_TABLE <<- PERMISSIONS_TABLE[project_id == proj_id & username != usrnm]
    }
    else {
        cat("user not part of project and/or you are not permitted to remove members")
    }
}
