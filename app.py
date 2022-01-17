from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, Response, jsonify
import io
import csv
import json
import os
from os.path import join, dirname, realpath
from fpdf import FPDF
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import hashlib
import qrcode 
import csv

app = Flask(__name__)

# CONNECTING WITH PYMYSQL: Open database connection
db_connection = pymysql.connect(host='localhost', 
                                user='root', 
                                passwd='', 
                                db='retiros_2') 

# settings
app.secret_key = 'mysecretkey'

UPLOAD_FOLDER = 'static/file/'
app.config['UPLOAD_FOLDER'] =  UPLOAD_FOLDER

#Direccion Principal 
@app.route('/')
def Index():
  try:
    if 'FullName' in session:
      return redirect('/home')
    else:
      return render_template('index.html')
  except:
      return render_template('index.html')

#Valida de usuario
@app.route('/validar_usuario', methods=['POST'])
def validarusuaro():
    if request.method == 'POST':
      usuario =  request.form['user']
      cur= db_connection.cursor()
      # Read a single record
      sql = "SELECT * FROM `usuarios` WHERE `Usuario`=%s Limit 1"
      cur.execute(sql, (usuario,))
      data = cur.fetchone()
      if len(data) > 0 :
        username = data[1]
        user = data[3]
        return render_template('inicio.html',username=username,user=user)
      else:
        return render_template('index.html')    

#Validacion de Contraseña
@app.route('/validar_contrasena/<user>', methods=['POST'])
def validarcontrasena(user):
    if request.method == 'POST':
      usuario =  user
      password = request.form['password']
      cur= db_connection.cursor()
      # Read a single record
      sql = "SELECT * FROM `usuarios` WHERE `Usuario`=%s Limit 1"
      cur.execute(sql, (usuario,))
      data = cur.fetchone()
      if len(data) > 0 :
          if check_password_hash(data[6],password):
            session['UserName'] = data[1]
            session['FullName'] = data[1] + data[2]
            session['User'] = data[3]
            session['FcName'] = data[4]
            session['SiteName'] = data[5]
            session['Rango'] = data[7]
            return redirect('/home')
          else:
            flash('Contraseña Incorrecta')
            return render_template('index.html')
      else:
        return render_template('index.html')   
#Pagina Principal
@app.route('/home',methods=['POST','GET'])
def home():
  if 'FullName' in session:
    return render_template('home.html',Datos = session)
  else:
    flash("Inicia Sesion")
    return render_template('index.html')

#formulario ordenes no Procesables 
@app.route('/Retiros',methods=['POST','GET'])
def No_procesable_form():
  if 'FullName' in session:
    return render_template('form/retiros.html',Datos = session)
  else:
    flash("Inicia Sesion")
    return render_template('index.html')
#Redirigie a el Formulario de Registro de Usuarios 
@app.route('/registro',methods=['POST','GET'])
def registro():
  try:
    if session['Rango'] == 'Administrador':
      return render_template('registro.html', Datos = session)
    else:
      flash("Acseso Denegado")
    return render_template('index.html')
  except:
    flash("Inicia Secion")
    return render_template('index.html')

#Registro de Usuarios 
@app.route('/registrar',methods=['POST'])
def registrar():
  try:
      if request.method == 'POST':
        nombre =  request.form['nombre']
        apellido =  request.form['apellido']
        rango = request.form['rango']
        ltrabajo =  request.form['ltrabajo']
        cdt = request.form['cdt']
        usuario =  request.form['usuario']

        password = _create_password(request.form['pass'])
        password2 = _create_password(request.form['pass2'])
        
        if check_password_hash(password,request.form['pass']) and check_password_hash(password,request.form['pass2']):
          cur= db_connection.cursor()
          # Read a single record
          sql = "SELECT * FROM `usuarios` WHERE `Usuario`=%s Limit 1"
          cur.execute(sql, (usuario,))
          data = cur.fetchone()
          if data != None:
            flash("El Usuario Ya Existe")
            return render_template('registro.html',Datos =session)
          else:
            cur= db_connection.cursor()
            # Create a new record
            sql = "INSERT INTO usuarios (Nombre,Apellido, Usuario, ltrabajo, cdt, contraseña, Rango) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            cur.execute(sql,(nombre,apellido,usuario,ltrabajo,cdt,password,rango,))
            # connection is not autocommit by default. So you must commit to save
            # your changes.
            db_connection.commit()
            flash("Registro Correcto")
            return render_template('registro.html',Datos =session)
        else:
          flash("Las Contraceñas no Cionciden")
          return render_template('registro.html',Datos =session)
  except:
    return render_template('registro.html',Datos =session)
def _create_password(password):
   return generate_password_hash(password,'pbkdf2:sha256:30',30)

# Registro de Salidas Service Center
@app.route('/ubicacion',methods=['POST'])
def registro_s_s():
  # try:
      if request.method == 'POST':
        meli = request.form['meli']
        cur= db_connection.cursor()
        # Read a single record
        sql = "SELECT * FROM solicitud_retiros WHERE meli = %s AND status != \'Cerrado\' LIMIT 1"
        cur.execute(sql, (meli,))
        retiros = cur.fetchone()
        if retiros != None:
          if int(retiros[4]) > int(retiros[7]): 
            numeroOla=retiros[1]
            ubicacion =  'R-'+meli+'-'+str(retiros[3])
            now= datetime.now()
            responsable=session['FullName']
            cur= db_connection.cursor()
            # Create a new record
            sql = "INSERT INTO retiros (nuemro_de_ola, meli, cantidad, ubicacion, responsable, fecha, fecha_hora) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            cur.execute(sql,(numeroOla,meli,1,ubicacion,responsable,now,now,))
            # connection is not autocommit by default. So you must commit to save
            # your changes.
            db_connection.commit()
            piesas= int(retiros[7])+1
            idretiro =int(retiros[0])
            if  piesas < int(retiros[4]):
              status='En Proceso'
            elif  piesas == int(retiros[4]):
              status='Cerrado'
            cur= db_connection.cursor()
            # Create a new record
            sql = "UPDATE solicitud_retiros SET cantidad_susrtida = %s, status = %s, ubicacion = %s WHERE id_tarea_retiros = %s"
            cur.execute(sql,(piesas,status,ubicacion,idretiro,))
            # connection is not autocommit by default. So you must commit to save
            # your changes.
            db_connection.commit()
            session['ubicacionretiro']=ubicacion
            return render_template('actualizacion/finalizado.html',Datos = session)
        cur= db_connection.cursor()
        # Read a single record
        sql = "SELECT * FROM solicitud_donacion WHERE SKU = %s AND status != \'Cerrado\' LIMIT 1 "
        cur.execute(sql, (meli,))
        donacion = cur.fetchone()
        if donacion != None:
          if int(donacion[3]) > int(donacion[7]): 
            numeroOla=donacion[1]
            ubicacion =  'D-'+meli+'-'+str(donacion[10])
            now= datetime.now()
            responsable=session['FullName']
            cur= db_connection.cursor()
            # Create a new record
            sql = "INSERT INTO donacion (nuemro_de_ola, SKU, cantidad, ubicacion, responsable, fecha, fecha_hora) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            cur.execute(sql,(numeroOla,meli,1,ubicacion,responsable,now,now,))
            # connection is not autocommit by default. So you must commit to save
            # your changes.
            db_connection.commit()
            piesas= int(donacion[7])+1
            iddonacion =int(donacion[0])
            if  piesas < int(donacion[3]):
              status='En Proceso'
            elif  piesas == int(donacion[3]):
              status='Cerrado'
            cur= db_connection.cursor()
            # Create a new record
            sql = "UPDATE solicitud_donacion SET cantidad_susrtida = %s, status = %s, ubicacion = %s WHERE id_donacion = %s"
            cur.execute(sql,(piesas,status,ubicacion,iddonacion,))
            # connection is not autocommit by default. So you must commit to save
            # your changes.
            db_connection.commit()
            session['ubicacionretiro']=ubicacion
            return render_template('actualizacion/finalizado.html',Datos = session)
        cur= db_connection.cursor()
        # Read a single record
        sql = "SELECT * FROM ingram WHERE SKU = %s AND estatus != \'Cerrado\' LIMIT 1 "
        cur.execute(sql, (meli,))
        ingram = cur.fetchone()
        if ingram != None:
          if int(ingram[3]) > int(ingram[5]): 
            numeroOla=ingram[1]
            ubicacion =  'I-'+meli+'-'+str(ingram[9])
            now= datetime.now() 
            responsable=session['FullName']
            cur= db_connection.cursor()
            # Create a new record
            sql = "INSERT INTO retirio_ingram (nuemro_de_ola, SKU, cantidad, ubicacion, responsable, fecha, fecha_hora) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            cur.execute(sql,(numeroOla,meli,1,ubicacion,responsable,now,now,))
            # connection is not autocommit by default. So you must commit to save
            # your changes.
            db_connection.commit()
            piesas= int(ingram[5])+1
            idingram =int(ingram[0])
            if  piesas < int(ingram[3]):
              status='En Proceso'
            elif  piesas == int(ingram[4]):
              status='Cerrado'
            cur= db_connection.cursor()
            # Create a new record
            sql = "UPDATE ingram SET piezas_surtidas = %s, estatus = %s, ubicacion = %s WHERE id_solicitud  = %s"
            cur.execute(sql,(piesas,status,ubicacion,idingram,))
            # connection is not autocommit by default. So you must commit to save
            # your changes.
            db_connection.commit()
            session['ubicacionretiro']=ubicacion
            return render_template('actualizacion/finalizado.html',Datos = session)
        flash("No hay Tareas Pendientes")
        return render_template('form/retiros.html',Datos = session)
      else:
        flash("No has enviado un registro")
        return render_template('form/retiros.html',Datos = session)
  # except:
  #   flash("Llena todos los Campos Correctamente")
  #   return render_template('form/retiros.html',Datos = session)

#Cerrar Session
@app.route('/logout')
def Cerrar_session():
  session.clear()
  return render_template('index.html')
#Reportes
@app.route('/Reporte_Retiros/<rowi>',methods=['POST','GET'])
def Reporte_retiros(rowi):
  # try:
      if request.method == 'POST':
        if request.method == 'GET':
          session['rowi_recibo']=rowi
          row1 = int(session['rowi_recibo'])
          row2 = 50
        else:
            row1 = int(session['rowi_recibo'])
            row2 =50
        if 'valor' in request.form:
          if len(request.form['valor'])>0:
            session['filtro_recibo']=request.form['filtro']
            session['valor_recibo']=request.form['valor']
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                daterangef=request.form['datefilter']
                daterange=daterangef.replace("-", "' AND '")
                session['datefilter_recibo']=daterange
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_recibo'],session['valor_recibo'],session['datefilter_recibo'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_recibo'],session['valor_recibo'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter_recibo')
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_recibo'],session['valor_recibo'],row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
          else:
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                if 'valor_recibo' in session:
                  if len(session['valor_recibo'])>0:
                    daterangef=request.form['datefilter']
                    daterange=daterangef.replace("-", "' AND '")
                    session['datefilter_recibo']=daterange
                    cur= db_connection.cursor()
                    # Read a single record
                    sql = "SELECT * FROM retiros WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_recibo'],session['valor_recibo'],session['datefilter_recibo'],row1,row2)
                    cur.execute(sql)
                    data = cur.fetchall()
                    return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
                  else:
                    session.pop('filtro_recibo')
                    session.pop('valor_recibo')
                    cur= db_connection.cursor()
                    # Read a single record
                    sql = "SELECT * FROM retiros WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_recibo'],row1,row2)
                    cur.execute(sql)
                    data = cur.fetchall()
                    return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
                else:
                  daterangef=request.form['datefilter']
                  daterange=daterangef.replace("-", "' AND '")
                  session['datefilter_recibo']=daterange
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retiros WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_recibo'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
              else:
                if 'valor_recibo' in session:
                  session.pop('filtro_recibo')
                  session.pop('valor_recibo')
                  if 'datefilter_recibo' in session:
                    session.pop('datefilter_recibo')
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retiros  LIMIT {}, {}".format(row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retiros  LIMIT {}, {}".format(row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
            else:
              if 'valor_recibo' in session:
                session.pop('filtro_recibo')
                session.pop('valor_recibo')
              if 'datefilter_recibo' in session:
                session.pop('datefilter_recibo')
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retiros  LIMIT {}, {}".format(row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
        elif 'datefilter' in request.form:
          if len(request.form['datefilter'])>0:
            if 'valor_recibo' in session:
              if len(session['valor_recibo'])>0:
                daterangef=request.form['datefilter']
                daterange=daterangef.replace("-", "' AND '")
                session['datefilter_recibo']=daterange
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_recibo'],session['valor_recibo'],session['datefilter_recibo'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
              else:
                session.pop('filtro_recibo')
                session.pop('valor_recibo')
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_recibo'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retiros WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_recibo'],row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
          else:
            if 'valor_recibo' in session:
              session.pop('filtro_recibo')
              session.pop('valor_recibo')
            if 'datefilter_recibo' in session:
                session.pop('datefilter_recibo')
            cur= db_connection.cursor()
            # Read a single record
            sql = "SELECT * FROM retiros  LIMIT {}, {}".format(row1,row2)
            cur.execute(sql)
            data = cur.fetchall()
            return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
        else:
          if 'valor_recibo' in session:
            if len(session['valor_recibo'])>0:
              if 'datefilter_recibo' in session:
                if len(session['datefilter_recibo'])>0:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retiros WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_recibo'],session['valor_recibo'],session['datefilter_recibo'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
                else:
                  session.pop('datefilter_recibo')
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_recibo'],session['valor_recibo'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_recibo'],session['valor_recibo'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data) 
            else:
              session.pop('filtro_recibo')
              session.pop('valor_recibo')
              if 'datefilter_recibo' in session:
                if len(session['datefilter_recibo'])>0:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retiros WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_recibo'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retiros LIMIT {}, {}".format(row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros  LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
          else:
            if 'datefilter_recibo' in session:
              if len(session['datefilter_recibo'])>0:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_recibo'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_recibo')
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
            else:
              if 'datefilter' in request.form:
                if len(request.form['datefilter'])>0:
                  daterangef=request.form['datefilter']
                  daterange=daterangef.replace("-", "' AND '")
                  session['datefilter_recibo']=daterange
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retiros WHERE  fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_recibo'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retiros LIMIT {}, {}".format(row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_retiros.html',Datos = session,Infos =data) 
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data) 
        
      else: 
        if request.method == 'GET':
          session['rowi_recibo']=rowi
          row1 = int(session['rowi_recibo'])
          row2 = 50
        else:
          row1 = int(session['rowi_recibo'])
          row2 =50
        if 'valor_recibo' in session:
          if len(session['valor_recibo'])>0:
            if 'datefilter_recibo' in session:
              if len(session['datefilter_recibo'])>0:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_recibo'],session['valor_recibo'],session['datefilter_recibo'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_recibo')
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_recibo'],session['valor_recibo'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_recibo'],session['valor_recibo'],row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_retiros.html',Datos = session,Infos =data) 
          else:
            session.pop('filtro_recibo')
            session.pop('valor_recibo')
            if 'datefilter_recibo' in session:
              if len(session['datefilter_recibo'])>0:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_recibo'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_recibo')
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retiros LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retiros  LIMIT {}, {}".format(row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
        else:
          if 'datefilter_recibo' in session:
            if len(session['datefilter_recibo'])>0:
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retiros WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_recibo'],row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter_recibo')
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retiros LIMIT {}, {}".format(row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
          else:
            cur= db_connection.cursor()
            # Read a single record
            sql = "SELECT * FROM retiros  LIMIT {}, {}".format(row1,row2)
            cur.execute(sql)
            data = cur.fetchall()
            return render_template('reportes/t_retiros.html',Datos = session,Infos =data)         
  # except:
  #   flash("Inicia Secion")
  #   return render_template('index.html')

@app.route('/Reporte_donacion/<rowi>',methods=['POST','GET'])
def Reporte_donacion(rowi):
  try:
      if request.method == 'POST':
        if request.method == 'GET':
          session['rowi_donacion']=rowi
          row1 = int(session['rowi_donacion'])
          row2 = 50
        else:
            row1 = int(session['rowi_donacion'])
            row2 =50
        if 'valor' in request.form:
          if len(request.form['valor'])>0:
            session['filtro_donacion']=request.form['filtro']
            session['valor_donacion']=request.form['valor']
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                daterangef=request.form['datefilter']
                daterange=daterangef.replace("-", "' AND '")
                session['datefilter_donacion']=daterange
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM donacion WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_donacion'],session['valor_donacion'],session['datefilter_donacion'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_donacion'],session['valor_donacion'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter')
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_donacion'],session['valor_donacion'],row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
          else:
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                if 'valor_donacion' in session:
                  if len(session['valor_donacion'])>0:
                    daterangef=request.form['datefilter']
                    daterange=daterangef.replace("-", "' AND '")
                    session['datefilter_donacion']=daterange
                    cur= db_connection.cursor()
                    # Read a single record
                    sql = "SELECT * FROM donacion WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_donacion'],session['valor_donacion'],session['datefilter_donacion'],row1,row2)
                    cur.execute(sql)
                    data = cur.fetchall()
                    return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
                  else:
                    session.pop('filtro_donacion')
                    session.pop('valor_donacion')
                    cur= db_connection.cursor()
                    # Read a single record
                    sql = "SELECT * FROM donacion WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_donacion'],row1,row2)
                    cur.execute(sql)
                    data = cur.fetchall()
                    return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
                else:
                  daterangef=request.form['datefilter']
                  daterange=daterangef.replace("-", "' AND '")
                  session['datefilter_donacion']=daterange
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM donacion WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_donacion'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
              else:
                if 'valor_donacion' in session:
                  session.pop('filtro_donacion')
                  session.pop('valor_donacion')
                if 'datefilter_donacion' in session:
                  session.pop('datefilter_donacion')
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM donacion  LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
            else:
              if 'valor_donacion' in session:
                session.pop('filtro_donacion')
                session.pop('valor_donacion')
              if 'datefilter_donacion' in session:
                  session.pop('datefilter_donacion')
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM donacion  LIMIT {}, {}".format(row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_donacion.html',Datos = session,Infos =data)

        else:
          if 'valor_donacion' in session:
            if len(session['valor_donacion'])>0:
              if 'datefilter_donacion' in session:
                if len(session['datefilter_donacion'])>0:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM donacion WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_donacion'],session['valor_donacion'],session['datefilter_donacion'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
                else:
                  session.pop('datefilter_donacion')
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_donacion'],session['valor_donacion'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_donacion'],session['valor_donacion'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_donacion.html',Datos = session,Infos =data) 
            else:
              session.pop('filtro_donacion')
              session.pop('valor_donacion')
              if 'datefilter_donacion' in session:
                if len(session['datefilter_donacion'])>0:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM donacion WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_donacion'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM donacion LIMIT {}, {}".format(row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM donacion  LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
          else:
            if 'datefilter_donacion' in session:
              if len(session['datefilter_donacion'])>0:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM donacion WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_donacion'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_donacion')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM donacion LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
            else:
              if 'datefilter' in request.form:
                if len(request.form['datefilter'])>0:
                  daterangef=request.form['datefilter']
                  daterange=daterangef.replace("-", "' AND '")
                  session['datefilter_donacion']=daterange
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM donacion WHERE  fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_donacion'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM donacion LIMIT {}, {}".format(row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_donacion.html',Datos = session,Infos =data) 
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM donacion LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_donacion.html',Datos = session,Infos =data) 
      else: 
        if request.method == 'GET':
          session['rowi_donacion']=rowi
          row1 = int(session['rowi_donacion'])
          row2 = 50
        else:
          row1 = int(session['rowi_donacion'])
          row2 =50
        if 'valor_donacion' in session:
          if len(session['valor_donacion'])>0:
            if 'datefilter_donacion' in session:
              if len(session['datefilter_donacion'])>0:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM donacion WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_donacion'],session['valor_donacion'],session['datefilter_donacion'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_donacion')
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_donacion'],session['valor_donacion'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_donacion'],session['valor_donacion'],row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_donacion.html',Datos = session,Infos =data) 
          else:
            session.pop('filtro_donacion')
            session.pop('valor_donacion')
            if 'datefilter_donacion' in session:
              if len(session['datefilter_donacion'])>0:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM donacion WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_donacion'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_donacion')
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM donacion LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM donacion  LIMIT {}, {}".format(row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
        else:
          if 'datefilter_donacion' in session:
            if len(session['datefilter_recibo'])>0:
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM donacion WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_donacion'],row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter_donacion')
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM donacion LIMIT {}, {}".format(row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_donacion.html',Datos = session,Infos =data)
          else:
            cur= db_connection.cursor()
            # Read a single record
            sql = "SELECT * FROM donacion  LIMIT {}, {}".format(row1,row2)
            cur.execute(sql)
            data = cur.fetchall()
            return render_template('reportes/t_donacion.html',Datos = session,Infos =data)         
  except:
    flash("Inicia Secion")
    return render_template('index.html')

@app.route('/Reporte_Ingram/<rowi>',methods=['POST','GET'])
def Reporte_ingram(rowi):
  try:
      if request.method == 'POST':
        if request.method == 'GET':
          session['rowi_ingram']=rowi
          row1 = int(session['rowi_ingram'])
          row2 = 50
        else:
            row1 = int(session['rowi_ingram'])
            row2 =50
        if 'valor' in request.form:
          if len(request.form['valor'])>0:
            session['filtro_ingram']=request.form['filtro']
            session['valor_ingram']=request.form['valor']
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                daterangef=request.form['datefilter']
                daterange=daterangef.replace("-", "' AND '")
                session['datefilter_ingram']=daterange
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_ingram'],session['valor_ingram'],session['datefilter_ingram'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_ingram'],session['valor_ingram'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter_ingram')
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_ingram'],session['valor_ingram'],row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
          else:
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                if 'valor_ingram' in session:
                  if len(session['valor_ingram'])>0:
                    daterangef=request.form['datefilter']
                    daterange=daterangef.replace("-", "' AND '")
                    session['datefilter_ingram']=daterange
                    cur= db_connection.cursor()
                    # Read a single record
                    sql = "SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_ingram'],session['valor_ingram'],session['datefilter_ingram'],row1,row2)
                    cur.execute(sql)
                    data = cur.fetchall()
                    return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
                  else:
                    session.pop('filtro_ingram')
                    session.pop('valor_ingram')
                    cur= db_connection.cursor()
                    # Read a single record
                    sql = "SELECT * FROM retirio_ingram WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_ingram'],row1,row2)
                    cur.execute(sql)
                    data = cur.fetchall()
                    return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retirio_ingram WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_ingram'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
              else:
                if 'valor_ingram' in session:
                  session.pop('filtro_ingram')
                  session.pop('valor_ingram')
                if 'datefilter_ingram' in session:
                  session.pop('datefilter_ingram')
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram  LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
            else:
              if 'valor_ingram' in session:
                session.pop('filtro_ingram')
                session.pop('valor_ingram')
              if 'datefilter_ingram' in session:
                session.pop('datefilter_ingram')
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retirio_ingram  LIMIT {}, {}".format(row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
        else:
          if 'valor_ingram' in session:
            if len(session['valor_ingram'])>0:
              if 'datefilter_ingram' in session:
                if len(session['datefilter_ingram'])>0:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_ingram'],session['valor_ingram'],session['datefilter_ingram'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
                else:
                  session.pop('datefilter_ingram')
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_ingram'],session['valor_ingram'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_ingram'],session['valor_ingram'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_ingram.html',Datos = session,Infos =data) 
            else:
              session.pop('filtro_ingram')
              session.pop('valor_ingram')
              if 'datefilter_ingram' in session:
                if len(session['datefilter_ingram'])>0:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retirio_ingram WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_ingram'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retirio_ingram LIMIT {}, {}".format(row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram  LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
          else:
            if 'datefilter_ingram' in session:
              if len(session['datefilter_ingram'])>0:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_ingram'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_ingram')
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
            else:
              if 'datefilter' in request.form:
                if len(request.form['datefilter'])>0:
                  daterangef=request.form['datefilter']
                  daterange=daterangef.replace("-", "' AND '")
                  session['datefilter_ingram']=daterange
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retirio_ingram WHERE  fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_ingram'],row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  # Read a single record
                  sql = "SELECT * FROM retirio_ingram LIMIT {}, {}".format(row1,row2)
                  cur.execute(sql)
                  data = cur.fetchall()
                  return render_template('reportes/t_ingram.html',Datos = session,Infos =data) 
              else:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_ingram.html',Datos = session,Infos =data) 
      else: 
        if request.method == 'GET':
          session['rowi_ingram']=rowi
          row1 = int(session['rowi_ingram'])
          row2 = 50
        else:
          row1 = int(session['rowi_ingram'])
          row2 =50
        if 'valor_ingram' in session:
          if len(session['valor_ingram'])>0:
            if 'datefilter_ingram' in session:
              if len(session['datefilter_ingram'])>0:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['filtro_ingram'],session['valor_ingram'],session['datefilter_ingram'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_ingram')
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_ingram'],session['valor_ingram'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}".format(session['filtro_ingram'],session['valor_ingram'],row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_ingram.html',Datos = session,Infos =data) 
          else:
            session.pop('filtro_ingram')
            session.pop('valor_ingram')
            if 'datefilter_ingram' in session:
              if len(session['datefilter_ingram'])>0:
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_ingram'],row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_ingram')
                cur= db_connection.cursor()
                # Read a single record
                sql = "SELECT * FROM retirio_ingram LIMIT {}, {}".format(row1,row2)
                cur.execute(sql)
                data = cur.fetchall()
                return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retirio_ingram  LIMIT {}, {}".format(row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
        else:
          if 'datefilter_ingram' in session:
            if len(session['datefilter_ingram'])>0:
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retirio_ingram WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}".format(session['datefilter_ingram'],row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter_ingram')
              cur= db_connection.cursor()
              # Read a single record
              sql = "SELECT * FROM retirio_ingram LIMIT {}, {}".format(row1,row2)
              cur.execute(sql)
              data = cur.fetchall()
              return render_template('reportes/t_ingram.html',Datos = session,Infos =data)
          else:
            cur= db_connection.cursor()
            # Read a single record
            sql = "SELECT * FROM retirio_ingram  LIMIT {}, {}".format(row1,row2)
            cur.execute(sql)
            data = cur.fetchall()
            return render_template('reportes/t_ingram.html',Datos = session,Infos =data)         
  except:
    flash("Inicia Secion")
    return render_template('index.html')

@app.route('/csvretiros',methods=['POST','GET'])
def crear_csvretiros():
    site=session['SiteName']
    row1 = 0
    row2 =5000
    if 'valor_recibo' in session:
      if len(session['valor_recibo'])>0:
        if 'datefilter_recibo' in session:
          if len(session['datefilter_recibo'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM retiros WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_recibo'],session['valor_recibo'],session['datefilter_recibo'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_recibo'],session['valor_recibo'],row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_recibo'],session['valor_recibo'],row1,row2))
          data = cur.fetchall()
      else:
        if 'datefilter_recibo' in session:
          if len(session['datefilter_recibo'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM retiros WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_recibo'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM retiros LIMIT {}, {}'.format(row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM retiros  LIMIT {}, {}'.format(row1,row2))
          data = cur.fetchall()
    else:
      if 'datefilter_recibo' in session:
        if len(session['datefilter_recibo'])>0:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM retiros WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_recibo'],row1,row2))
          data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM retiros LIMIT {}, {}'.format(row1,row2))
          data = cur.fechall()
      else:
        cur= db_connection.cursor()
        cur.execute('SELECT * FROM retiros  LIMIT {}, {}'.format(row1,row2))
        data = cur.fetchall()
    datos="Id"+","+"Ola"+","+"Meli"+","+"Cantidad"+","+"Ubicacion"+","+"Responsable"+","+"Fecha"+","+"Fecha y Hora"+"\n"
    for res in data:
      datos+=str(res[0])
      datos+=","+str(res[1]).replace(","," ")
      datos+=","+str(res[2]).replace(","," ")
      datos+=","+str(res[3]).replace(","," ")
      datos+=","+str(res[4]).replace(","," ")
      datos+=","+str(res[5]).replace(","," ")
      datos+=","+str(res[6]).replace(","," ")
      datos+=","+str(res[7]).replace(","," ")
      datos+="\n"

    response = make_response(datos)
    response.headers["Content-Disposition"] = "attachment; filename="+"Reportre_Recibo-"+str(datetime.today())+".csv"; 
    return response

@app.route('/csvdonacion',methods=['POST','GET'])
def crear_csvdonacion():
    site=session['SiteName']
    row1 = 0
    row2 =5000
    if 'valor_donacion' in session:
      if len(session['valor_donacion'])>0:
        if 'datefilter_donacion' in session:
          if len(session['datefilter_donacion'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM donacion WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_donacion'],session['valor_donacion'],session['datefilter_donacion'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_donacion'],session['valor_donacion'],row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_donacion'],session['valor_donacion'],row1,row2))
          data = cur.fetchall()
      else:
        if 'datefilter_donacion' in session:
          if len(session['datefilter_donacion'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM donacion WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_donacion'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM donacion LIMIT {}, {}'.format(row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM donacion  LIMIT {}, {}'.format(row1,row2))
          data = cur.fetchall()
    else:
      if 'datefilter_donacion' in session:
        if len(session['datefilter_donacion'])>0:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM donacion WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_donacion'],row1,row2))
          data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM donacion LIMIT {}, {}'.format(row1,row2))
          data = cur.fetchall()
      else:
        cur= db_connection.cursor()
        cur.execute('SELECT * FROM donacion  LIMIT {}, {}'.format(row1,row2))
        data = cur.fetchall()
    datos="Id"+","+"Ola"+","+"SKU"+","+"Cantidad"+","+"Ubicacion"+","+"Responsable"+","+"Fecha"+","+"Fecha y Hora"+","+"\n"
    for res in data:
      datos+=str(res[0]).replace(","," ")
      datos+=","+str(res[1]).replace(","," ")
      datos+=","+str(res[2]).replace(","," ")
      datos+=","+str(res[3]).replace(","," ")
      datos+=","+str(res[4]).replace(","," ")
      datos+=","+str(res[5]).replace(","," ")
      datos+=","+str(res[6]).replace(","," ")
      datos+=","+str(res[7]).replace(","," ")
      datos+="\n"

    response = make_response(datos)
    response.headers["Content-Disposition"] = "attachment; filename="+"Donacion-"+str(datetime.today())+".csv"; 
    return response

@app.route('/csvingram',methods=['POST','GET'])
def crear_ccsvingram():
    site=session['SiteName']
    row1 = 0
    row2 =5000
    if 'valor_ingram' in session:
      if len(session['valor_ingram'])>0:
        if 'datefilter_ingram' in session:
          if len(session['datefilter'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\' AND fecha BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_ingram'],session['valor_ingram'],session['datefilter_ingram'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_ingram'],session['valor_ingram'],row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM retirio_ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_ingram'],session['valor_ingram'],row1,row2))
          data = cur.fetchall()
      else:
        if 'datefilter_ingram' in session:
          if len(session['datefilter_ingram'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM retirio_ingram WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_ingram'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM retirio_ingram LIMIT {}, {}'.format(row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM retirio_ingram  LIMIT {}, {}'.format(row1,row2))
          data = cur.fetchall()
    else:
      if 'datefilter_ingram' in session:
        if len(session['datefilter_ingram'])>0:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM retirio_ingram WHERE fecha BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_ingram'],row1,row2))
          data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM retirio_ingram LIMIT {}, {}'.format(row1,row2))
          data = cur.fetchall()
      else:
        cur= db_connection.cursor()
        cur.execute('SELECT * FROM retirio_ingram  LIMIT {}, {}'.format(row1,row2))
        data = cur.fetchall()
    datos="Id"+","+"Ola"+","+"SKU"+","+"Cantidad"+","+"Ubicacion"+","+"Responsable"+","+"Fecha"+","+"Fecha y Hora"+","+"\n"
    for res in data:
      datos+=str(res[0]).replace(","," ")
      datos+=","+str(res[1]).replace(","," ")
      datos+=","+str(res[2]).replace(","," ")
      datos+=","+str(res[3]).replace(","," ")
      datos+=","+str(res[4]).replace(","," ")
      datos+=","+str(res[5]).replace(","," ")
      datos+=","+str(res[6]).replace(","," ")
      datos+=","+str(res[7]).replace(","," ")
      datos+="\n"

    response = make_response(datos)
    response.headers["Content-Disposition"] = "attachment; filename="+"Ingram-"+str(datetime.today())+".csv"; 
    return response

#Solicitudes
@app.route('/Solicitudes_Retiros/<rowi>',methods=['POST','GET'])
def solicitudes_retiros(rowi):
  # try:
      if request.method == 'POST':
        if request.method == 'GET':
          session['rowi_solicitudrecibo']=rowi
          row1 = int(session['rowi_solicitudrecibo'])
          row2 = 50
        else:
            row1 = int(session['rowi_solicitudrecibo'])
            row2 =50
        if 'valor' in request.form:
          if len(request.form['valor'])>0:
            session['filtro_solicitudrecibo']=request.form['filtro']
            session['valor_solicitudrecibo']=request.form['valor']
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                daterangef=request.form['datefilter']
                daterange=daterangef.replace("-", "' AND '")
                session['datefilter_solicitudrecibo']=daterange
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\' AND fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],session['datefilter_solicitudrecibo'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter_solicitudrecibo')
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
          else:
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                if 'valor_solicitudrecibo' in session:
                  if len(session['valor_solicitudrecibo'])>0:
                    daterangef=request.form['datefilter']
                    daterange=daterangef.replace("-", "' AND '")
                    session['datefilter_solicitudrecibo']=daterange
                    cur= db_connection.cursor()
                    cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\' AND fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],session['datefilter_solicitudrecibo'],row1,row2))
                    data = cur.fetchall()
                    return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
                  else:
                    session.pop('filtro_solicitudrecibo')
                    session.pop('valor_solicitudrecibo')
                    cur= db_connection.cursor()
                    cur.execute('SELECT * FROM solicitud_retiros WHERE fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudrecibo'],row1,row2))
                    data = cur.fetchall()
                    return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
                else:
                  daterangef=request.form['datefilter']
                  daterange=daterangef.replace("-", "' AND '")
                  session['datefilter_solicitudrecibo']=daterange
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_retiros WHERE fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudrecibo'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
              else:
                if 'valor_solicitudrecibo' in session:
                  session.pop('filtro_solicitudrecibo')
                  session.pop('valor_solicitudrecibo')
                if 'datefilter_solicitudrecibo' in session:
                  session.pop('datefilter_solicitudrecibo')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros  LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_retiros.html',Datos = session,Infos =data)
            else:
              if 'valor_solicitudrecibo' in session:
                session.pop('filtro_solicitudrecibo')
                session.pop('valor_solicitudrecibo')
              if 'datefilter_solicitudrecibo' in session:
                session.pop('datefilter_solicitudrecibo')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros  LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)

        else:
          if 'valor_solicitudrecibo' in session:
            if len(session['valor_solicitudrecibo'])>0:
              if 'datefilter_solicitudrecibo' in session:
                if len(session['datefilter_solicitudrecibo'])>0:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\' AND fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],session['datefilter_solicitudrecibo'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
                else:
                  session.pop('datefilter_solicitudrecibo')
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data) 
            else:
              session.pop('filtro_solicitudrecibo')
              session.pop('valor_solicitudrecibo')
              if 'datefilter_solicitudrecibo' in session:
                if len(session['datefilter_solicitudrecibo'])>0:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_retiros WHERE fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudrecibo'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_retiros LIMIT {}, {}'.format(row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros  LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
          else:
            if 'datefilter_solicitudrecibo' in session:
              if len(session['datefilter_solicitudrecibo'])>0:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros WHERE fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudrecibo'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_solicitudrecibo')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
            else:
              if 'datefilter' in request.form:
                if len(request.form['datefilter'])>0:
                  daterangef=request.form['datefilter']
                  daterange=daterangef.replace("-", "' AND '")
                  session['datefilter_solicitudrecibo']=daterange
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_retiros WHERE  fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudrecibo'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_retiros LIMIT {}, {}'.format(row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data) 
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data) 
      else: 
        if request.method == 'GET':
          session['rowi_solicitudrecibo']=rowi
          row1 = int(session['rowi_solicitudrecibo'])
          row2 = 50
        else:
          row1 = int(session['rowi_solicitudrecibo'])
          row2 =50
        if 'valor_solicitudrecibo' in session:
          if len(session['valor_solicitudrecibo'])>0:
            if 'datefilter_solicitudrecibo' in session:
              if len(session['datefilter_solicitudrecibo'])>0:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\' AND fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],session['datefilter_solicitudrecibo'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_solicitudrecibo')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data) 
          else:
            session.pop('filtro_solicitudrecibo')
            session.pop('valor_solicitudrecibo')
            if 'datefilter_solicitudrecibo' in session:
              if len(session['datefilter_solicitudrecibo'])>0:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros WHERE fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudrecibo'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_solicitudrecibo')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_retiros LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM solicitud_retiros  LIMIT {}, {}'.format(row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
        else:
          if 'datefilter_solicitudrecibo' in session:
            if len(session['datefilter_solicitudrecibo'])>0:
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM solicitud_retiros WHERE fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudrecibo'],row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter_solicitudrecibo')
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM solicitud_retiros LIMIT {}, {}'.format(row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM solicitud_retiros  LIMIT {}, {}'.format(row1,row2))
            data = cur.fetchall()
            return render_template('reportes/t_solicitudretiros.html',Datos = session,Infos =data)         
  # except:
  #   flash("Inicia Secion")
  #   return render_template('index.html')

@app.route('/Solicitudes_donacion/<rowi>',methods=['POST','GET'])
def solicitud_donacion(rowi):
  try:
      if request.method == 'POST':
        if request.method == 'GET':
          session['rowi_solicituddonacion']=rowi
          row1 = int(session['rowi_solicituddonacion'])
          row2 = 50
        else:
            row1 = int(session['rowi_solicituddonacion'])
            row2 =50
        if 'valor' in request.form:
          if len(request.form['valor'])>0:
            session['filtro_solicituddonacion']=request.form['filtro']
            session['valor_solicituddonacion']=request.form['valor']
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                daterangef=request.form['datefilter']
                daterange=daterangef.replace("-", "' AND '")
                session['datefilter_solicituddonacion']=daterange
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\' AND fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],session['datefilter_solicituddonacion'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter_solicituddonacion')
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
          else:
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                if 'valor_solicituddonacion' in session:
                  if len(session['valor_solicituddonacion'])>0:
                    daterangef=request.form['datefilter']
                    daterange=daterangef.replace("-", "' AND '")
                    session['datefilter_solicituddonacion']=daterange
                    cur= db_connection.cursor()
                    cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\' AND fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],session['datefilter_solicituddonacion'],row1,row2))
                    data = cur.fetchall()
                    return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
                  else:
                    session.pop('filtro_solicituddonacion')
                    session.pop('valor_solicituddonacion')
                    cur= db_connection.cursor()
                    cur.execute('SELECT * FROM solicitud_donacion WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicituddonacion'],row1,row2))
                    data = cur.fetchall()
                    return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_donacion WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicituddonacion'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
              else:
                if 'valor_solicituddonacion' in session:
                  session.pop('filtro_solicituddonacion')
                  session.pop('valor_solicituddonacion')
                  if 'datefilter_solicituddonacion' in session:
                    session.pop('datefilter_solicituddonacion')
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_donacion  LIMIT {}, {}'.format(row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_donacion  LIMIT {}, {}'.format(row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
            else:
              if 'valor_solicituddonacion' in session:
                if 'datefilter_solicituddonacion' in session:
                    session.pop('datefilter_solicituddonacion')
                session.pop('filtro_solicituddonacion')
                session.pop('valor_solicituddonacion')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion  LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion  LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)

        else:
          if 'valor_solicituddonacion' in session:
            if len(session['valor_solicituddonacion'])>0:
              if 'datefilter_solicituddonacion' in session:
                if len(session['datefilter_solicituddonacion'])>0:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\' AND fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],session['datefilter_solicituddonacion'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
                else:
                  session.pop('datefilter_solicituddonacion')
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data) 
            else:
              session.pop('filtro_solicituddonacion')
              session.pop('valor_solicituddonacion')
              if 'datefilter_solicituddonacion' in session:
                if len(session['datefilter_solicituddonacion'])>0:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_donacion WHERE Fecha BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicituddonacion'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_donacion LIMIT {}, {}'.format(row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion  LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
          else:
            if 'datefilter_solicituddonacion' in session:
              if len(session['datefilter_solicituddonacion'])>0:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicituddonacion'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_solicituddonacion')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
            else:
              if 'datefilter' in request.form:
                if len(request.form['datefilter'])>0:
                  daterangef=request.form['datefilter']
                  daterange=daterangef.replace("-", "' AND '")
                  session['datefilter_solicituddonacion']=daterange
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_donacion WHERE  fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicituddonacion'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM solicitud_donacion LIMIT {}, {}'.format(row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data) 
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data) 
      else: 
        if request.method == 'GET':
          session['rowi_solicituddonacion']=rowi
          row1 = int(session['rowi_solicituddonacion'])
          row2 = 50
        else:
          row1 = int(session['rowi_solicituddonacion'])
          row2 =50
        if 'valor_solicituddonacion' in session:
          if len(session['valor_solicituddonacion'])>0:
            if 'datefilter_solicituddonacion' in session:
              if len(session['datefilter_solicituddonacion'])>0:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\' AND fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],session['datefilter_solicituddonacion'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_solicituddonacion')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data) 
          else:
            session.pop('filtro_solicituddonacion')
            session.pop('valor_solicituddonacion')
            if 'datefilter_solicituddonacion' in session:
              if len(session['datefilter_solicituddonacion'])>0:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicituddonacion'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_solicituddonacion')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM solicitud_donacion LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM solicitud_donacion  LIMIT {}, {}'.format(row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
        else:
          if 'datefilter_solicituddonacion' in session:
            if len(session['datefilter_recibo'])>0:
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM solicitud_donacion WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicituddonacion'],row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter_solicituddonacion')
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM solicitud_donacion LIMIT {}, {}'.format(row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM solicitud_donacion  LIMIT {}, {}'.format(row1,row2))
            data = cur.fetchall()
            return render_template('reportes/t_solicituddonacion.html',Datos = session,Infos =data)         
  except:
    flash("Inicia Secion")
    return render_template('index.html')

@app.route('/Solicitudes_Ingram/<rowi>',methods=['POST','GET'])
def solicitud_ingram(rowi):
  # try:
      if request.method == 'POST':
        if request.method == 'GET':
          session['rowi_solicitudingram']=rowi
          row1 = int(session['rowi_solicitudingram'])
          row2 = 50
        else:
            row1 = int(session['rowi_solicitudingram'])
            row2 =50
        if 'valor' in request.form:
          if len(request.form['valor'])>0:
            session['filtro_solicitudingram']=request.form['filtro']
            session['valor_solicitudingram']=request.form['valor']
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                daterangef=request.form['datefilter']
                daterange=daterangef.replace("-", "' AND '")
                session['datefilter_solicitudingram']=daterange
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\' AND fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],session['datefilter_solicitudingram'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter_solicitudingram')
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
          else:
            if 'datefilter' in request.form:
              if len(request.form['datefilter'])>0:
                if 'valor_solicitudingram' in session:
                  if len(session['valor_solicitudingram'])>0:
                    daterangef=request.form['datefilter']
                    daterange=daterangef.replace("-", "' AND '")
                    session['datefilter_solicitudingram']=daterange
                    cur= db_connection.cursor()
                    cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\' AND fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],session['datefilter_solicitudingram'],row1,row2))
                    data = cur.fetchall()
                    return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
                  else:
                    session.pop('filtro_solicitudingram')
                    session.pop('valor_solicitudingram')
                    cur= db_connection.cursor()
                    cur.execute('SELECT * FROM ingram WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudingram'],row1,row2))
                    data = cur.fetchall()
                    return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM ingram WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudingram'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
              else:
                if 'valor_solicitudingram' in session:
                  session.pop('filtro_solicitudingram')
                  session.pop('valor_solicitudingram')
                  if 'datefilter_solicitudingram' in session:
                    session.pop('datefilter_solicitudingram')
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM ingram  LIMIT {}, {}'.format(row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM ingram  LIMIT {}, {}'.format(row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
            else:
              if 'valor_solicitudingram' in session:
                if 'datefilter_solicitudingram' in session:
                    session.pop('datefilter_solicitudingram')
                session.pop('filtro_solicitudingram')
                session.pop('valor_solicitudingram')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram  LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram  LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)

        else:
          if 'valor_solicitudingram' in session:
            if len(session['valor_solicitudingram'])>0:
              if 'datefilter_solicitudingram' in session:
                if len(session['datefilter_solicitudingram'])>0:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\' AND fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],session['datefilter_solicitudingram'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
                else:
                  session.pop('datefilter_solicitudingram')
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data) 
            else:
              session.pop('filtro_solicitudingram')
              session.pop('valor_solicitudingram')
              if 'datefilter_solicitudingram' in session:
                if len(session['datefilter_solicitudingram'])>0:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM ingram WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudingram'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM ingram LIMIT {}, {}'.format(row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram  LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
          else:
            if 'datefilter_solicitudingram' in session:
              if len(session['datefilter_solicitudingram'])>0:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudingram'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_solicitudingram')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
            else:
              if 'datefilter' in request.form:
                if len(request.form['datefilter'])>0:
                  daterangef=request.form['datefilter']
                  daterange=daterangef.replace("-", "' AND '")
                  session['datefilter_solicitudingram']=daterange
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM ingram WHERE  fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudingram'],row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
                else:
                  cur= db_connection.cursor()
                  cur.execute('SELECT * FROM ingram LIMIT {}, {}'.format(row1,row2))
                  data = cur.fetchall()
                  return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data) 
              else:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data) 
      else: 
        if request.method == 'GET':
          session['rowi_solicitudingram']=rowi
          row1 = int(session['rowi_solicitudingram'])
          row2 = 50
        else:
          row1 = int(session['rowi_solicitudingram'])
          row2 =50
        if 'valor_solicitudingram' in session:
          if len(session['valor_solicitudingram'])>0:
            if 'datefilter_solicitudingram' in session:
              if len(session['datefilter_solicitudingram'])>0:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\' AND fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],session['datefilter_solicitudingram'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_solicitudingram')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data) 
          else:
            session.pop('filtro_solicitudingram')
            session.pop('valor_solicitudingram')
            if 'datefilter_solicitudingram' in session:
              if len(session['datefilter_solicitudingram'])>0:
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudingram'],row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
              else:
                session.pop('datefilter_solicitudingram')
                cur= db_connection.cursor()
                cur.execute('SELECT * FROM ingram LIMIT {}, {}'.format(row1,row2))
                data = cur.fetchall()
                return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
            else:
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM ingram  LIMIT {}, {}'.format(row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
        else:
          if 'datefilter_solicitudingram' in session:
            if len(session['datefilter_solicitudingram'])>0:
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM ingram WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudingram'],row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
            else:
              session.pop('datefilter_solicitudingram')
              cur= db_connection.cursor()
              cur.execute('SELECT * FROM ingram LIMIT {}, {}'.format(row1,row2))
              data = cur.fetchall()
              return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM ingram  LIMIT {}, {}'.format(row1,row2))
            data = cur.fetchall()
            return render_template('reportes/t_solicitudingram.html',Datos = session,Infos =data)         
  # except:
  #   return render_template('index.html')

@app.route('/csvsolicitudretiros',methods=['POST','GET'])
def crear_csvsolicitudretiros():
    site=session['SiteName']
    row1 = 0
    row2 =5000
    if 'valor_solicitudrecibo' in session:
      if len(session['valor_solicitudrecibo'])>0:
        if 'datefilter_solicitudrecibo' in session:
          if len(session['datefilter_solicitudrecibo'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\' AND fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],session['datefilter_solicitudrecibo'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM solicitud_retiros WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudrecibo'],session['valor_solicitudrecibo'],row1,row2))
          data = cur.fetchall()
      else:
        if 'datefilter_solicitudrecibo' in session:
          if len(session['datefilter_solicitudrecibo'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM solicitud_retiros WHERE fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudrecibo'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM solicitud_retiros LIMIT {}, {}'.format(row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM solicitud_retiros  LIMIT {}, {}'.format(row1,row2))
          data = cur.fetchall()
    else:
      if 'datefilter_solicitudrecibo' in session:
        if len(session['datefilter_solicitudrecibo'])>0:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM solicitud_retiros WHERE fecha_de_entrega BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudrecibo'],row1,row2))
          data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM solicitud_retiros LIMIT {}, {}'.format(row1,row2))
      else:
        cur= db_connection.cursor()
        cur.execute('SELECT * FROM solicitud_retiros  LIMIT {}, {}'.format(row1,row2))
        data = cur.fetchall()
    datos="Id"+","+"Ola"+","+"Meli"+","+"Fecha de Entrega"+","+"Cantidad Solicitada"+","+"QTY_DISP_WMS"+","+"Descripción"+","+"cantidad_susrtida"+","+"Estatus"+","+"Ubicacion"+","+"Fecha de creacion"+"\n"
    for res in data:
      datos+=str(res[0])
      datos+=","+str(res[1]).replace(","," ")
      datos+=","+str(res[2]).replace(","," ")
      datos+=","+str(res[3]).replace(","," ")
      datos+=","+str(res[4]).replace(","," ")
      datos+=","+str(res[5]).replace(","," ")
      datos+=","+str(res[6]).replace(","," ")
      datos+=","+str(res[7]).replace(","," ")
      datos+=","+str(res[8]).replace(","," ")
      datos+=","+str(res[9]).replace(","," ")
      datos+=","+str(res[10]).replace(","," ")
      datos+="\n"

    response = make_response(datos)
    response.headers["Content-Disposition"] = "attachment; filename="+"solicitud_retiros-"+str(datetime.today())+".csv"; 
    return response

@app.route('/csvsolicituddonacion',methods=['POST','GET'])
def crear_csvsolicituddonacion():
    site=session['SiteName']
    row1 = 0
    row2 =5000
    if 'valor_solicituddonacion' in session:
      if len(session['valor_solicituddonacion'])>0:
        if 'datefilter_solicituddonacion' in session:
          if len(session['datefilter_solicituddonacion'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\' AND fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],session['datefilter_solicituddonacion'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM solicitud_donacion WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicituddonacion'],session['valor_solicituddonacion'],row1,row2))
          data = cur.fetchall()
      else:
        if 'datefilter_solicituddonacion' in session:
          if len(session['datefilter_solicituddonacion'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM solicitud_donacion WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicituddonacion'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM solicitud_donacion LIMIT {}, {}'.format(row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM solicitud_donacion  LIMIT {}, {}'.format(row1,row2))
          data = cur.fetchall()
    else:
      if 'datefilter_solicituddonacion' in session:
        if len(session['datefilter'])>0:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM solicitud_donacion WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicituddonacion'],row1,row2))
          data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM solicitud_donacion LIMIT {}, {}'.format(row1,row2))
      else:
        cur= db_connection.cursor()
        cur.execute('SELECT * FROM solicitud_donacion  LIMIT {}, {}'.format(row1,row2))
        data = cur.fetchall()
    datos="Id"+","+"Ola"+","+"SKU"+","+"Cantidad Solicitada"+","+"Costo Unitario"+","+"Suma de GMV"+","+"Descripcion"+","+"Cantidad Surtida "+","+"Status"+","+"Ubicacion"+","+"Fecha "+"\n"
    for res in data:
      datos+=str(res[0]).replace(","," ")
      datos+=","+str(res[1]).replace(","," ")
      datos+=","+str(res[2]).replace(","," ")
      datos+=","+str(res[3]).replace(","," ")
      datos+=","+str(res[4]).replace(","," ")
      datos+=","+str(res[5]).replace(","," ")
      datos+=","+str(res[6]).replace(","," ")
      datos+=","+str(res[7]).replace(","," ")
      datos+=","+str(res[8]).replace(","," ")
      datos+=","+str(res[9]).replace(","," ")
      datos+=","+str(res[10]).replace(","," ")
      datos+="\n"

    response = make_response(datos)
    response.headers["Content-Disposition"] = "attachment;filename= Solicitud_Donacion-"+str(datetime.today())+".csv"; 
    return response

@app.route('/csvsolicitudingram',methods=['POST','GET'])
def crear_ccsvsolicitudingram():
    site=session['SiteName']
    row1 = 0
    row2 =5000
    if 'valor_solicitudingram' in session:
      if len(session['valor_solicitudingram'])>0:
        if 'datefilter_solicitudingram' in session:
          if len(session['datefilter_solicitudingram'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\' AND fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],session['datefilter_solicitudingram'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM ingram WHERE {} LIKE \'%{}%\'  LIMIT {}, {}'.format(session['filtro_solicitudingram'],session['valor_solicitudingram'],row1,row2))
          data = cur.fetchall()
      else:
        if 'datefilter_solicitudingram' in session:
          if len(session['datefilter_solicitudingram'])>0:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM ingram WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudingram'],row1,row2))
            data = cur.fetchall()
          else:
            cur= db_connection.cursor()
            cur.execute('SELECT * FROM ingram LIMIT {}, {}'.format(row1,row2))
            data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM ingram  LIMIT {}, {}'.format(row1,row2))
          data = cur.fetchall()
    else:
      if 'datefilter_solicitudingram' in session:
        if len(session['datefilter'])>0:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM ingram WHERE fecha_de_solicitud BETWEEN \'{}\'  LIMIT {}, {}'.format(session['datefilter_solicitudingram'],row1,row2))
          data = cur.fetchall()
        else:
          cur= db_connection.cursor()
          cur.execute('SELECT * FROM ingram LIMIT {}, {}'.format(row1,row2))
      else:
        cur= db_connection.cursor()
        cur.execute('SELECT * FROM ingram  LIMIT {}, {}'.format(row1,row2))
        data = cur.fetchall()
    datos="Id"+","+"Ola"+","+"SKU"+","+"Cantidad Solicitada"+","+"Cantidad Disponible"+","+"Piezas Surtidas"+","+"Descripcion"+","+"Estatus"+","+"Ubicacion"+","+"Fecha"+"\n"
    for res in data:
      datos+=str(res[0]).replace(","," ")
      datos+=","+str(res[1]).replace(","," ")
      datos+=","+str(res[2]).replace(","," ")
      datos+=","+str(res[3]).replace(","," ")
      datos+=","+str(res[4]).replace(","," ")
      datos+=","+str(res[5]).replace(","," ")
      datos+=","+str(res[6]).replace(","," ")
      datos+=","+str(res[7]).replace(","," ")
      datos+=","+str(res[8]).replace(","," ")
      datos+=","+str(res[9]).replace(","," ")
      datos+="\n"

    response = make_response(datos)
    response.headers["Content-Disposition"] = "attachment; filename="+"Solicitud_Ingram-"+str(datetime.today())+".csv"; 
    return response


#PDF Ubicacion
@app.route('/pdf/<ubicacion>',methods=['POST','GET'])
def pdf_template(ubicacion):
  
        qr =  ubicacion
        img =qrcode.make(qr)
        file =open('static/img/qr.png','wb')
        img.save(file)
        lugar = 'De: '+session['FcName']+' | '+session['SiteName']
        facility = session['FcName']
        site = session['SiteName']
        today= datetime.today()
 
        pdf = FPDF(orientation = 'P',unit = 'mm',format= (128,60))
        pdf.add_page()
         
        page_width = pdf.w - 2 * pdf.l_margin
         
        pdf.ln(5)
        pdf.image('static/img/MercadoLibre_logo.png', x= 5, y = 5, w=25, h = 10)
        pdf.set_font('Times','B',30)
        pdf.set_text_color(0,47,109)  
        pdf.text(x = 35, y = 15 ,txt =  "Withdrawal System" )
        pdf.ln(80)
        
        pdf.image('static/img/qr.png', x= 10, y = 20, w=40, h = 40)

        pdf.set_font('Times','B',12) 
        
        pdf.set_text_color(0,0,0) 
        pdf.text( x= 70, y = 27, txt = str(today))
        pdf.text( x= 70, y = 37, txt = "Ubicacion:")
        pdf.text( x= 70, y = 47, txt = qr)

        return Response(pdf.output(dest='S').encode('latin-1'), mimetype='application/pdf', headers={'Content-Disposition':'Atachment;filename=Ubicacion-'+qr+'.pdf'})

@app.route('/files',methods=['POST','GET'])
def Files_():
  if 'FullName' in session:
    return render_template('form/files.html',Datos=session)
  else:
    return redirect('/')

@app.route('/CargarDatos',methods=['POST','GET'])
def uploadFiles():
  # try:
    if 'FullName' in session:
      # get the uploaded file
      file =request.files['datos']
      base = request.form['base']
      
      if base == 'Donacion':
        file.save(os.path.join(UPLOAD_FOLDER, "donacioncsv.csv"))
        # data = csv.reader(open('static/file/donacioncsv.csv))
        with open('static/file/donacioncsv.csv',"r", encoding="utf8") as csv_file:
          data=csv.reader(csv_file, delimiter=',')
          i=0
          for row in data:
            if i >0:
              now= datetime.now()
              cur= db_connection.cursor()
              # Create a new record
              sql = "INSERT INTO solicitud_donacion (numero_ola,  SKU, Cantidad_Solicitada, costo_unitario, suma_de_gmv_total, descripcion, cantidad_susrtida,  fecha_de_solicitud, facility, Site) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
              cur.execute(sql,(row[0], row[1], row[2], row[3], row[4], row[5],0,now,session['FcName'],session['SiteName'],))
              # connection is not autocommit by default. So you must commit to save
              # your changes.
              db_connection.commit()
            i+=1 
        
        flash(str(i)+' Registros Exitoso')
        return redirect('/files')
      elif base == 'Retiros':
        file.save(os.path.join(UPLOAD_FOLDER, "retiroscsv.csv"))
        # data = csv.reader(open('static/file/retiroscsv.csv'))
        with open('static/file/retiroscsv.csv',"r", encoding="utf8") as csv_file:
          data=csv.reader(csv_file, delimiter=',')
          i=0
          for row in data:
            if i>0:
              now= datetime.now()
              cur= db_connection.cursor()
              # Create a new record
              sql = "INSERT INTO solicitud_retiros (nuemro_de_ola,  meli, fecha_de_entrega, cantidad_solizitada, QTY_DISP_WMS, Descripción, Fecha_de_creacion,  facility, Site) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
              cur.execute(sql,(row[0], row[1], row[2], row[3], row[4], row[5],now,session['FcName'],session['SiteName'],))
              # connection is not autocommit by default. So you must commit to save
              # your changes.
              db_connection.commit()
            i+=1
        
        flash(str(i)+' Registros Exitoso')
        return redirect('/files')
      elif base == 'Ingram':
        file.save(os.path.join(UPLOAD_FOLDER, "ingramcsv.csv"))
        # data = csv.reader(open('static/file/ingramcsv.csv'))
        with open('static/file/ingramcsv.csv',"r", encoding="utf8") as csv_file:
          data=csv.reader(csv_file, delimiter=',')
          i=0
          for row in data:
            if i>0:
              now= datetime.now()
              cur= db_connection.cursor()
              # Create a new record
              sql = "INSERT INTO ingram (numero_ola,  SKU, Cantidad_Solicitada, cantidad_disponible, descripcion, fecha_de_solicitud, facility, Site) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
              cur.execute(sql,(row[0], row[1], row[2], row[3], row[4],now,session['FcName'],session['SiteName'],))
              # connection is not autocommit by default. So you must commit to save
              # your changes.
              db_connection.commit()
            i+=1
        
        flash(str(i)+' Registros Exitoso')
        return redirect('/files')
      elif base == 'Inventario Seller':
        file.save(os.path.join(UPLOAD_FOLDER, "inventariosellercsv.csv"))
        # data = csv.reader(open('static/file/inventariosellercsv.csv'))
        with open('static/file/inventariosellercsv.csv',"r", encoding="utf8") as csv_file:
          data=csv.reader(csv_file, delimiter=',')
          i=0
          for row in data:
            if i>0:
              now= datetime.now()
              cur= db_connection.cursor()
              # Create a new record
              sql = "INSERT INTO inventario_seller (INVENTORY_ID,  ADDRESS_ID_TO, Seller, Holding, Cantidad, fecha_de_actualizacion, facility, Site) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
              cur.execute(sql,(row[1], row[2], row[3], row[4], row[5],now,session['FcName'],session['SiteName'],))
              # connection is not autocommit by default. So you must commit to save
              # your changes.
              db_connection.commit()
            i+=1
        
        flash(str(i)+' Registros Exitoso')
        return redirect('/files')
    else:
      return redirect('/')
  # except:
  #   flash('Ocurrió un error, Por favor Revisa bien los datos y vuelve a intentarlo.')
  #   return redirect('/files')

@app.route('/dashboard',methods=['POST','GET'])
def dash():
  # try:
    if request.method == 'POST':
      daterangef=request.form['datefilter']
      daterange=daterangef.replace("-", "' AND '")
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(cantidad_solizitada), COUNT(id_tarea_retiros) FROM solicitud_retiros WHERE status = \'Pendiente\' AND fecha_de_entrega BETWEEN \'{}\' AND  Site =  \'{}\' LIMIT 1'.format(daterange, session['SiteName']))
      retiropendientes = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(cantidad_solizitada), COUNT(id_tarea_retiros) FROM solicitud_retiros WHERE status = \'En Proceso\' AND fecha_de_entrega BETWEEN \'{}\' AND  Site =  \'{}\'  LIMIT 1'.format(daterange, session['SiteName']))
      retiroenproceso = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(cantidad_solizitada), COUNT(id_tarea_retiros) FROM solicitud_retiros WHERE status = \'Cerrado\' AND fecha_de_entrega BETWEEN \'{}\' AND  Site =  \'{}\'  LIMIT 1'.format(daterange, session['SiteName']))
      retirocerrado = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_donacion) FROM solicitud_donacion WHERE status = \'Pendiente\' AND fecha_de_solicitud BETWEEN \'{}\' AND  Site =  \'{}\' LIMIT 1'.format(daterange, session['SiteName']))
      donacionpendientes = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_donacion) FROM solicitud_donacion WHERE status = \'En Proceso\' AND fecha_de_solicitud BETWEEN \'{}\' AND  Site =  \'{}\'  LIMIT 1'.format(daterange, session['SiteName']))
      donacionenproceso = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_donacion) FROM solicitud_donacion WHERE status = \'Cerrado\' AND fecha_de_solicitud BETWEEN \'{}\' AND  Site =  \'{}\'  LIMIT 1'.format(daterange, session['SiteName']))
      donacionocerrado = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_solicitud) FROM ingram WHERE estatus = \'Pendiente\' AND fecha_de_solicitud BETWEEN \'{}\' AND  Site =  \'{}\' LIMIT 1'.format(daterange, session['SiteName']))
      ingrampendientes = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_solicitud) FROM ingram WHERE estatus = \'En Proceso\' AND fecha_de_solicitud BETWEEN \'{}\' AND  Site =  \'{}\'  LIMIT 1'.format(daterange, session['SiteName']))
      ingramenproceso = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_solicitud) FROM ingram WHERE estatus = \'Cerrado\' AND fecha_de_solicitud BETWEEN \'{}\' AND  Site =  \'{}\'  LIMIT 1'.format(daterange, session['SiteName']))
      ingramcerrado = cur.fetchone()
      return render_template('dashboard.html',Datos=session,retiropendientes=retiropendientes,retiroenproceso=retiroenproceso,retirocerrado=retirocerrado,donacionpendientes=donacionpendientes,donacionenproceso=donacionenproceso,donacionocerrado=donacionocerrado,ingrampendientes=ingrampendientes,ingramenproceso=ingramenproceso,ingramcerrado=ingramcerrado)
    else:
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(cantidad_solizitada), COUNT(id_tarea_retiros) FROM solicitud_retiros WHERE status = \'Pendiente\' AND fecha_de_entrega BETWEEN (CURRENT_DATE-30) AND (CURRENT_DATE) AND  Site =  \'{}\'  LIMIT 1'.format(session['SiteName']))
      retiropendientes = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(cantidad_solizitada), COUNT(id_tarea_retiros) FROM solicitud_retiros WHERE status = \'En Proceso\' AND fecha_de_entrega BETWEEN (CURRENT_DATE-30) AND (CURRENT_DATE) AND  Site =  \'{}\' LIMIT 1'.format(session['SiteName']))
      retiroenproceso = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(cantidad_solizitada), COUNT(id_tarea_retiros) FROM solicitud_retiros WHERE status = \'Cerrado\' AND fecha_de_entrega BETWEEN (CURRENT_DATE-30) AND (CURRENT_DATE)  AND  Site =  \'{}\' LIMIT 1'.format(session['SiteName']))
      retirocerrado = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_donacion) FROM solicitud_donacion WHERE status = \'Pendiente\' AND fecha_de_solicitud BETWEEN (CURRENT_DATE-30) AND (CURRENT_DATE) AND  Site =  \'{}\' LIMIT 1'.format(session['SiteName']))
      donacionpendientes = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_donacion) FROM solicitud_donacion WHERE status = \'En Proceso\' AND fecha_de_solicitud BETWEEN (CURRENT_DATE-30) AND (CURRENT_DATE) AND  Site =  \'{}\'  LIMIT 1'.format(session['SiteName']))
      donacionenproceso = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_donacion) FROM solicitud_donacion WHERE status = \'Cerrado\' AND fecha_de_solicitud BETWEEN (CURRENT_DATE-30) AND (CURRENT_DATE) AND  Site =  \'{}\'  LIMIT 1'.format(session['SiteName']))
      donacionocerrado = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_solicitud) FROM ingram WHERE estatus = \'Pendiente\' AND fecha_de_solicitud BETWEEN (CURRENT_DATE-30) AND (CURRENT_DATE) AND  Site =  \'{}\' LIMIT 1'.format(session['SiteName']))
      ingrampendientes = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_solicitud) FROM ingram WHERE estatus = \'En Proceso\' AND fecha_de_solicitud BETWEEN (CURRENT_DATE-30) AND (CURRENT_DATE) AND  Site =  \'{}\'  LIMIT 1'.format(session['SiteName']))
      ingramenproceso = cur.fetchone()
      cur= db_connection.cursor()
      cur.execute('SELECT  SUM(Cantidad_Solicitada), COUNT(id_solicitud) FROM ingram WHERE estatus = \'Cerrado\' AND fecha_de_solicitud BETWEEN (CURRENT_DATE-30) AND (CURRENT_DATE) AND  Site =  \'{}\'  LIMIT 1'.format(session['SiteName']))
      ingramcerrado = cur.fetchone()
      return render_template('dashboard.html',Datos=session,retiropendientes=retiropendientes,retiroenproceso=retiroenproceso,retirocerrado=retirocerrado,donacionpendientes=donacionpendientes,donacionenproceso=donacionenproceso,donacionocerrado=donacionocerrado,ingrampendientes=ingrampendientes,ingramenproceso=ingramenproceso,ingramcerrado=ingramcerrado)
  # except:
  #   return redirect('/')



if __name__=='__main__':
    app.run(port = 5000, debug =True)