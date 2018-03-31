#! /usr/bin/python3.6
# -*- coding:utf-8 -*-

from flask import Flask, render_template, url_for, request, g, redirect, session
import mysql.connector
from passlib.hash import argon2
import requests as R

app = Flask(__name__)
app.config.from_object('config')
app.config.from_object('secret_config')

########################################
#			  DB CONNECTION		       #
########################################

mysql_connection = mysql.connector.connect(
	host = app.config['DATABASE_HOST'],
	user = app.config['DATABASE_USER'],
	password = app.config['DATABASE_PASSWORD'],
	database = app.config['DATABASE_NAME']
)
mysql_cursor = mysql_connection.cursor()


########################################
#			  FUNCTIONS				   #
########################################

def get_code_statut_from(url):
	try:
		url_request_code = R.get(url).status_code
		statut_code_str = str(url_request_code)
		first_num_code = int(statut_code_str[0])

		if first_num_code == 2:
			message = "Accessible"
		elif first_num_code == 4:
			message = "Unreachable"
		elif first_num_code == 5:
			message = "Server Error"
		else:
			message = "Http error 1xx or 3xx"

		return url_request_code, message
	
	except:
		return 999, "Could not reach the server"

########################################
#				ROUTES				   #
########################################

@app.route('/')
def home():
	mysql_cursor.execute("SELECT id, url, code, message FROM websites")
	urls = mysql_cursor.fetchall()
	return render_template('home.html', urls = urls)

@app.route('/login/', methods = ['GET', 'POST'])
def login():
	email = str(request.form.get('email'))
	password = str(request.form.get('password'))
	mysql_cursor.execute('SELECT name, email, password, is_admin FROM users WHERE email = %(email)s', {'email' : email})
	users = mysql_cursor.fetchall()
	valid_user = False
	for user in users :
		if argon2.verify(password, user[2]) :
			valid_user = user
			if valid_user :
				session['user'] = valid_user
				return redirect(url_for('admin'))
	return render_template('login.html')

@app.route('/logout/')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/website/<int:website>/')
def show_website(website):
	mysql_cursor.execute("SELECT id, url, code, message FROM websites WHERE id = ('%s')" % (website))
	url = mysql_cursor.fetchone()
	if url == None:
		return redirect(url_for('error404'))
	else:
		mysql_cursor.execute("SELECT message, update_date FROM historicals WHERE website_id = ('%s')" % (website))
		historicals = mysql_cursor.fetchall()
	return render_template('/website/show.html', website = url, historicals = historicals)

@app.route('/admin/')
def admin() :
    if not session.get('user') or not session.get('user')[2] :
        return redirect(url_for('login'))
    mysql_cursor.execute("SELECT id, url, code, message FROM websites")
    urls = mysql_cursor.fetchall()
    return render_template('admin.html', user = session['user'], urls = urls)

@app.route('/admin/website/add/', methods=['GET', 'POST'])
def add_website():
	if request.method == 'POST':
		url = request.form.get('url')
		if url != '':
			try:
				code, message = get_code_statut_from(url)
				mysql_cursor.execute("INSERT INTO websites (url, code, message) VALUES ('%s', '%s', '%s')" % (url, code, message))
				mysql_connection.commit()
				success_message = "Row added with success"
				return redirect(url_for('success', message = success_message))
			except Exception as error:
				print('Failed to insert data :', error)
	return render_template('website/add.html')

@app.route('/success/<message>')
def success(message):
	return render_template('website/success.html', message = message)

@app.route('/admin/website/<int:website>/update/', methods=['GET', 'POST'])
def update_website(website):
	mysql_cursor.execute("SELECT url FROM websites WHERE id = ('%s')" % (website))
	url = mysql_cursor.fetchone()
	if url == None:
		return redirect(url_for('error404'))
	if request.method == 'POST':
		form_url = request.form.get('url')
		if url != '':
			try:
				code, message = get_code_statut_from(form_url)
				mysql_cursor.execute("UPDATE websites SET url=('%s'), code=('%s'), message=('%s') WHERE id = ('%s')" % (form_url, code, message, website))
				mysql_connection.commit()
				success_message = "Row update with success"
				return redirect(url_for('success', message = success_message))

			except Exception as error:
				print('Failed to update data :', error)
	return render_template('website/update.html', website = website, url = url)

@app.route('/admin/website/<int:website>/delete/', methods=['GET', 'POST'])
def delete_website(website):
	mysql_cursor.execute("SELECT url FROM websites WHERE id = ('%s')" % (website))
	url = mysql_cursor.fetchone()
	if url == None:
		return redirect(url_for('error404'))
	if request.method == 'POST':
		mysql_cursor.execute("DELETE FROM websites WHERE id = ('%s')" % (website))
		mysql_connection.commit()
		success_message = "Row deleted with success"
		return redirect(url_for('success', message = success_message))
	return render_template('website/delete.html', website = website, url = url)

@app.route('/404/')
def error404():
	return render_template('errors/404.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')