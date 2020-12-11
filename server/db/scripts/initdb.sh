#!/bin/bash

function execute_sql() {
    echo $1
    mysql -h localhost -uroot -p${MYSQL_ROOT_PASSWORD} -e "$1"
}

function next_ip() {
    NEXT_IP=$(echo $1 | awk -F. '{ printf("%s.%s.%s.%d", $1, $2, $3, ($4 + 1) ); }')
    echo $NEXT_IP
}

if [ "${MYSQL_DATABASE}" != "" ]; then
    # grab NIC network device
    NET_DEVICE=$(ip route | grep default | grep -v tun | awk '{ print $5 }' | sed -z 's/\n//')
    echo "Container NET_DEVICE=${NET_DEVICE}"
    
    # get the current docker container IP address associated with NIC
    MYSQL_HOST_IP=$(ip route| grep $NET_DEVICE | grep -v default | grep src | awk '{ print $9 }' | sed -z 's/\n//')
    echo "Container IP=${MYSQL_HOST_IP}"
    echo "Executing with PROFILE='${PROFILE:-prod}' ..."
    
    # this is only for production
    if [ "${PROFILE}" != "dev" ]; then

        # grant the access for the user api in the next 10 container IP addresses 
        CURRENT_IP=$(next_ip "${MYSQL_HOST_IP}" )
        for i in `seq 1 ${CONTAINERS_AMOUNT:-10}`; 
        do
            execute_sql "CREATE USER '${MYSQL_API_USER}'@'${CURRENT_IP}' IDENTIFIED WITH mysql_native_password BY '${MYSQL_API_PASSWORD}';"
            execute_sql "GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_API_USER}'@'${CURRENT_IP}' WITH GRANT OPTION;"
            CURRENT_IP=$(next_ip "${CURRENT_IP}" )
        done
    
    else
        # valid only on development environment
        execute_sql "CREATE USER '${MYSQL_API_USER}'@'%' IDENTIFIED WITH mysql_native_password BY '${MYSQL_API_PASSWORD}';"
        execute_sql "GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_API_USER}'@'%' WITH GRANT OPTION;"
    
    fi
    # creating the reader user
    execute_sql "CREATE USER '${MYSQL_READER}'@'%' IDENTIFIED WITH mysql_native_password BY '${MYSQL_READER_PASSWORD}';"
    execute_sql "GRANT SELECT ON  \`${MYSQL_DATABASE}\`.* TO '${MYSQL_READER}'@'%' WITH GRANT OPTION;"
fi