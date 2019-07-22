#!/bin/bash

Installer_Apache(){
	echo -e "\e[32mInstallation d’Apache\e[0m"
	DEBIAN_FRONTEND=noninteractive apt-get install -y apache2
	echo -e "\e[32mApache utilise le répertoire /var/www/html comme racine pour votre site\e[0m"
	chown -R $USER:www-data /var/www/html/
	chmod -R 770 /var/www/html/
	sleep 5
}

Installer_MySQL(){
	echo -e "\e[32mInstallation de MySQL-server MySQL-client \e[0m"
	apt-get install mysql-server mysql-client -y
	echo -e "\e[33mFait\e[0m"
	sleep 5
	# If /root/.my.cnf exists then it won't ask for root password
	if [ -f /root/.my.cnf ]; then
		USER='yapo'
		PASSWORD='pipi'
		RESULT=`mysql -u $USER -p$PASSWORD --skip-column-names -e "SHOW DATABASES LIKE 'rpi'"`
		if [ "$RESULT" == "rpi" ]; then
		    echo -e "\e[31mDatabase exist\e[0m"
	       	    sleep 5
		else
		    echo "Database does not exist"
		    echo "Please enter the NAME of the new database! (example: database1)"
		    read dbname
		    echo "Please enter the database CHARACTER SET! (example: latin1, utf8, ...)"
		    #read charset
		    charset=utf8
		    echo "Creating new database..."
		    mysql -e "CREATE DATABASE ${dbname} /*\!40100 DEFAULT CHARACTER SET ${charset} */;"
		    echo "Database successfully created!"
		    echo "Showing existing databases..."
		    mysql -e "show databases;"
		    echo ""
		    echo "Please enter the NAME of the new database user! (example: user1)"
		    read username
		    echo "Please enter the PASSWORD for the new database user!"
		    read userpass
		    echo "Creating new user..."
		    mysql -e "CREATE USER ${username}@localhost IDENTIFIED BY '${userpass}';"
		    echo "User successfully created!"
		    echo ""
		    echo "Granting ALL privileges on ${dbname} to ${username}!"
		    mysql -e "GRANT ALL PRIVILEGES ON ${dbname}.* TO '${username}'@'localhost';"
		    mysql -e "FLUSH PRIVILEGES;"
		    echo "You're good now :)"
		    sleep 5
		fi
	# If /root/.my.cnf doesn't exist then it'll ask for root password	
	else
		rootpasswd=root
		echo "The root user MySQL password! $rootpasswd."
		echo ""
		dbname=rpi
		username=yapo
		userpass=pipi
		RESULT=`mysql -u $username -p$userpass --skip-column-names -e "SHOW DATABASES LIKE 'rpi'"`
		if [ "$RESULT" == "rpi" ]; then
		    echo -e "\e[31mDatabase exist\e[0m"
		    sleep 5
		else
		    echo "The NAME of the new  database! $dbname."
		    charset=utf8
		    echo "the  database CHARACTER SET! $charset."
		    echo "Creating new  database..."
		    mysql -uroot -p${rootpasswd} -e "CREATE DATABASE ${dbname} /*\!40100 DEFAULT CHARACTER SET ${charset} */;"
		    echo "Database successfully created!"
		    echo "Showing existing databases..."
		    mysql -uroot -p${rootpasswd} -e "show databases;"
		    echo ""
		    echo "The NAME of the new  database user! $username."
		    echo ""
		    echo "The PASSWORD for the new  database user! $userpass."
		    echo "Creating new user..."
		    mysql -uroot -p${rootpasswd} -e "CREATE USER ${username}@localhost IDENTIFIED BY '${userpass}';"
		    echo "User successfully created!"
		    echo ""
		    echo "Granting ALL privileges on ${dbname} to ${username}!"
		    mysql -uroot -p${rootpasswd} -e "GRANT ALL PRIVILEGES ON ${dbname}.* TO '${username}'@'localhost';"
		    mysql -uroot -p${rootpasswd} -e "FLUSH PRIVILEGES;"
		    mysql -uroot -p${rootpasswd} -e "show databases;"
		    mysql -uroot -p${rootpasswd} -e "USE $dbname;"
		    echo "You're good now :)"
		    sleep 5
		fi
	fi
}
#sudo apt-get update -y 
#Installer_Apache
Installer_MySQL
#sudo /etc/init.d/mysql start
mysqld_safe --skip-grant-tables &
mysql
apt-get install expect -y 
# Not required in actual script
MYSQL_ROOT_PASSWORD=root

SECURE_MYSQL=$(expect -c "
set timeout 10
spawn mysql_secure_installation
expect \"Enter current password for root (enter for none):\"
send \"$MYSQL\r\"
expect \"Change the root password?\"
send \"n\r\"
expect \"Remove anonymous users?\"
send \"y\r\"
expect \"Disallow root login remotely?\"
send \"y\r\"
expect \"Remove test database and access to it?\"
send \"y\r\"
expect \"Reload privilege tables now?\"
send \"y\r\"
expect eof
")

echo "$SECURE_MYSQL"

apt-get purge expect -y 
