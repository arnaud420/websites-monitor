#! /usr/bin/python3.6
# -*- coding:utf-8 -*-

from flask import Flask, render_template, url_for, request, g, redirect, session
import mysql.connector
from passlib.hash import argon2

app = Flask(__name__)
app.config.from_object('config')
app.config.from_object('secret_config')

########################################
#			  DB CONNECTION		       #
########################################

def connect_db():
    g.mysql_connection = mysql.connector.connect(
    	host = app.config['DATABASE_HOST'],
    	user = app.config['DATABASE_USER'],
    	password = app.config['DATABASE_PASSWORD'],
    	database = app.config['DATABASE_NAME'])   
    g.mysql_cursor = g.mysql_connection.cursor()
    return g.mysql_cursor

def get_db():
    if not hasattr(g, 'db') :
        g.db = connect_db()
    return g.db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db') :
        g.db.close()

########################################
#				ROUTES				   #
########################################

@app.route('/')
def home():
	db = get_db()
	db.execute(
		"""
		SELECT url, statut_id, code, message
		FROM websites JOIN status
		ON status.id = websites.statut_id
		"""
	)
	urls = db.fetchall()
	return render_template('home.html', urls = urls)

@app.route('/login/', methods = ['GET', 'POST'])
def login():
	email = str(request.form.get('email'))
	password = str(request.form.get('password'))
	db = get_db()
	db.execute('SELECT name, email, password, is_admin FROM users WHERE email = %(email)s', {'email' : email})
	users = db.fetchall()
	valid_user = False
	for user in users :
		if argon2.verify(password, user[2]) :
			valid_user = user
			if valid_user :
				session['user'] = valid_user
				return redirect(url_for('admin'))
	return render_template('login.html')

@app.route('/admin/')
def admin () :
    if not session.get('user') or not session.get('user')[2] :
        return redirect(url_for('login'))

    return render_template('admin.html', user = session['user'])

@app.route('/logout/')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')