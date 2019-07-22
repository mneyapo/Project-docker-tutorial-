# Python Base Image from https://hub.docker.com/r/arm32v7/python/
#FROM arm32v7/python:3.5.7-stretch

FROM debian:stretch
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y sudo \
  && apt-get install -y python-pip

RUN easy_install pip
RUN pwd
RUN echo "\e[32mInstallation d’Apache\e[0m" 
RUN apt-get update -y && apt-get install -y apache2 \
	&& chown -R $USER:www-data /var/www/html/ \
	&& chmod -R 770 /var/www/html/
  
# add our user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN groupadd -r mysql && useradd -r -g mysql mysql \
  \
  && echo "\e[32m***** Init bash...\e[0m" \
  && printf "\nalias ll='ls -l'\nalias l='ls -lA'\n" >> /root/.bashrc \
  # Map Ctrl-Up and Ctrl-Down to history based bash completion
  && printf '"\\e[1;5A": history-search-backward\n"\\e[1;5B": history-search-forward\n"\\e[1;5C": forward-word\n"\\e[1;5D": backward-word' > /etc/inputrc \
  \
  && echo "\e[32m***** Install packages...\e[0m" \
  && apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y perl --no-install-recommends \
  # Install apt-get allowing subsequent package configuration
  && DEBIAN_FRONTEND=noninteractive apt-get install -y apt-utils \
  # Install minimal admin utils
  && DEBIAN_FRONTEND=noninteractive apt-get install -y less nano procps git \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libpwquality-tools  libssl-dev build-essential  python3-dev libmariadbclient-dev 
  
# Install MySQL server
RUN echo "\e[32m***** Install MySQL server...\e[0m" \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server mysql-client \
  #&& DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends mysql-server mysql-client \
  # Clean cache
  && rm -rf /var/lib/apt/lists/*

# the "/var/lib/mysql" stuff here is because the mysql-server postinst doesn't have an explicit way to disable the mysql_install_db codepath besides having a database already "configured" (ie, stuff in /var/lib/mysql/mysql)
# also, we set debconf keys to make APT a little quieter
RUN {\
		echo mariadb-server mysql-server/root_password password 'unused'; \
		echo mariadb-server mysql-server/root_password_again password 'unused'; \
	} | debconf-set-selections \
	&& apt-get update \
	&& DEBIAN_FRONTEND=noninteractive apt-get install -y mariadb-server \
	&& rm -rf /var/lib/apt/lists/* 
  
# Config mysql
RUN echo "\e[32m***** Config mysql...\e[0m" \
  # comment out any "user" entires in the MySQL config ("docker-entrypoint.sh" or "--user" will handle user switching)
  && sed -ri 's/^user\s/#&/' /etc/mysql/my.cnf /etc/mysql/conf.d/* \
  # purge and re-create /var/lib/mysql with appropriate ownership # Remove pre-installed database(rm -rf /var/lib/mysql)
  && rm -rf /var/lib/mysql && mkdir -p /var/lib/mysql /var/run/mysqld \
  && touch /var/log/mysqld.log \
  && chown -R mysql:mysql /var/lib/mysql /var/run/mysqld /var/log/mysqld.log \ 
  # Ensure that /var/run/mysqld (used for socket and lock files) is writable regardless of the UID our mysqld instance ends up having at runtime
  && chmod 777 /var/run/mysqld /var/lib/mysql \
  && chmod 775 /var/log \
  && echo "\e[31m***** Disable Debian MySQL config...\e[0m" \
  # Disable Debian MySQL config since it overwrites config from volume
  && mv /etc/mysql/conf.d/mysqldump.cnf /etc/mysql/conf.d/mysqldump.cnf.disabled \
  && mv /etc/mysql/conf.d/mysql.cnf /etc/mysql/conf.d/mysql.cnf.disabled \
  # Create placeholder for custom my.cnf
  && touch /etc/mysql/conf.d/my.cnf \
  # Set docker settings, these settings always win
  && printf '[client]\nsocket=/var/lib/mysql/mysql.sock\n\n[server]\nsocket=/var/lib/mysql/mysql.sock\ndatadir=/var/lib/mysql\nsecure-file-priv=/var/lib/mysql-files\nuser=mysql\nskip-host-cache\nskip-name-resolve\n' > /etc/mysql/conf.d/docker.cnf \
  && mkdir /docker-entrypoint-initdb.d 

# comment out a few problematic configuration values
# don't reverse lookup hostnames, they are usually another container
RUN sed -Ei 's/^(bind-address|log)/#&/' /etc/mysql/my.cnf \
  && echo 'skip-host-cache\nskip-name-resolve' | awk '{ print } $1 == "[mysqld]" && c == 0 { c = 1; system("cat") }' /etc/mysql/my.cnf > /tmp/my.cnf \
  && mv /tmp/my.cnf /etc/mysql/my.cnf

#RUN sed -i -e"s/^bind-address\s*=\s*127.0.0.1/bind-address = 0.0.0.0/"/etc/mysql/my.cnf

#COPY .my.cnf ./
#ADD .my.cnf ./

#RUN cp .my.cnf /root/
#RUN cp .my.cnf /etc/mysql/conf.d/my.cnf
       
VOLUME /var/lib/mysql
  
# Copy the script to Config and Install command
COPY healthcheck.sh /healthcheck.sh
COPY docker-entrypoint.sh /usr/local/bin/
COPY docker-entrypoint.sh /entrypoint.sh

COPY init_db.sh /tmp/init_db.sh
ADD init_db.sh /tmp/init_db.sh
#RUN /tmp/init_db.sh
ENTRYPOINT ["docker-entrypoint.sh"]
HEALTHCHECK CMD /healthcheck.sh

EXPOSE 3306

#RUN mkdir -p /app/CityClub
#RUN mkdir -p /app/CityClub/Archive

#WORKDIR /app/CityClub
COPY requirements.txt ./
ADD requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt 
#&& pip install --no-cache-dir smbus-cffi 

# Make sure dependencies are installed
#RUN python3 -m pip install --no-cache-dir -r requirements.txt

RUN echo "\e[32m***** RUN commands finished\e[0m"

## Copy source code
#COPY CityClub /app/CityClub
#COPY autostart /app/CityClub/autostart
#COPY chmod.py /app/CityClub/chmod.py
#COPY CityClub.py /app/CityClub/CityClub.py
#COPY pirc522 /app/CityClub/pirc522
#COPY python_script.py /app/CityClub/python_script.py

COPY test.py ./
COPY app.py ./

## ADD source code
#ADD CityClub /app/CityClub
#ADD autostart /app/CityClub/autostart
#ADD chmod.py /app/CityClub/chmod.py
#ADD CityClub.py /app/CityClub/CityClub.py
#ADD pirc522 /app/CityClub/pirc522
#ADD python_script.py /app/CityClub/python_script.py

ADD test.py ./
ADD app.py ./

CMD ["mysqld"]
#CMD ["python","app.py"]
# Set the default command to execute
#COPY cmd.sh /tmp/cmd.sh
#COPY cmd.sh ./
#RUN chmod +x /tmp/cmd.sh
#CMD /tmp/cmd.sh
