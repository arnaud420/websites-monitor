#! /usr/bin/python3.6
# -*- coding:utf-8 -*-

from flask import Flask, render_template, url_for, request, g, redirect, session, flash
import mysql.connector
from passlib.hash import argon2
import requests as R
import time
import _thread

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
		database = app.config['DATABASE_NAME']
	)
	return g.mysql_connection

def get_db_and_cursor() :
    if not hasattr(g, 'db') :
        g.db = connect_db()
        g.cursor = g.db.cursor()
    return g.db, g.cursor

########################################
#			  FUNCTIONS				   #
########################################
def sendToTelegram(message):
	chat_id = app.config['TELEGRAM_CHAT_ID']
	token = app.config['TELEGRAM_TOKEN']
	url = "https://api.telegram.org/bot{}/".format(token)
	url_with_msg = url + "sendMessage?chat_id={}&text={}".format(chat_id, message)
	try:
		req = R.get(url_with_msg)
		return req
	except Exception as e:
		return e

def sendToSlack(message):
	url = app.config['SLACK_WEBHOOK']
	content = {"text":"{}".format(message)}
	try:
		req = R.post(url, json=content)
		return req
	except Exception as e:
		return e

def sendAllMessages(message):
	sendToTelegram(message)
	sendToSlack(message)

# Return the http request code with it message from a url
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

# Infinite loop for check the http request return on each row in websites table every 120s
# Then insert the http request message with a date in historicals table 
# Send messages to telegram and slack if the return http code is not 200 for 3 times
def check_websites_statut():
	def loop():
		while True:
			with app.app_context():
				db, cursor = get_db_and_cursor()
				try:
					cursor.execute("SELECT id, url, counter, message_time FROM websites")
					websites = cursor.fetchall()

					for website in websites:

						website_id = website[0]
						url = website[1]
						website_counter = website[2]
						message_time = website[3]
						update_date = time.asctime( time.localtime(time.time()) )
						code, message = get_code_statut_from(url)

						# insert an historical of each website statut
						cursor.execute("INSERT INTO historicals (message, update_date, website_id) VALUES ('%s', '%s', (SELECT id from websites WHERE id = '%s'))" % (message, update_date, website_id))
						# update website with the current http code return
						cursor.execute("UPDATE websites SET url=('%s'), code=('%s'), message=('%s') WHERE id = ('%s')" % (url, code, message, website_id))
						db.commit()

						if code != 200:

							now = int(time.time())
							two_hours = 7200
							two_hours_from_last_message = message_time + two_hours
							website_counter+=1
							cursor.execute("UPDATE websites SET counter=('%s') WHERE id = ('%s')" % (website_counter, website_id))
							db.commit()

							if website_counter >= 3 and now >= two_hours_from_last_message:
								
								cursor.execute("UPDATE websites SET counter=('%s'), message_time=('%s') WHERE id = ('%s')" % (0, now, website_id))
								db.commit()
								message_content = "[HTTP: {}] on website url => {} ".format(code, url)
								sendAllMessages(message_content)

					db.close()
					time.sleep(120)

				except Exception as error:
					print("ERROR : ", error)
	loop()

########################################
#				ROUTES				   #
########################################

@app.route('/')
def home():
	db, cursor = get_db_and_cursor()
	cursor.execute("SELECT id, url, code, message FROM websites")
	websites = cursor.fetchall()
	db.close()
	return render_template('home.html', websites = websites)

@app.route('/login/', methods = ['GET', 'POST'])
def login():
	db, cursor = get_db_and_cursor()
	email = str(request.form.get('email'))
	password = str(request.form.get('password'))
	cursor.execute('SELECT name, email, password, is_admin FROM users WHERE email = %(email)s', {'email' : email})
	users = cursor.fetchall()
	db.close()
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
	db, cursor = get_db_and_cursor()
	cursor.execute("SELECT id, url, code, message FROM websites WHERE id = ('%s')" % (website))
	url = cursor.fetchone()
	if url == None:
		return redirect(url_for('error404'))
	else:
		cursor.execute("SELECT message, update_date FROM historicals WHERE website_id = ('%s') ORDER BY id DESC" % (website))
		historicals = cursor.fetchall()
	db.close()

	return render_template('/website/show.html', website = url, historicals = historicals)

@app.route('/admin/')
def admin() :
    if not session.get('user') or not session.get('user')[2] :
        return redirect(url_for('login'))
    db, cursor = get_db_and_cursor()
    cursor.execute("SELECT id, url, code, message FROM websites")
    urls = cursor.fetchall()
    db.close()
    return render_template('admin.html', user = session['user'], urls = urls)

@app.route('/admin/website/add/', methods=['GET', 'POST'])
def add_website():
	if not session.get('user') or not session.get('user')[2] :
		return redirect(url_for('login'))
	if request.method == 'POST':
		url = request.form.get('url')
		if url != '':
			try:
				code, message = get_code_statut_from(url)
				db, cursor = get_db_and_cursor()
				cursor.execute("INSERT INTO websites (url, code, message) VALUES ('%s', '%s', '%s')" % (url, code, message))
				
				if (cursor.rowcount == 1):
					db.commit()
					db.close()
					success_message = "Row added with success"
					return redirect(url_for('success', message = success_message))

			except Exception as error:
				print('Failed to insert data :', error)
		else:
			flash("Field can't be empty")
	return render_template('website/add.html')

@app.route('/success/<message>')
def success(message):
	return render_template('website/success.html', message = message)

@app.route('/admin/website/<int:website>/update/', methods=['GET', 'POST'])
def update_website(website):
	if not session.get('user') or not session.get('user')[2] :
		return redirect(url_for('login'))
	db, cursor = get_db_and_cursor()
	cursor.execute("SELECT url FROM websites WHERE id = ('%s')" % (website))
	url = cursor.fetchone()
	if url == None:
		db.close()
		return redirect(url_for('error404'))
	if request.method == 'POST':
		form_url = request.form.get('url')
		if form_url != '':
			try:
				code, message = get_code_statut_from(form_url)
				cursor.execute("UPDATE websites SET url=('%s'), code=('%s'), message=('%s') WHERE id = ('%s')" % (form_url, code, message, website))
				db.commit()
				db.close()
				success_message = "Row update with success"
				return redirect(url_for('success', message = success_message))
			except Exception as error:
				print('Failed to update data :', error)
		else:
			flash("Field can't be empty")
	return render_template('website/update.html', website = website, url = url)

@app.route('/admin/website/<int:website>/delete/', methods=['GET', 'POST'])
def delete_website(website):
	if not session.get('user') or not session.get('user')[2] :
		return redirect(url_for('login'))
	db, cursor = get_db_and_cursor()
	cursor.execute("SELECT url FROM websites WHERE id = ('%s')" % (website))
	url = cursor.fetchone()
	if url == None:
		db.close()
		return redirect(url_for('error404'))
	if request.method == 'POST':
		cursor.execute("DELETE FROM websites WHERE id = ('%s')" % (website))
		db.commit()
		db.close()
		success_message = "Row deleted with success"
		return redirect(url_for('success', message = success_message))
	return render_template('website/delete.html', website = website, url = url)

@app.route('/404/')
def error404():
	return render_template('errors/404.html')


# Start the check_websites_statut() function in a new thread
_thread.start_new_thread(check_websites_statut, ())

# Start web app
if __name__ == '__main__':
	# use_reloader=False is for avoid running the loop in thread twice
	app.run(debug=True, host='0.0.0.0', use_reloader=False)