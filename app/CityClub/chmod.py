import subprocess as sp
import MySQLdb

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


#********************************************************
def Insert_Param_autostart():
    try:
        db = MySQLdb.connect("127.0.0.1", "yapo", "pipi", "rpi")
        curs=db.cursor()
        curs.execute("""INSERT INTO `Parametre` (`id`, `Param_Nom`, `Param_Valeur`) VALUES 
       (11, 'autostart',   '0') # passera à 1 après mise à jour de l'autostart
        ;""")
        db.commit()  # accept the changes
        # print("Table Parametre Updated")
        db.close()
    except Exception as e:
        # print(e)
        db.close()

#*******************************************************

#********************************************************
def Update_Param_autostart():
    try:
        db = MySQLdb.connect("127.0.0.1", "yapo", "pipi", "rpi")
        curs=db.cursor()
        curs.execute("""REPLACE INTO `Parametre` (`id`, `Param_Nom`, `Param_Valeur`) VALUES 
       (11, 'autostart', 1) 
        ;""")
        db.commit()  # accept the changes
        # print("Table Parametre Updated")
        db.close()
    except Exception as e:
        print(e)
        db.close()
#*******************************************************

Insert_Param_autostart()
# Update_Param_autostart()
print("Dévérouillage AutoStart :",Chmod_autostart())

