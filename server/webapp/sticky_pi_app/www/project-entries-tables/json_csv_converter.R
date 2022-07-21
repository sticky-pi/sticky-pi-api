library(jsonlite)
library(data.table)
library(tools)

args <- commandArgs(trailingOnly = TRUE)

print(paste( "reading from", args[1]))

# JSON --> CSV
if (file_ext(args[1]) == "json" && file_ext(args[2]) != "csv") {
    data <- fromJSON(args[1])
    fwrite(data, args[2])
# CSV --> JSON
} else if (file_ext(args[1]) == "csv" && file_ext(args[2]) == "json") {
    data <- fread(args[1])
    write(toJSON(data), args[2])
} else {
    stop("one of input(first) or output(second) file specified must be a JSON, the other a CSV")
}
print(data)
writeLines("\n")
print(paste( "wrote to", args[2]))
