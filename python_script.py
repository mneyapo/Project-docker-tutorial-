#!/usr/bin/python3
# -*- coding: utf8 -*-
import RPi.GPIO as GPIO
import signal
import time
import datetime
import sys
from pirc522 import RFID
import socket
import smbus
import os
import MySQLdb
import threading
import sys
import requests
import json
import socket
import signal
import os
import re
import fcntl
import struct
import subprocess as sp

from requests.packages.urllib3.exceptions import InsecureRequestWarning
# Disable Warnings Unverified HTTPS request 
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
# Variables Globales
Version = "19.05.06.1"                  # Version Du Programme
Mode_PRG = "E"                          # Mode du Programme : "T" = Test, "E" = Exploitation
MonIP = ""                              # Adresse IP interne du Raspberry sur Eth0
societe = "CITY_CLUB"                   # Client
state=""                                # Etat de la Carte
Can_Try_Offline_Upload = False          # Permet de savoir si on peut tenter des remontées d'informations offline
LAST_MSG = ""                           # Message qui sera affiché le dernier
next_action = ""                        # Action a effectuer ensuite
Card_Init_Status = ""                   # Etat de la Carte au moment de la lecture de l'UID
last_visit = ""                         # Dernière visite enregistrée sur la carte
bOK = True                              # pour les traitements Go / no Go
boucle_attente = False                  # utilisé pour attendre que la Carte soit retirée
boucle_compteur = 0                     # utilisé comme compteur de passages dans la boucle principale, passé de 60 à 120 (1 mn)
boucle_maj = 300                        # utilisé comme compteur de passages pour vérifier la mise a jour (2mn 30s)
Link = ""                               # Lien de téléchargement
Reponse_ws = ""                         # Réponse du Web Service pour la Version du Programme
rbnom = ""                              # Nom du Raspberry installé dans le tourniquet
url_ping_CC = ""                        # URL du ping CityClub
timeout_ping = 0                        # Timeout sur le Ping CityClub et YAPO
url_WS = ""                             # URL du WebService CityClub
url_WS_tm = 0                           # Timeout sur le WebService CityClub
url_yapo_ping = ""                      # URL du Ping YAPO
last_UID = []                           # dernier UID lu
last_UID_datetime = datetime.datetime.utcnow()  # date et heure du dernier UID lu
last_message_l1 = ""                    # Dernier message sur le LCD, ligne 1, qui pourra être réaffiché
last_message_l2 = ""                    # Dernier message sur le LCD, ligne 2, qui pourra être réaffiché
last_message_l3 = ""                    # Dernier message sur le LCD, ligne 3, qui pourra être réaffiché
last_message_l4 = ""                    # Dernier message sur le LCD, ligne 4, qui pourra être réaffiché
Est_Carte = False
Est_Auth = False
tag_uid = []
#data_bloc = None
state="Non Envoyée"
lastvisitdb=""
back_Data = []
# Set util debug to true - it will print what's going on
debug = False

#********************************************************
LAST_LOCAL_DATE_TIME_PING_CC = datetime.datetime.utcnow()       # date et heure du dernier ping CityClub
LAST_LOCAL_DATE_TIME_PING_PY = datetime.datetime.utcnow()       # date et heure du dernier ping YAPO
LAST_LOCAL_DATE_TIME_PING_UPDATE = datetime.datetime.utcnow()   # date et heure du mise à jour
#********************************************************
# Carte RFID
# Clefs d'authentification
key_public    = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]      # Clé publique
key_YAPO      = [0x59,0x61,0x50,0x6F,0x54,0x74]      # clé privée YAPO
key_CityClub  = [0x43,0x69,0x54,0x79,0x43,0x6C]      # clé privée CityClub
Sector_Key_CC = [0x43,0x69,0x54,0x79,0x43,0x6C,0xFF,0x07,0x80,0x69,0x43,0x69,0x54,0x79,0x43,0x6C] # ce qu'il faut écrire dans le secteur d'authentification pour protéger la carte avec la clef privée CityClub
# Bloc1
B1S4 = 4            # FirstName
B1S5 = 5            # LastName
B1S7 = 7            # Clef d'Authentification
# Bloc2
B2S8 = 8            # Date Limite d'Abonnement
B2S11 = 11          # Clef d'Authentification
# Bloc3
B3S12 = 12          # Last Visit (Date dernier passage)
B3S15 = 15          # Clef d'Authentification
# Pour savoir si une carte est insérée
Card_Insert = 0     # carte détectée (pour boucler tant que la carte n'a pas été retirée)
#********************************************************
hostname = 'localhost'
# localhost | 
username = 'yapo'
password = 'pipi'
database = 'rpi'
# Démarrer SERVICE MySql
#os.system("sudo /etc/init.d/mysql start")
rpiname ="YAP-02"
#debug = True
# On bouclera tant que continue_reading = True
continue_reading = True
# End READING
def end_read(signal,frame):
    global run
    print("\nCtrl+C captured, ending read.")
    run = False
    rdr.cleanup()
    sys.exit()
#********************************************************
signal.signal(signal.SIGINT, end_read)
#********************************************************
# Démarrer une Instance RFID
rdr = RFID()
# Clean Up
rdr.cleanup()
#********************************************************
def is_connected():
    try:
        # connect to the host -- tells us if the host is actually
        # reachable
        socket.create_connection(("www.google.com", 80))
        return True
    except Exception as e:
        os.system("sudo ifconfig eth0 up")
        #os.system("sudo /etc/init.d/networking restart")
    return False
# Creation des Tables
# create Log table For logging
def Create_Table_Log():
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("""CREATE TABLE IF NOT EXISTS log(
        id INT NOT NULL AUTO_INCREMENT,
        Date_Heure VARCHAR(255),
        Description VARCHAR(2055),
        PRIMARY KEY(id))""")
        db.commit()
        print("Table log, if not exists, created")
        db.close()
    except Exception as e:
        print("Create table log: ",e)
        db.close()
#********************************************************
# Insertion des logs
#********************************************************
def insert_LOG(rpi_time,Note):
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("INSERT INTO log SET Date_Heure='%s', Description='%s'" % (rpi_time,Note))
        print("log a bien été ajouté !'")
        db.commit()
        db.close()
    except Exception as e:
        print("Exception while MYSQL Connection: ",err)
        db.close()
#********************************************************

#********************************************************
# Create CityClub table
def Create_Table_CC():
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("""CREATE TABLE IF NOT EXISTS `CityClub` (
        `id` int(10) NOT NULL AUTO_INCREMENT,
        `idreader` varchar(16) NOT NULL,
        `mode` varchar(16) NOT NULL,
        `uid` varchar(30) NOT NULL,
        `firstname` varchar(100) NOT NULL,
        `lastname` varchar(100) NOT NULL,
        `enddate` varchar(30) NOT NULL,
        `rpitime` varchar(30) NOT NULL,
        `newvisit` varchar(30) NOT NULL,
        `Est_Envoye` varchar(10) NOT NULL,
        `A_Remonter` varchar(10) NOT NULL,
        `Result_ws` varchar(50) NOT NULL,
        PRIMARY KEY (`id`)
        )""")
        db.commit()  # accept the changes
        print("Table CityClub, if not exists, created")
        db.close()
    except Exception as e:
        print("Create table cc: ",e)
        db.close()
#********************************************************
#********************************************************
# Insertion des Passages Offline
#********************************************************
def insert_passage(host,uidcarte,Nom,Prenom,Datefin,rpitimes,dvisit,A_Envoyer,A_remonter,Result):
    global debug
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        query="INSERT INTO CityClub SET idreader='%s', mode='offline', uid='%s', firstname='%s', lastname='%s', enddate='%s', rpitime='%s',newvisit='%s' ,  Est_Envoye= '%s',A_Remonter= '%s',Result_ws= '%s'" % (host,uidcarte,Nom,Prenom,Datefin,rpitimes,dvisit,A_Envoyer,A_remonter,Result)
        if debug: print("query: ",query)
        curs.execute(query)
        if debug: print("Passage à été bien Enregistré !'")
        db.commit()
        db.close()
    except Exception as err:
        print("Exception insert_passage: ",err)
        db.close()
#*******************************************************

#********************************************************
# Update Passage
#********************************************************
def update_passage(ServerID):
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("UPDATE CityClub SET Est_Envoye='OUI' WHERE id='%s'" % ServerID)
        db.commit()  # accept the changes
        state="Envoyée"
    except MySQLdb.Error as err:
        state="Non-Envoyée"
        print("Update Passage: ",state," ",err)
        db.close()
    finally:
        curs.close()
        db.close()
    return state
#********************************************************

#********************************************************
def Appel_Web_Service(json_data):
    global url_WS
    global url_WS_tm
    global Can_Try_Offline_Upload   # Permet de savoir s'il faut faire des remontées d'information Offline
    headers = {'User-Agent':rpiname,'Content-Type':'application/json','Accept':'application/json'}
    try:
        requests.packages.urllib3.disable_warnings()
        r=requests.post(url_WS, data = json_data, headers = headers, verify = False, timeout = url_WS_tm)
        if r.status_code != 200:
            Can_Try_Offline_Upload = False
            print("Failed to post data to server")
            mode = "pas200"
            return r,mode
        else:
            mode ="online"
            Can_Try_Offline_Upload = True
            return r,mode
    except Exception as e:
        Can_Try_Offline_Upload = False
        r =""
        mode = "exception"
        return r,mode
#********************************************************

#********************************************************
# select Offline Passage ORDER BY rpitime
#********************************************************
def select__passage():
    global debug
    state="Non Envoyée"
    carte_da='{}'
    mode=""
    response=""
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("UPDATE CityClub SET newvisit= rpitime  WHERE Est_Envoye='NON' AND A_Remonter='OUI' and    newvisit='--::'")
        sql = "SELECT * FROM CityClub WHERE Est_Envoye='NON' AND A_Remonter='OUI' ORDER BY rpitime ASC LIMIT 1"
        curs.execute(sql)
        results = curs.fetchall()
        for row in results:
            fid = row[0]
            carte_da ='{"idreader":"'+row[1]+'","uid":"'+row[3]+'","mode":"'+row[2]+'","rpitime":"'+row[7]+'","lastvisit":"'+row[8]+'","resultacb":"'+row[11]+'"}'
        if not carte_da =='{}':
            print(carte_da)
            response,mode=Appel_Web_Service(carte_da)

        if debug: print("response",response)
        if mode=="online":
            if not 'exception' in response and response !="":
                curs.execute("UPDATE CityClub SET Est_Envoye='OUI' WHERE id='%s'" %fid)
                db.commit()  # accept the changes
                state="Envoyée"
            else:
                state="Non Envoyée"
            print("Status: ",state)
        db.close()
        time.sleep(1)
    except Exception as e:
        print("Envoie des passages: ",e)
        db.close()
#********************************************************
# FUNCTION Traitement Post-ONLINE
#********************************************************
def select_COUNT():
    fcount =0
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        sql = "SELECT count(*) FROM CityClub WHERE Est_Envoye='NON' AND A_Remonter= 'OUI'"
        curs.execute(sql)
        results = curs.fetchall()
        for row in results:
            fcount = row[0]
        db.close()
    except Exception as err:
        print("Selection des Passages: ",err)
        db.close()
    return fcount
#********************************************************
# Post-Online
#********************************************************
def traitement_post_online():
    try:
        count = select_COUNT()
    except:
        count=0
    if count !=0:
        print("Nombre File D'attente:",count)
        time.sleep(0.1)
        select__passage()
#********************************************************

#*******************************************************
# Mise à jour des droits de l'autostart
def Chmod_autostart():
    try:
        qm_status,qm_result = sp.getstatusoutput("sudo chmod o+rwx /home/pi/CityClub/autostart")
        if qm_status == 0 :
            return "OK"
        else:
            print(qm_result)
            return "NG"
    except Exception as e:
        print(e)
        return "NG"
#*******************************************************
# Ces paramètres seront insérés que la première fois, les autres fois,
# Comme ils sont déjà présents, il seront ignorés
#********************************************************
def Insert_Param_autostart():
# Ces paramètres seront insérés que la première fois, les autres fois, comme ils sont déjà présents, il seront ignorés
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("""INSERT INTO `Parametre` (`id`, `Param_Nom`, `Param_Valeur`) VALUES
       (11, 'autostart','0')
        ;""")
        db.commit()  # accept the changes
        # print("Table Parametre Updated")
        db.close()
    except Exception as e:
        db.close()
#*******************************************************

#*******************************************************
# Insert Mode
def Insert_Param_Mode_PRG():
# Ces paramètres seront insérés que la première fois, les autres fois, comme ils sont déjà présents, il seront ignorés
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("""INSERT INTO `Parametre` (`id`, `Param_Nom`, `Param_Valeur`) VALUES
       (8, 'Mode_PRG','T')
        ;""")
        db.commit()  # accept the changes
        # print("Table Parametre Updated")
        db.close()
    except Exception as e:
        db.close()
#********************************************************
# Update Param table
def UPDATE_url_Param(Url_W,Url_p):
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("UPDATE Parametre SET Param_Valeur='%s' WHERE Param_Nom='Url_WS'"%(Url_W))
        curs.execute("UPDATE Parametre SET Param_Valeur='%s' WHERE Param_Nom='Url_ping'"%(Url_p))
        curs.execute("""REPLACE INTO `Parametre` (`id`, `Param_Nom`, `Param_Valeur`) VALUES
       (8, 'Mode_PRG','E');""")
        print("Url && Mode Updated ")
        # accept the changes
        db.commit()
        db.close()
    except Exception as ex:
        print(ex)
        db.close()
#********************************************************

#********************************************************
# Update autostart
def Update_Param_autostart():
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("""REPLACE INTO `Parametre` (`id`, `Param_Nom`, `Param_Valeur`) VALUES
       (11, 'autostart', 1);""")
        db.commit()  # accept the changes
        print("Parametre autostart Updated")
        db.close()
    except Exception as e:
        print(e)
        db.close()
#*******************************************************

#********************************************************
# Update Mode
def Update_Mode_PRG():
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("""REPLACE INTO `Parametre` (`id`, `Param_Nom`, `Param_Valeur`) VALUES
       (8, 'Mode_PRG','E');""")
        db.commit()  # accept the changes
        print("Parametre Mode_PRG Updated")
        db.close()
    except Exception as e:
        print("Update_Mode_PRG: ",e)
        db.close()
#*******************************************************

#********************************************************
# Update Param table
def UPDATE_Param():
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        # RPI Name (pour information)
        curs.execute("UPDATE Parametre SET Param_Valeur='%s' WHERE Param_Nom='idreader'"%(rpiname))
        print("idreader Updated :",rpiname)
        # Version (pour information)
        curs.execute("UPDATE Parametre SET Param_Valeur='%s' WHERE Param_Nom='Version'"%(Version))
        print("Version Updated :",Version)
        # accept the changes
        db.commit()
        db.close()
    except Exception as ex:
        print("Update Param table: ",ex)
        db.close()
#********************************************************

#*******************************************************
# Insert Param table
def Insert_Update_Param():
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        # La syntaxe REPLACE permet de créer ou de mettre à jour un paramètre existant
        curs.execute("""REPLACE INTO `Parametre` (`id`, `Param_Nom`, `Param_Valeur`) VALUES
        ( 1, 'Version',      'NOT USED'),
        ( 2, 'Url_WS',       'http://192.168.1.201/access/amb'),
        ( 3, 'timeout',      '0.8'),
        ( 4, 'idreader',     'TBD-01'),
        ( 5, 'Url_ping',     'http://192.168.1.201/access/amb/ping'),
        ( 6, 'timeout_ping', '2'),
        ( 7, 'lcd_addr',     '39'),
        ( 9, 'Url_WS_t',     'https://arya.ovh/local/test'),
        (10, 'Url_ping_t',   'https://arya.ovh/local/test/ping')
        ;""")
        db.commit()  # accept the changes
        print("Table Parametre Updated")
        db.close()
    except Exception as e:
        print("Insertion Param table: ",e)
        db.close()
#********************************************************

#********************************************************
# Récupération des Paramètres dans la base MySQL
def get_param(Param_N):
    Param_Valeur=""
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("SELECT Param_Valeur FROM Parametre Where Param_Nom='%s'"% Param_N)
        results = curs.fetchall()
        for row in results:
            Param_Valeur = row[0]
        db.close()
    except Exception as e:
        print("Récupération des Paramètres: ",e)
        db.close()
    return  Param_Valeur
#********************************************************

#********************************************************
# show Parametre
def show_Param():
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        curs.execute("SELECT Param_Nom, Param_Valeur FROM Parametre")
        for Param_info in curs.fetchall():
            print(Param_info)
        curs.close()
        print("Table Parametre shown")
        db.close()
    except Exception as e:
        print("View Parametres: ",e)
        db.close()
#********************************************************
# Create Param table
def Create_Table_Param():
    try:
        db = MySQLdb.connect(host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()
        # curs.execute("DROP TABLE `rpi`.`Parametre`;")
        curs.execute("""CREATE TABLE IF NOT EXISTS Parametre(
        id INT NOT NULL AUTO_INCREMENT,
        Param_Nom varchar(40) NOT NULL,
        Param_Valeur varchar(100) NOT NULL,
        PRIMARY KEY (id))
        """)
        db.commit()  # accept the changes
        print("Table Parametre, if not exists, created")
        db.close()
    except Exception as e:
        print("Create Param table: ",e)
        db.close()
#********************************************************
# Create user
def CREATE_USER():
    try:
        db = MySQLdb.connect( host=hostname,user=username, passwd=password, db=database)
        curs=db.cursor()  # creates new cursor object for executing SQL statements
        curs.execute("""CREATE USER IF NOT EXISTS 'yapo'@'%' IDENTIFIED BY 'pipi';""")
        curs.execute("""GRANT ALL PRIVILEGES ON *.* TO 'yapo'@'%' WITH GRANT OPTION;""")
        curs.execute("SELECT User, Host, plugin FROM mysql.user")
        for info in curs.fetchall() :
            print(info)
        curs.close()
        db.close()  # closes the connection
    except Exception as e:
        print("Create user: ",e)
        db.close()  # closes the connection
#********************************************************
# Create DB
def CREATE_DB():
    try:
        db = MySQLdb.connect( host='127.0.0.1',user='root', passwd='root', db='mysql')
        curs=db.cursor()  # creates new cursor object for executing SQL statements
        curs.execute("""CREATE DATABASE  IF NOT EXISTS rpi;""")
        db.commit()  # conn.commit()  //Commits the transactions
        db.close()  # closes the connection
    except Exception as e:
        db.close()  # closes the connection
        print("Create database: ",e)
#********************************************************
# Afficher Les Bases Existants
def SHOW_DB():
    try:
        print ("Using MySQLdb…")
        myConnection = MySQLdb.connect( host=hostname, user=username, passwd=password, db=database)
        cur = myConnection.cursor()
        cur.execute( "SHOW DATABASES;" )
        for DATABASES in cur.fetchall() :
            print(DATABASES)
        cur.close()
        myConnection.close()
    except Exception as e:
        print("Erreur: ", e)
#********************************************************
#********************************************************
# adresse IP locale
def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', bytes(ifname[:15], 'utf-8'))
    )[20:24])
#********************************************************
# Mode du Programme : T pour TEST sinon E pour EXPLOITATION
#********************************************************
def Quel_Mode():
    global url_WS
    global url_ping_CC
    global Mode_PRG         # Mode du Programme : T pour TEST sinon E pour EXPLOITATION
    global debug
    try:
        list_ip=['192.168.1.201','192.168.11.201','192.168.12.201','192.168.13.201','192.168.14.201','192.168.15.201','192.168.16.201','192.168.17.201','192.168.18.201','192.168.19.201','192.168.20.201','192.168.21.201','192.168.22.201','192.168.23.201','192.168.24.201','192.168.25.201','192.168.26.201','192.168.27.201','192.168.28.201','192.168.29.201','192.168.30.201','192.168.31.201','192.168.32.201','192.168.33.201','192.168.34.201','192.168.36.201']
        for ip in list_ip:
            qm_status,qm_result = sp.getstatusoutput("ping -c1 -w1 "+ip)
            if debug: print("Status from :",ip, ": active" if not qm_status else "inactive")
            if qm_status == 0 :
                print ("Status from ", ip,"is","alive")
                url_WS='http://'+ip+'/access/amb'
                url_ping_CC='http://'+ip+'/access/amb/ping'
                UPDATE_url_Param(url_WS,url_ping_CC)
                Mode_PRG = "E"
                break
            else:
                Mode_PRG = "T"
    except Exception as e:
        print(e)
        Mode_PRG = "T"
#********************************************************

#********************************************************
# Récupération de la Date et l'Heure du Raspberry au format AAAA-MM-JJ HH:mm:SS
def get_rpi_time():
    strtoday= datetime.datetime.utcnow()
    rpitime=strtoday.strftime("%Y-%m-%d %H:%M:%S")
    return rpitime
#********************************************************
#********************************************************
def change_Datetime_format(date_time):
    backData=date_time[0:4]+"-"+date_time[4:6]+"-"+date_time[6:8]+" "+date_time[8:10]+":"+date_time[10:12]+":"+date_time[12:14]
    return backData
#********************************************************
#********************************************************
# Version Info
def Get_Version_from_ws():
    Data = ""
    try:
        url = 'http://update.yapo.ovh/GetVersion/CITYCLUB_RPI'
        r = requests.get(url, timeout=5)
        if r.status_code ==200:
            Data=r.text
    except requests.exceptions.ConnectionError as errc:
         print ("\nMise à jour : Error Connecting ",datetime.datetime.utcnow().strftime("%H:%M:%S"))
         insert_LOG(get_rpi_time(),"Mise à jour  : Error Connecting")
    except Exception as e:
        print(e)
    return Data
#********************************************************

#********************************************************
# VERIFIER Les mises à jour
def Check_New_Version():
    global continue_reading
    # print("\nMise à jour ? : ",end="")
    # boucle_maj = 0
    Reponse_ws = Get_Version_from_ws()
    if Reponse_ws != "":
        if not Reponse_ws.startswith("<html"):
            pos1 = Reponse_ws.find('Version')
            pos2 = Reponse_ws.find(';')
            Version_ws = Reponse_ws[pos1+8:pos2]
            pos1 = Reponse_ws.find('Link')
            Link = Reponse_ws[pos1+5:]# Utilisé pour Telechargement
            print("Mise à jour ? : ","PRG :", Version, "SRV :", Version_ws, "Lien :", Link)
            if Version_ws > Version:
                print("Téléchargement du programme de mise à jour",Version_ws,"\n")
                status = Telecharger_Mise_a_jour_Programe(Link) #  Telécharger Programme depuis Web Service
                time.sleep(1)
                if status =="OK":
                    print("Téléchargement Terminé ...")
                    continue_reading = False
                    time.sleep(1)
                    msg("PRG REDEMARRE", "ESSAYEZ + TARD","","")
                    time.sleep(1)
                    try:
                        os.system('sudo reboot') # redémarrer
                    except Exception as e:
                        print("Exception: ",e)
                        pass
                else:
                    print("Mise à jour ? : ", "Réponse Incorrecte ...")
        else:
            print("Mise à jour ? : ", "Réponse Incorrecte ...")
#********************************************************

#********************************************************
def Telecharger_Mise_a_jour_Programe(url):
    try:
        r = requests.get(url)
        if r.status_code ==200:
            path="/home/pi/CityClub/CityClub.py"
            with open(path, 'wb') as f:
                f.write(r.content)
            return "OK"
        else:
            return "NG"
    except Exception as e:
        print(e)
        return "NG"
#********************************************************

#********************************************************
def Telecharger_autostart():
    try:
        r = requests.get("http://update.yapo.ma/2018-08-12_autostart.txt")
        if r.status_code ==200:
            path="/home/pi/CityClub/autostart"
            with open(path, 'wb') as f:
                f.write(r.content)
        return "OK"
    except Exception as e:
        print(e)
        return "NG"
#********************************************************

#********************************************************
# Envoi d'un ping vers le serveur YAPO
def Send_last_passage(last_passage):
    global url_yapo_Send_last_passage # URL d'envoie passage
    global timeout_ping     # Time out
    global continue_reading
    try:
        requests.packages.urllib3.disable_warnings()
        my_req = requests.get(url_yapo_Send_last_passage+last_passage, verify = False, timeout = timeout_ping) # Timeout
        if my_req.status_code != 200:
            print("Ping YAPO : ", "Echec, code : ", my_req.status_code)
        else:
            rep = my_req.text
            print("Date dernier passage depuis Web Service: [", change_Datetime_format(last_passage),"] ")
            if not rep.startswith("<html"):
                if my_req.text != "":
                    print("Ping YAPO : ",my_req.text[:3],change_Datetime_format(my_req.text[3:]))
                else:
                    print("Ping YAPO : ", my_req.text) # OK : + Date et Heure du serveur YAPO
                #my_req.text = 'REBOOT'
                if my_req.text == 'REBOOT':
                    continue_reading = False
                    print("MACHINE REBOOT", "ESSAYEZ + TARD")
                    time.sleep(1)
                    msg("MACHINE REBOOT", "ESSAYEZ + TARD","","")
                    time.sleep(1)
                    os.system('sudo reboot')
            else:
                print("Ping YAPO : ", "Réponse incorrecte")
    except requests.exceptions.ConnectionError as errc:
         print ("Ping YAPO : Error Connecting ",datetime.datetime.utcnow().strftime("%H:%M:%S"))
         insert_LOG(get_rpi_time(),"Ping YAPO : Error Connecting")
    except requests.exceptions.Timeout as errt:
        print ("Ping YAPO : Timeout Error:",errt)
        insert_LOG(get_rpi_time(),"Ping YAPO : Timeout Error")
    except Exception as e:
        print("Ping YAPO : ", "Exception : ", e)
        insert_LOG(get_rpi_time(),"Ping YAPO : Connection")
#********************************************************

#********************************************************
# Envoi d'un ping vers le serveur
def Ping_Local_CityClub():
    global url_ping_CC              # url du Ping CityClub
    global timeout_ping             # Time out
    global rbnom                    # le Nom local du RPI
    global Can_Try_Offline_Upload   # Permet de savoir s'il faut faire des remontées d'information Offline
    my_post_data = '{"idreader":"' + rbnom + '","mode":"ping"}' # POST data envoyé au Ping
    my_headers = {'User-Agent':rbnom,'Content-Type':'application/json','Accept':'application/json'}
    try:
        requests.packages.urllib3.disable_warnings()
        req=requests.post(url_ping_CC, data = my_post_data, headers = my_headers, verify = False, timeout= timeout_ping) # Timeout
        if req.status_code != 200:
            Can_Try_Offline_Upload = Fals
            print("Ping Local CC : ", "Echec, code : ", req.status_code)
        else:
            my_reponse_json = json.loads(req.text)
            ping_reply_datetime = my_reponse_json['currentdatetime'] # Date et Heure retourné par le ping CC
            Can_Try_Offline_Upload = True # autoriser les remontées d'information
            print("Ping Local CC : ", "OK : ", ping_reply_datetime)
    except requests.exceptions.ConnectionError as errc:
        Can_Try_Offline_Upload = False
        print ("\nPing Local CC : Error Connecting ",datetime.datetime.utcnow().strftime("%H:%M:%S"))
        insert_LOG(get_rpi_time(),"Ping Local CC : Error Connecting")
    except requests.exceptions.Timeout as errt:
        Can_Try_Offline_Upload = False
        print ("Ping Local CC : Timeout Error:",errt)
        insert_LOG(get_rpi_time(),"Ping Local CC : Timeout Error")
    except Exception as e:
        Can_Try_Offline_Upload = False
        print("Ping Local CC : ","Echec, Exception : ", e)
        insert_LOG(get_rpi_time(),"Ping Local CC : Echec, Exception : ConnectionError")
#********************************************************

#********************************************************
def Ping_all():
    # Ping_Local_CityClub
    pCC=threading.Thread(name='pCC',target=Ping_Local_CityClub)
    pCC.start()
    pCC.join(5) # # Attend 5 secondes que le thread se termine
    # Ping_Yapo
    # Envoyer la date du dernier passage
    pLast_pass = threading.Thread(name='pLast_pass',target=Send_last_passage, args=(last_passage,))
    pLast_pass.start()
    pLast_pass.join(5) # # Attend 5 secondes que le thread se termine
#********************************************************

#********************************************************
# Bus GPIO
#********************************************************
GPIO_LEDR = 32          # LED Rouge
#********************************************************
GPIO_LEDV = 36          # LED Verte
#********************************************************
GPIO_buzzer = 7         # uzzer est branche sur la pin 7 / GPIO4
#********************************************************
GPIO_relais = 40        # Relais est branche sur la pin 40 / GPIO21
#********************************************************

#********************************************************
# Afficheur LCD via le bus I2C
I2C_ADDR  = 0 # pour test 0x27 et  0x3f pour city club
I2C_LINE = "2" # NB de lignes de l'afficheur, 2 lignes ou 4 lignes
LCD_ON = 1 # permet de désactiver le LCD si souci avec
LCD_WIDTH = 20   # Maximum characters per line
LCD_CHR = 1 # Mode - Sending data
LCD_CMD = 0 # Mode - Sending command
LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line
LCD_LINE_3 = 0x94 # LCD RAM address for the 3rd line
LCD_LINE_4 = 0xD4 # LCD RAM address for the 4th line
LCD_BACKLIGHT  = 0x08  # On
ENABLE = 0b00000100 # Enable bit
E_PULSE = 0.0005 # Timing constants
E_DELAY = 0.0005 # Timing constants


# Initialisation LCD ************************************
def lcd_init():
    lcd_byte(0x33,LCD_CMD) # 110011 Initialise
    lcd_byte(0x32,LCD_CMD) # 110010 Initialise
    lcd_byte(0x06,LCD_CMD) # 000110 Cursor move direction
    lcd_byte(0x0C,LCD_CMD) # 001100 Display On,Cursor Off, Blink Off
    lcd_byte(0x28,LCD_CMD) # 101000 Data length, number of lines, font size
    lcd_byte(0x01,LCD_CMD) # 000001 Clear display
    time.sleep(E_DELAY)

# Send byte to data pins, bits = the data, mode = 1 for data, 0 for command
def lcd_byte(bits, mode):
    bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
    bits_low = mode | ((bits<<4) & 0xF0) | LCD_BACKLIGHT
    bus.write_byte(I2C_ADDR, bits_high) # High bits
    lcd_toggle_enable(bits_high)
    bus.write_byte(I2C_ADDR, bits_low) # Low bits
    lcd_toggle_enable(bits_low)

# LCD Toggle Enable **************************************
def lcd_toggle_enable(bits):
    time.sleep(E_DELAY)
    bus.write_byte(I2C_ADDR, (bits | ENABLE))
    time.sleep(E_PULSE)
    bus.write_byte(I2C_ADDR,(bits & ~ENABLE))
    time.sleep(E_DELAY)

# Affichage Message sur une Ligne ************************
def lcd_string(message,line):
    message = message.ljust(LCD_WIDTH," ") # Send string to display
    lcd_byte(line, LCD_CMD)
    for lcd_i in range(LCD_WIDTH):
        lcd_byte(ord(message[lcd_i]),LCD_CHR)
# Clear SCREEN
def lcd_clear():
    lcd_byte(0x01,LCD_CMD) # 000001 Clear display
# Affichage Message sur 4 lignes, et report sur Console **
def msg(L1,L2,L3,L4):
    global last_message_l1
    global last_message_l2
    global last_message_l3
    global last_message_l4
    global LCD_ON
    last_message_l1 = L1
    last_message_l2 = L2
    last_message_l3 = L3
    last_message_l4 = L4
    lcd_clear()
    if I2C_LINE == "4":
        if LCD_ON: lcd_string(L1,LCD_LINE_1)
        if LCD_ON: lcd_string(L2,LCD_LINE_2)
        if LCD_ON: lcd_string(L3,LCD_LINE_3)
        if LCD_ON: lcd_string(L4,LCD_LINE_4)
        if LCD_ON: print("LCD:",L1,"|",L2,"|",L3,"|",L4)
        else: print("(LCD OFF):",L1,"|",L2,"|",L3,"|",L4)
    else:
        if LCD_ON: lcd_string(L1,LCD_LINE_1)
        if LCD_ON: lcd_string(L2,LCD_LINE_2)
        if LCD_ON: print("LCD:",L1,"|",L2)
        else: print("(LCD OFF):",L1,"|",L2)
#********************************************************

#********************************************************
## Programme principal ##

#********************************************************
# Création des Tables s'il elles n'existent pas
Create_Table_Log()    # Log de l'application
Create_Table_Param()  # Paramètres
Insert_Update_Param() # Mise à jour des Paramètres, création si non existant
UPDATE_Param()        # Mise à jour du Nom du RPI et de la Version dans la Base (pour information)
Create_Table_CC()
#********************************************************
rpiname  = "YAP-02"
# c'est parti
print("Début :")
# takedown the internet os.system('sudo ifconfig eth0 up down')
# Mise à jour de l'autostart
print("autostart version : ",end="")
Insert_Param_autostart() # Insére la valeur "0" si le paramètre autostart n'est pas encore présent
version_autostart =  get_param("autostart")
print(version_autostart)
if version_autostart == "0":
    print("mise à jour de autostart :")
    print("chmod sur autostart:")
    if Chmod_autostart() != "OK":
        print(" Echec !")
    else:
        print(" OK ...")
        print ("Téléchargement du nouvel autostart :")
        if Telecharger_autostart ()== "NG":
            print("Echec !")
        else:
            print("OK...")
            print("Update Paramètre autostart ...")
            Update_Param_autostart()
            time.sleep(2)
            os.system('sudo reboot')

# La version se trouve dans la variable Version
print("Programme Version :", Version)

# Adresse IP eth0
try:
    MonIP = get_ip_address("eth0")
except:
    MonIP = "0.0.0.0"
print("IP locale", MonIP)

# Nom du Raspberry
rbnom=get_param("idreader")
print("Reader name: ",rbnom)
# Mode
Insert_Param_Mode_PRG()
Mode_PRG = get_param("Mode_PRG") # relire le mode d'esploitation, si T (Test) comme la première fois, détecter le changement
# si on est encore en mode Test
if Mode_PRG == "T":
    print("ping sur les adresses serveur, si joignable Désactivé")
    #Quel_Mode() # ping sur adresse serveur, si joignable, Mode Exploitation
if Mode_PRG == "T": print("Mode TEST")
else: print("Mode Exploitation")

# URL du ping CityClub
if Mode_PRG == "E" :
    url_ping_CC=get_param("Url_ping")
else :
    url_ping_CC=get_param("Url_ping_t")
print("Ping CC sur : ",url_ping_CC)

# URL du WebService CityClub
if Mode_PRG == "E" :
    url_WS=get_param("Url_WS")
else :
    url_WS=get_param("Url_WS_t")
print("WS CC sur : ",url_WS)

# Timeout du WebService CityClub
url_WS_tm=float(get_param("timeout"))
print ("WS Timeout : ",url_WS_tm)
# Timeout du WebService CityClub
timeout_ping=float(get_param("timeout_ping"))
print ("Ping CC et YAPO : Timeout : ", timeout_ping)

# URL du Ping YAPO
# Nouvelle adresse
url_yapo_Send_last_passage="http://www.e-maroc.org/ping_up/CITY_CLUB/RPI/"+rbnom+"/"
print("Ping YAPO / Dernier passage sur:",url_yapo_Send_last_passage)
#********************************************************
# Liste des RPI connus avec afficheur 4 lignes (à remplacer par WEB-SERVICE)
my_list = ["YAP-03","MNE-01","CM5-01","CAL-01","UHR-01","VAL-01","RNK-02","JDA-01","MGL-02","INZ-01","INZ-02","AMI-01","AMI-02"]
if rpiname in my_list:
    I2C_LINE = "4"
else:
    I2C_LINE = "2"

# Initialiser le LCD
#I2C_ADDR = int(get_param("lcd_addr"))
I2C_ADDR = 0X27
bus = smbus.SMBus(1)
try:
    lcd_init()
    lcd_byte(0x01,LCD_CMD)
    lcd_init()
except:
    I2C_ADDR = 0x3F
    try:
        lcd_init()
        lcd_byte(0x01,LCD_CMD)
        lcd_init()
    except:
        I2C_ADDR = 0 # pas de LCD
        LCD_ON = 0 # pas de LCD

# Time interval in Seconds
time_sleep_led = .5
time_sleep_relay = 0.5
#rpiname = str(socket.gethostname())     # Nom RPI
print("Adresse LCD (I2C_ADDR) : ",end="")
print('0x' + hex(I2C_ADDR)[2:].rjust(2, '0'))
print("# Lignes LCD : ",I2C_LINE)

last_passage = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
print("LAST LOCAL DATETIME PING: ",datetime.datetime.utcnow().strftime("%H:%M:%S"))

# Ping CityClub && YAPO
p_all= threading.Thread(name='p_all',target=Ping_all)
p_all.start()

# Verifier mise a jour
p_maj= threading.Thread(name='p_maj',target=Check_New_Version)
p_maj.start()

# Utile
if LCD_ON:
    msg(rbnom + ' (' + Mode_PRG + ')', MonIP,"","")
    time.sleep(3)
# Déclencher le buzzer

def setup():
    # Initialisation du bus GPIO
    GPIO.setmode(GPIO.BOARD)            # comme la librairie MFRC522
    GPIO.setwarnings(False)             # Disable Warnings
    GPIO.setup(GPIO_relais, GPIO.OUT)   # Pin Relais
    GPIO.output(GPIO_relais, True)      # éteindre le Relais
    GPIO.setup(GPIO_buzzer, GPIO.OUT)   # Pin Buzzer
    GPIO.output(GPIO_buzzer, True)      # éteindre le Buzzer
    GPIO.setup(GPIO_LEDV, GPIO.OUT)     # Pin Led Verte
    GPIO.output(GPIO_LEDV, False)       # éteindre la LED Verte
    GPIO.setup(GPIO_LEDR, GPIO.OUT)     # Pin LED Rouge
    GPIO.output(GPIO_LEDR, False)       # éteindre LED Rouge
# Pour déclencher le buzzer : bip
def declenchebuzzer():
    GPIO.output(GPIO_buzzer,GPIO.LOW)  # led on
    time.sleep(0.1)        # Attendre
    GPIO.output(GPIO_buzzer, GPIO.HIGH) # led off
    time.sleep(0.1)        # Attendre

# Pour déclencher le buzzer 3 fois : bip-bip-bip
def declenchebuzzer3():
    for x in range(1, 4):
        declenchebuzzer()
        time.sleep(0.05)
#******************************************************
def turnOn(pin):
    GPIO.output(pin,True)
    time.sleep(time_sleep_led)
    GPIO.output(pin,False)
#******************************************************
#********************************************************
# Pour déclencher le relais
def declencherelay():
    GPIO.output(GPIO_relais, False)     # Allumer
    time.sleep(time_sleep_relay)        # Attendre
    GPIO.output(GPIO_relais, True)      # Eteindre
#********************************************************
def destroy():
  GPIO.output(GPIO_LEDV, GPIO.LOW)   # led off
  GPIO.output(GPIO_LEDR, GPIO.LOW)   # led Rouge off
  GPIO.output(GPIO_buzzer,True)      # Buzzer off
  GPIO.cleanup()                     # Release resource

#********************************************************

#********************************************************
# Récupération de la Date et l'Heure du Raspberry au format AAAA-MM-JJ HH:mm:SS
def get_rpi_time():
    strtoday= datetime.datetime.utcnow()
    rpitime=strtoday.strftime("%Y-%m-%d %H:%M:%S")
    return rpitime
#********************************************************

#********************************************************
def h2str(entree):
    sortie=str(chr(entree))
    return sortie
#********************************************************
#********************************************************
def change_Datetime_format(date_time):
    backData=date_time[0:4]+"-"+date_time[4:6]+"-"+date_time[6:8]+" "+date_time[8:10]+":"+date_time[10:12]+":"+date_time[12:14]
    return backData
#********************************************************
def read_card(backData):
    Datatemp = ""
    c =0
    while (c<16):
        if(backData[c]!=0):
            try:
                Datatemp=Datatemp+h2str(backData[c])
            except Exception as e:
                print(e)
        c=c+1
    #print("\n")
    return Datatemp
#********************************************************

#********************************************************
def write_data(sdata):
    data = []
    strx=sdata
    for c in strx:
        if (len(data)<16):
            data.append(int(ord(c)))
    while(len(data)!=16):
        data.append(0)
    return data
#********************************************************

#********************************************************
def from_card(date_time):
    backData=date_time[0:4]+"-"+date_time[4:6]+"-"+date_time[6:8]+date_time[8:11]+":"+date_time[11:13]+":"+date_time[13:15]
    return backData
#********************************************************

#*******************************************************
def Date_Comparison(DATE_VALID):
    DATE_DAY=strtoday.strftime("%Y-%m-%d")
    if DATE_VALID >= DATE_DAY:
        bOkString="OK"
    else:
        if DATE_VALID != "":
            bOkString="STOP X04"
        else:
            bOkString="STOP X07"
    return bOkString
#*******************************************************

#********************************************************
def String_replace(time_temp):
    time_temp=time_temp.replace('-','')
    time_temp=time_temp.replace(':','')
    return time_temp
#********************************************************

#*****************************************************************
def change_date_format(dt):
        return re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1', dt)
#****************************************************************
#********************************************************
def recup_date_val(dlv): # autre method equivalante read_card()+h2str
    Date_TEMP=""
    Date_TEMP_OUT=""
    c= 0
    while (c<len(dlv)):
        if(dlv[c]!=0):
            try:
                Date_TEMP=str(chr(dlv[c]))
                Date_TEMP_OUT=Date_TEMP_OUT+Date_TEMP
            except :
                print(" Contenu Illisible")
        c=c+1
    return Date_TEMP_OUT
#********************************************************

#********************************************************
def Traitement_OK_STOP(res):
    if res == 'OK':
        print("Led Verte - ")
        t2 = threading.Thread(name='t2',target=turnOn, args=(GPIO_LEDV,)).start()
        print("Relais")
        t1 = threading.Thread(name='t1',target= declencherelay).start()
    else:
        print("Led Rouge")
        t3 = threading.Thread(name='t3',target=turnOn, args=(GPIO_LEDR,)).start()
        t4 = threading.Thread(name='t4',target=declenchebuzzer3).start() # Buzzer
#********************************************************
# FUNCTION Card
#********************************************************

#-------------------------------------------------------
def Read_lastname_firstname_from_Card(current_UID):
# Ecrit le lastname dans le secteur B1S4 et le firstname dans le secteur B1S5
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    my_lastname = ""
    my_firstname = ""
    global debug
    # try auth with CC key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST CC")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST CC 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD CC ...")
            # print("UID CC ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT CC ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B1S4, key_CityClub, my_UID)
                        # print("AUTH A CC...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A CITYCLUB B1S4 OK")
    # Lire
    if not (E_Carte and E_Auth):
        print("Echec Auth B1S4")
        Est_Erreur = True
    else:
        # Lire Firstname B1S4
        (Est_Erreur, my_data) = rdr.read(B1S4)
        if not Est_Erreur:
            my_firstname = read_card(my_data)
        # Lire Lastname B1S5
        if not Est_Erreur:
            (Est_Erreur, my_data) = rdr.read(B1S5)
            if not Est_Erreur:
               my_lastname = read_card(my_data)
    # Conclure
    rdr.stop_crypto()
    if debug: print("Stopping crypto1")
    return Est_Erreur, my_lastname, my_firstname
#-------------------------------------------------

#-------------------------------------------------------
def Write_lastname_firstname_to_Card(lastname,firstname, current_UID):
# Ecrit le lastname dans le secteur B1S4 et le firstname dans le secteur B1S5
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    global debug
    # first try with Public key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST PB")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST PB 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD PB ...")
            # print("UID PB ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT PB ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B1S4, key_public, my_UID)
                        # print("AUTH A PB ...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A PUBLIC B1S4 OK")
    # second try with Public key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD CC ...")
            # print("UID CC ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT CC ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B1S4, key_CityClub, my_UID)
                        # print("AUTH A CC ...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A CITYCLUB B1S4 OK")
    # third try with YAPO key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD YP ...")
            # print("UID YP ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT YP ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B1S4, key_YAPO, my_UID)
                        # print("AUTH A YP ...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A YAPO B1S4 OK")
    # Ecrire les blocs et le trailer
    if not (E_Carte and E_Auth):
        print("Echec Auth B1S4")
        Est_Erreur = True
    else:
        # Ecrire firstname B1S4
        # (Est_Erreur, my_data) = rdr.read(B1S4)
        if True: # not Est_Erreur:
            # print("B1S4 avant : ", str(my_data))
            my_data = write_data(firstname)
            # print("MY DATA : ", str(my_data))
            Est_Erreur = rdr.write(B1S4, my_data)
            if not Est_Erreur:
                pass
                # print("   OK - B1S4") # : ", str(rdr.read(B1S4)))
            else:
                print("Erreur Ecriture B1S4")
        # Ecrire Lastname B1S5
        if not Est_Erreur:
            # (Est_Erreur, my_data) = rdr.read(B1S5)
            if True: # not Est_Erreur:
                # print("B1S5 avant : ", str(my_data))
                my_data = write_data(lastname)
                # print("MY DATA : ", str(my_data))
                Est_Erreur = rdr.write(B1S5, my_data)
                if not Est_Erreur:
                    pass
                    # print("   OK - B1S5") #  : ", str(rdr.read(B1S5)))
                else:
                    print("   Erreur Ecriture B1S5")
        # Ecrire clef CC dans le Trailer
        if not Est_Erreur:
            # (Est_Erreur, my_data) = rdr.read(B1S7)
            if True: #not Est_Erreur:
                # print("B1S7 avant : ", str(my_data))
                my_data = Sector_Key_CC
                # print("MY DATA : ", str(my_data))
                Est_Erreur = rdr.write(B1S7, my_data)
                if not Est_Erreur:
                    pass
                    # print("   OK - B1S7")
                else:
                    print("   Erreur Ecriture B1S7")
    # Conclure
    rdr.stop_crypto()
    if debug: print("Stopping crypto1")
    return Est_Erreur
#-------------------------------------------------

#-------------------------------------------------------
def Read_SubScription_End_Date_from_Card(current_UID):
# Lit la Date de Fin d'abonnement dans le secteur B2S8
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    my_LVD = "" # la date de fin d'abonnement
    global debug
    # Try with CC key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST PB")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST PB 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD PB ...")
            # print("UID PB ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT PB ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B2S8, key_CityClub, my_UID)
                        # print("AUTH A PB ...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A CITYCLUB B2S8 OK")
    # Lire
    if not (E_Carte and E_Auth):
        print("Echec Auth B2S8")
        Est_Erreur = True
    else:
        # Lire Subscription End Date dans B2S8
        (Est_Erreur, my_data) = rdr.read(B2S8)
        if not Est_Erreur:
            my_LVD = read_card(my_data)
    # Conclure
    rdr.stop_crypto()
    if debug: print("Stopping crypto1")
    return Est_Erreur, my_LVD
#-------------------------------------------------

#-------------------------------------------------------
def Write_SubScription_End_Date_to_Card(subscription_end_date, current_UID):
# Ecrit la Date de Fin d'abonnement dans le secteur B2S8
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    global debug
    # first try with Public key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST PB")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST PB 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD PB ...")
            # print("UID PB ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT PB ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B2S8, key_public, my_UID)
                        # print("AUTH A PB ...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A PUBLIC B2S8 OK")
    # second try with Public key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD CC ...")
            # print("UID CC ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT CC ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B2S8, key_CityClub, my_UID)
                        # print("AUTH A CC ...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A CITYCLUB B2S8 OK")
    # third try with YAPO key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD YP ...")
            # print("UID YP ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT YP ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B2S8, key_YAPO, my_UID)
                        # print("AUTH A YP ...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A YAPO B2S8 OK")
    # Ecrire les blocs et le trailer
    if not (E_Carte and E_Auth):
        print("Echec Auth B2S8")
        Est_Erreur = True
    else:
        # Ecrire Subscription End Date dans B2S8
        # (Est_Erreur, my_data) = rdr.read(B2S8)
        if True: # not Est_Erreur:
            # print("B2S8 avant : ", str(my_data))
            my_data = write_data(subscription_end_date)
            # print("MY DATA : ", str(my_data))
            Est_Erreur = rdr.write(B2S8, my_data)
            if not Est_Erreur:
                pass
                # print("   OK - B2S8") #  : ", str(rdr.read(B2S8)))
            else:
                print("Erreur Ecriture B2S8")
        # Ecrire clef CC dans le Trailer
        if not Est_Erreur:
            # (Est_Erreur, my_data) = rdr.read(B2S11)
            if True: #  not Est_Erreur:
                my_data = Sector_Key_CC
                Est_Erreur = rdr.write(B2S11, my_data)
                if not Est_Erreur:
                    pass
                    # print("   OK - B2S11")
                else:
                    print("   Erreur Ecriture B2S11")
    # Conclure
    rdr.stop_crypto()
    if debug: print("Stopping crypto1")
    return Est_Erreur
#-------------------------------------------------------

#-------------------------------------------------------
def Read_Last_Visit_Date_from_Card(current_UID):
# Ecrit la Date de dernière visite dans le secteur B3S12
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    my_LVD = ""
    global debug
    # first try with Public key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST PB")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST PB 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD PB ...")
            # print("UID PB ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT PB ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B3S12, key_CityClub, my_UID)
                        # print("AUTH A PB ...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A CITYCLUB B3S12 OK")
    # Lire
    if not (E_Carte and E_Auth):
        print("Echec Auth B3S12")
        Est_Erreur = True
    else:
        # Lire Subscription End Date dans B3S12
        (Est_Erreur, my_data) = rdr.read(B3S12)
        if not Est_Erreur:
            my_LVD = read_card(my_data)
    # Conclure
    rdr.stop_crypto()
    if debug:  print("Stopping crypto1")
    return Est_Erreur, my_LVD
#-------------------------------------------------------

#-------------------------------------------------------
def Write_Last_Visit_Date_to_Card(last_visit_date, current_UID):
# Ecrit la Date de dernière visite dans le secteur B3S12
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    global debug
    # first try with Public key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST PB")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST PB 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD PB ...")
            # print("UID PB ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT PB ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B3S12, key_public, my_UID)
                        # print("AUTH A PB ...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A PUBLIC B3S12 OK")
    # second try with Public key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD CC ...")
            # print("UID CC ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT CC ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B3S12, key_CityClub, my_UID)
                        # print("AUTH A CC ...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A CITYCLUB B3S12 OK")
    # third try with YAPO key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD YP ...")
            # print("UID YP ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT YP ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B3S12, key_YAPO, my_UID)
                        # print("AUTH A YP ...")
                        if not error_a:
                            E_Auth = True
                            if debug: print("AUTH A YAPO B3S12 OK")
    # Ecrire les blocs et le trailer
    if not (E_Carte and E_Auth):
        print("Echec Auth B3S12")
        Est_Erreur = True
    else:
        # Ecrire Subscription End Date dans B3S12
        # (Est_Erreur, my_data) = rdr.read(B3S12)
        if True: #  not Est_Erreur:
            # print("B3S12 avant : ", str(my_data))
            my_data = write_data(String_replace(last_visit_date))
            # print("MY DATA : ", str(my_data))
            Est_Erreur = rdr.write(B3S12, my_data)
            if not Est_Erreur:
                pass
                # print("   OK - B3S12") #  : ", str(rdr.read(B3S12)))
            else:
                print("Erreur Ecriture B3S12")
        # Ecrire clef CC dans le Trailer
        if not Est_Erreur:
            # (Est_Erreur, my_data) = rdr.read(B3S15)
            if True: #  not Est_Erreur:
                my_data = Sector_Key_CC
                Est_Erreur = rdr.write(B3S15, my_data)
                if not Est_Erreur:
                    pass
                    # print("   OK - B3S15")
                else:
                    print("   Erreur Ecriture B3S15")
    # Conclure
    rdr.stop_crypto()
    if debug:  print("Stopping crypto1")
    return Est_Erreur
#-------------------------------------------------
#-------------------------------------------------
# Detect Carte Func
#********************************************************
def Detect_Card():
# si une carte est détectée, essaye plusieurs authentification pour renvoyer l'UID, et le Secteur B3S12
    E_Carte = False
    E_Auth = False
    my_UID = []
    B3S12_data = []
    global last_UID
    global last_UID_datetime
    global debug
    # first try with CC key
    if True: # (not E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if error_q:
            (error_q, data) = rdr.request()
        if not error_q:
            if debug: print("\nDetected: " + format(data, "02x"))
##            declenchebuzzer() # bip d'indication de lecture de la carte
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if error_u:
                #if debug: print("Card read UID: ",my_UID)
                (error_u, my_UID) = rdr.anticoll()
                #if error_u: (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if debug: print("Selecting UID " + str(my_UID))
                error_s = rdr.select_tag(my_UID)
                if not error_s:
                    if (my_UID == last_UID) and ((datetime.datetime.utcnow() - last_UID_datetime).total_seconds() <= 10 ): # moins de 10 secondes avec le même UID
                        E_Carte = False
                        # next_action = "" # boucler sans faire d'autres traitements
                        # last_UID_datetime = datetime.datetime.utcnow() # mémoriser de nouveau la date/heure du passage
                        declenchebuzzer3() # bip-bip-bip
                        if debug: print("UID déjà lu dans les 10 secondes : ", my_UID)
                        # réafficher le dernier message de l'écran
                        if I2C_LINE == "4":
                            if last_message_l2== "DEJA LU < 10s !":
                                if LCD_ON:
                                    msg(last_message_l1,"DEJA LU < 10s !",last_message_l3, last_message_l4)

                            else:
                                if LCD_ON:
                                    msg(last_message_l1,"DEJA LU < 10s !",last_message_l3,last_message_l4)
                                else:
                                    print(last_message_l1,"DEJA LU < 10s !",last_message_l3,last_message_l4)
                        else:
                            if LCD_ON:
                                msg("DEJA LU < 10s !",last_message_l2,"","")
                            else:
                                print("UID déjà lu dans les 10 secondes : ", my_UID)
                        Wait_for_Card_Removing(tag_uid)
                    else: # initialiser last_UID et last_UID_lasttime
                        last_UID = my_UID
                        last_UID_datetime = datetime.datetime.utcnow()
                        # next_action = "UID" # Traitement de l'UID
                        error_a = rdr.card_auth(rdr.auth_a, B3S12, key_CityClub, my_UID)
                        if debug: print("Authenticate A CC ...")
                        if not error_a:
                            if debug: print("READ CC ...")
                            (error_r, B3S12_data) = rdr.read(B3S12)
                            if not error_r:
                                if debug: print("\nReading block B3S12 with CityClub key : " + str(B3S12_data))
                                E_Auth = True
                                rdr.stop_crypto()
                                if debug: print("Stopping crypto1")
##    # second try with Public key
##    if (E_Carte) and (not E_Auth):
##        (error_q, data) = rdr.request()
##        if not error_q:
##            # print("\nCARD PB ...")
##            E_Carte = True
##            # print("UID PB ...")
##            (error_u, my_UID) = rdr.anticoll()
##            if not error_u:
##                error_s = rdr.select_tag(my_UID)
##                if not error_s:
##                    error_a = rdr.card_auth(rdr.auth_a, B3S12, key_public, my_UID)
##                    if not error_a:
##                        (error_r, B3S12_data) = rdr.read(B3S12)
##                        if not error_r:
##                            print("\nReading block B3S12 with Public key : " + str(B3S12_data))
##                            E_Auth = True
##                            rdr.stop_crypto()
##    # third try with YAPO key
##    if (E_Carte) and (not E_Auth):
##        (error_q, data) = rdr.request()
##        if not error_q:
##            E_Carte = True
##            # print("UID YAPO ...")
##            (error_u, my_UID) = rdr.anticoll()
##            if not error_u:
##                error_s = rdr.select_tag(my_UID)
##                if not error_s:
##                    error_a = rdr.card_auth(rdr.auth_a, B3S12, key_YAPO, my_UID)
##                    if not error_a:
##                        (error_r, B3S12_data) = rdr.read(B3S12)
##                        if not error_r:
##                            print("\nReading block B3S12 with YAPO key : " + str(B3S12_data))
##                            E_Auth = True
##                            rdr.stop_crypto()
    # Renvoyer Réponse
    if my_UID == []: # au cas où la carte n'a pas été correctement détectée
        E_Carte = False
    return (E_Carte, E_Auth, my_UID, B3S12_data)
#********************************************************
#********************************************************
# Attend jusqu'à ce que la carte soit retirée
def Wait_for_Card_Removing(old_UID):
    continue_waiting = True
    # rdr.stop_crypto()
    data = []
    while continue_waiting:
        (error_q, data) = rdr.request()
        if error_q:
            (error_q, data) = rdr.request()
        # print("Request : ", error_q)
        if not error_q:
            (error_u, my_UID) = rdr.anticoll()
            if error_u:
               (error_u, my_UID) = rdr.anticoll()
               #continue_waiting = True
##            if debug: print("UID: ", error_u, old_UID, my_UID)
            if not error_u:
                continue_waiting = (old_UID == my_UID)
##            else:
##                continue_waiting = False
        else:
            continue_waiting = False
        if continue_waiting:
            # print("+", end="")
            time.sleep(0.5)
    # en sortie
    rdr.stop_crypto()
    time.sleep(1) # afin de laisser le message affiché à l'écran
    print("Carte retirée ...\n")

print("connected: ",is_connected())
if __name__ == '__main__':     # Program start from here
  setup()
  declenchebuzzer3()
  if True:
      while continue_reading:
        if boucle_compteur % 10 == 0 : print("Attente Carte :", boucle_compteur, "...")
        strtoday= datetime.datetime.today() # qui sera affiché sur l'écran
        # Display Message LCD L1 et L2 (ne pas modifier pour ne pas afficher dans le terminal)
        if LCD_ON: lcd_string(strtoday.strftime("%Y-%m-%d %H:%M:%S"),LCD_LINE_1)
        if LCD_ON: lcd_string("CARTE ?  " + rbnom,LCD_LINE_2)
        if LCD_ON and I2C_LINE =="4": lcd_string("PUIS PATIENTER",LCD_LINE_3)
        if LCD_ON and I2C_LINE =="4": lcd_string(" ",LCD_LINE_4)
        next_action = "NEW_DETECT"
        # Détection de la Carte : si une carte est présentée, retourne l'UID et
        if next_action == "NEW_DETECT":
            (Est_Carte, Est_Auth, tag_uid, data_bloc) = Detect_Card()
            if Est_Carte and len(tag_uid) >= 4:
                declenchebuzzer() # bip d'indication de lecture de la carte
                last_passage = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                Card_Insert = 1
                GCP_UID = '%02X' % tag_uid[0] + '%02X' % tag_uid[1] + '%02X' % tag_uid[2] + '%02X' % tag_uid[3]
                print ("\nCarte insérée", "\nUID de la carte : ",GCP_UID)
                #(data_bloc == None) or (data_bloc[0] != 50) or (data_bloc[1] != 48): # 20xx-xx-xx ...
                if not Est_Auth:
                    last_visit = ""
                else:
                    back_Data = read_card(data_bloc)
                    last_visit=back_Data
                if back_Data!="--::" and back_Data!="": last_visit= from_card(back_Data)
                print("Date dernier passage depuis la Carte: [" + last_visit + "]")
                next_action ="WS" # faire appel au WS avec lastvisit initialisé
        # Appel Web service
        if next_action == "WS":
            last_passage = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            if LCD_ON and I2C_LINE == "4":
                lcd_string(str(GCP_UID)+" "+rbnom,LCD_LINE_2)
                lcd_string("PATIENTEZ...",LCD_LINE_3)
            elif LCD_ON and I2C_LINE == "2":
                lcd_string(str(GCP_UID)+" "+rbnom,LCD_LINE_1)
                lcd_string("PATIENTEZ...",LCD_LINE_2)
            DATA ='{"idreader":"' + rbnom + '","uid":"' + GCP_UID + '","mode":"online","rpitime":"' + get_rpi_time() + '","lastvisit":"' + last_visit + '"}'
            print("WS : Sent Data : ",datetime.datetime.now().strftime("%H:%M:%S"),"\n",DATA)
            response,mode=Appel_Web_Service(DATA) # on récupère en response le json data
            if debug: print("Réponse du WS:",response)
            # on récupère dans mode : pas200, online ou exception
            # mode = "pas200" # pour les tests
            if mode == "online":
                print("ON LINE, Réponse du WS:",datetime.datetime.now().strftime("%H:%M:%S"),"\n", response.text)
                python_obj=json.loads(response.text)
                mode = python_obj['mode'] ## toujours "online"
                firstname = python_obj['firstname']
                lastname = python_obj['lastname']
                result= python_obj['result'] # OK ou STOP
                enddate = python_obj['enddate']
                newvisit = python_obj['newvisit']
                next_action = "TT_ONLINE" # mettre à jour la carte et ouvrir passage
                # déjà défini dans l'appel à Appel_Web_Service : Can_Try_Offline_Upload = True # si Vrai, tenter de remonter des infos OFF_LINE
            elif mode == "pas200":
                print("Status Error, Code Réponse du WS:", response.status_code)
                next_action = "TT_OFFLINE"
                # déjà défini dans l'appel à Appel_Web_Service : Can_Try_Offline_Upload = False # si Faux, ne pas tenter de remonter des infos OFF_LINE
                # si carte initialisée, récupérer les info, insérer dans la base et autoriser ou pas le passage
                # si carte pas initialisée, accueil
            elif mode == "exception":
                print("Exception sur le WebService, timeout ?",datetime.datetime.now().strftime("%H:%M:%S"))
                next_action = "TT_OFFLINE"
                # déjà défini dans l'appel à Appel_Web_Service : Can_Try_Offline_Upload = False # si Faux, ne pas tenter de remonter des infos OFF_LINE
                # voir avant
            else:
                print("WebService retourne mode inconnu : ", mode)
                next_action = "TT_OFFLINE"
                Can_Try_Offline_Upload = False # si Faux, ne pas tenter de remonter des infos OFF_LINE

        # Traitement ON LINE
        if next_action == "TT_ONLINE":
            print("Traitement ON LINE :")
            # result = "OK" # pour les tests
            # Autoriser ou pas le passage en fonction de result, initialiser ou mettre à jour la carte
            # Traitement de la carte
            if result == "OK":
                Kein_Erreur = False
                if last_visit == "": # indique que la carte n'était pas initialisée
                    Kein_Erreur = Write_lastname_firstname_to_Card(lastname, firstname, tag_uid)
                    print("Write to Card Lastname / Firstname [" + lastname + "] [" + firstname + "] :" , "OK" if not Kein_Erreur else "Erreur")
                    if not Kein_Erreur:
                        Kein_Erreur = Write_SubScription_End_Date_to_Card(enddate, tag_uid)
                        print("Write to Card Subscription End Date [" + enddate + "] :", "OK" if not Kein_Erreur else "Erreur")
                        if not Kein_Erreur:
                            Kein_Erreur = Write_Last_Visit_Date_to_Card(newvisit, tag_uid)
                            print("Write to Card Last Visit Date [" + newvisit + "] :", "OK" if not Kein_Erreur else "Erreur")
                else: # si la carte était initialisée avec un last_visit != ""
                    Kein_Erreur = Write_Last_Visit_Date_to_Card(newvisit, tag_uid)
                    print("Write to Card Last Visit Date [" + newvisit + "] :", "OK" if not Kein_Erreur else "Erreur")
            # Déclencher le relais / LED
            Traitement_OK_STOP(result);
            if firstname == "" and lastname == "":
                LCD_2 = str(GCP_UID)+" "+rbnom
            else:
                LCD_2 = firstname+" "+lastname
            # Affichage du Message
            if 'X02' in result :
                if I2C_LINE == "4":
                    if LCD_ON:
                        msg(datetime.datetime.today().strftime("%Y-%m-%d %H:%M"),"CARTE: "+str(GCP_UID)+" X02","STOP INCONNU !","")
                    else:
                        print("(LCD OFF):",datetime.datetime.today().strftime("%Y-%m-%d %H:%M"),"CARTE: "+str(GCP_UID)+" X02","STOP INCONNU !")
                else:
                    if LCD_ON:
                        msg(GCP_UID + " X02","STOP INCONNU !","","")
                    else:
                        print("(LCD OFF):",GCP_UID + " X02","STOP INCONNU !")
            elif 'X04' in result :
                if not len(enddate)== 0:
                    poub_date = datetime.datetime.strptime(enddate,"%Y-%m-%d")
                else:
                    poub_date=datetime.datetime.today()
                if I2C_LINE == "4":
                    if LCD_ON:
                        msg(get_rpi_time(),GCP_UID + " X04",firstname+" "+lastname,"STOP "+poub_date.strftime("%d-%m-%Y"))
                    else:
                        print("(LCD OFF):",get_rpi_time(),GCP_UID + " X04",firstname+" "+lastname,"STOP "+poub_date.strftime("%d-%m-%Y"))
                else:
                    if LCD_ON:
                        msg(LCD_2,"STOP "+poub_date.strftime("%d-%m-%Y"),"","")
                    else:
                        print("(LCD OFF):",LCD_2,"STOP "+poub_date.strftime("%d-%m-%Y"))
            else:
                if I2C_LINE == "4":
                    if LCD_ON:
                        msg(get_rpi_time(),LCD_2,result,enddate)
                    else:
                        print("(LCD OFF):",get_rpi_time(),LCD_2,result,enddate)
                else:
                    if LCD_ON:
                        msg(LCD_2,result+ "   "+enddate,"","")
                    else:
                        print("(LCD OFF):",LCD_2,result+ "   "+enddate,"","")
            next_action = "" # dernier traitement avant de boucler
        # Traitement OFFLINE
        if next_action == "TT_OFFLINE":
            print("Traitement OFF LINE : ")
            next_action = "" # dernier traitement avant de boucler
            mode = "offline" # utilisé pour insérer dans la base
            if last_visit == "": # indique que la carte n'était pas initialisée
                Traitement_OK_STOP("BAD") # si pas "OK", va allumer la LED rouge
                if I2C_LINE == "4":
                    if LCD_ON:
                        msg(get_rpi_time(),"CARTE: "+str(GCP_UID),"OFFLINE", "VOIR ACCUEIL")
                    else:
                        print("(LCD OFF):",get_rpi_time(),"CARTE: "+str(GCP_UID),"OFFLINE", "VOIR ACCUEIL")
                else:
                    if LCD_ON:
                        msg("OFFLINE", "VOIR ACCUEIL","","")
                    else:
                        print("(LCD OFF):","OFFLINE", "VOIR ACCUEIL")
            else: # Carte initialisée
                resultat="STOP X02" ; lastname = "" ; firstname = "" ; enddate = "" ; lastvisit = ""
                # Lire le Nom et le Prénom
                Kein_Erreur, lastname, firstname = Read_lastname_firstname_from_Card(tag_uid)
                print("Read from Card Lastname / Firstname : [" + lastname + "] [" + firstname + "] :" , "OK" if not Kein_Erreur else "Erreur")
                if not Kein_Erreur:
                    Kein_Erreur, enddate = Read_SubScription_End_Date_from_Card(tag_uid)
                    print("Read from Card Subscription End Date : [" + enddate + "] :", "OK" if not Kein_Erreur else "Erreur")
                    if not Kein_Erreur:
                        Kein_Erreur, lastvisit = Read_Last_Visit_Date_from_Card(tag_uid)
                        if lastvisit!="--::" and lastvisit!="":
                            lastvisitdb=from_card(lastvisit)
                        else:
                            lastvisitdb= get_rpi_time()
                        lastvisit=lastvisitdb
                        print("Read from Card Last Visit Date : [" + lastvisit + "] :", "OK" if not Kein_Erreur else "Erreur")
                        if not Kein_Erreur:
                            resultat = Date_Comparison(enddate) # OK ou STOP en fonction de l'expiration de la carte
                # Insérer le passage dans la base
                if resultat !="STOP X02": # Carte Inconnue, valeur par défaut si on a pas réussi à lire la carte, ou carte arrachée
                    A_R='OUI' ; A_A='NON'
                    insert_passage(rbnom, GCP_UID, lastname, firstname, enddate, get_rpi_time(), lastvisitdb, A_A, A_R, resultat)
                    Traitement_OK_STOP(resultat)
                    if I2C_LINE == "4":
                        if LCD_ON:
                            msg(get_rpi_time(),str(GCP_UID),firstname + " " + lastname, resultat + "   " + change_date_format(enddate))
                        else:
                            print("(LCD OFF):",get_rpi_time(),str(GCP_UID),firstname + " " + lastname, resultat + "   " + change_date_format(enddate))
                    else:
                        if LCD_ON:
                            msg(firstname + " " + lastname, resultat + "   " + change_date_format(enddate),"","")
                        else:
                            print("(LCD OFF):",firstname + " " + lastname, resultat + "   " + change_date_format(enddate),"","")
                else:
                    A_R='NON' ; A_A='OUI'
                    insert_passage(rbnom, GCP_UID, lastname, firstname, enddate, get_rpi_time(), lastvisitdb, A_A, A_R, resultat)
                    Traitement_OK_STOP("BAD") # si pas "OK", va allumer la LED rouge
                    if I2C_LINE == "4":
                        if LCD_ON:
                            msg(get_rpi_time(),str(GCP_UID),"OFFLINE", "VOIR ACCUEIL")
                        else:
                            print("(LCD OFF):",get_rpi_time(),str(GCP_UID),"OFFLINE", "VOIR ACCUEIL")
                    else:
                        if LCD_ON:
                            msg("OFFLINE", "VOIR ACCUEIL","","")
                        else:
                            print("(LCD OFF):","OFFLINE", "VOIR ACCUEIL")
        # cmpt
        boucle_compteur = boucle_compteur + 1
        # Tous les minutes, faire un ping vers le serveur local CityClub
        if ((datetime.datetime.utcnow() - LAST_LOCAL_DATE_TIME_PING_CC).total_seconds() >= 60) and Card_Insert == 0:
            # Réinitialiser le Compteur
            boucle_compteur = 0
            LAST_LOCAL_DATE_TIME_PING_CC = datetime.datetime.utcnow()
            if debug: print("LAST LOCAL DATETIME PING CC AT : ",LAST_LOCAL_DATE_TIME_PING_CC.strftime("%H:%M:%S"))
            pCC=threading.Thread(name='pCC',target=Ping_Local_CityClub)
            pCC.start()
            pCC.join(5) # Attend 5 secondes que le thread se termine

        # Tous les 5 min faire un ping vers YAPO
        if ((datetime.datetime.utcnow() - LAST_LOCAL_DATE_TIME_PING_PY).total_seconds() >= 30) and Card_Insert == 0:
            # Réinitialisation
            LAST_LOCAL_DATE_TIME_PING_PY = datetime.datetime.utcnow()
            if debug: print("LAST LOCAL DATETIME PING YAPO AT : ",LAST_LOCAL_DATE_TIME_PING_PY.strftime("%H:%M:%S"))
            pLast_pass = threading.Thread(name='pLast_pass',target=Send_last_passage, args=(last_passage,))
            pLast_pass.start()
            pLast_pass.join(5) # Attend 5 secondes que le thread se termine

        # Tous les 10 min Verifier Mise à Jour Du programme
        if ((datetime.datetime.utcnow() - LAST_LOCAL_DATE_TIME_PING_UPDATE).total_seconds() >= 600) and Card_Insert == 0:
            LAST_LOCAL_DATE_TIME_PING_UPDATE = datetime.datetime.utcnow()
            if debug: print("LAST LOCAL DATETIME UPDATE: ",LAST_LOCAL_DATE_TIME_PING_UPDATE.strftime("%H:%M:%S"))
            p_maj= threading.Thread(name='p_maj',target=Check_New_Version)
            p_maj.start()
            p_maj.join(5) # Attend 5 secondes que le thread se termine
        # Remonter les passages off_line
        if Can_Try_Offline_Upload == True and Card_Insert == 0:
            traitement_post_online()
            # Attente entre 2 boucles principales
            time.sleep(0.2)
        if Card_Insert == 1:
            Card_Insert = 0 # pour ne pas recommencer à la prochaine boucle sans carte
            Wait_for_Card_Removing(tag_uid)
        
#  except KeyboardInterrupt:  # When 'Ctrl+C' is pressed, the child program destroy() will be  executed.
#    destroy()
#  except Exception as e:
#    print("Exception: ",e)
#    insert_LOG(get_rpi_time(),e)
#    if LCD_ON: msg("PRG REDEMARRE", "ESSAYEZ + TARD",get_rpi_time(),"")
#    print("cleaning up")
#    GPIO.cleanup()
#

#RUN apt-get update \
#  && apt-get install -y sudo \
#  && apt-get install -y perl --no-install-recommends \
#  # Install apt-get allowing subsequent package configuration
#  && apt-get install -y apt-utils \
#  # Install minimal admin utils
#  && apt-get install -y less nano procps git 
