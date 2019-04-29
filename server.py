from flask import Flask, render_template, redirect, request, flash, session
from mysqlconnection import connectToMySQL
from flask_bcrypt import Bcrypt        
import re
import datetime
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
PASSWORD_REGEX = re.compile(r'^(?=[a-zA-Z0-9!@#$%^&*()_+=-]{8,}$)(?=.*?[a-z])(?=.*?[A-Z])(?=.*?[0-9]).*$')    
app = Flask(__name__)
app.secret_key = "keep it secret"
bcrypt = Bcrypt(app)
database = "wishes"

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/users/create", methods=["POST"])
def create_user():
    if len(request.form['first_name']) < 1:
        flash("Please enter a first name")
    if len(request.form['last_name']) < 1:
        flash("Please enter a last name")
    if len(request.form['email']) <1:
        flash("Please enter an email")
    if len(request.form['password']) <1:
        flash("Please enter a password")
    
    mysql = connectToMySQL(database)
    query = "SELECT * FROM users WHERE email = %(username)s;"
    data = { "username" : request.form["email"]}
    result = mysql.query_db(query, data)
    if len(result) > 0:
        flash("Duplicate email")
    
    if request.form['password_confirmation'] != request.form['password']:
        flash("Password are not the same")

    if not EMAIL_REGEX.match(request.form['email']):
        flash("Invalid email address!")

    if not PASSWORD_REGEX.match(request.form['password']):
        flash("Invalid Password! Please see password requirements.")
    
    
    if not '_flashes' in session:
        pw_hash = bcrypt.generate_password_hash(request.form['password'])
        mysql = connectToMySQL(database)
        data = {
            "fn": request.form["first_name"],
            "ln": request.form["last_name"],
            "em": request.form["email"],
            "pass": pw_hash
        }
        query = "INSERT INTO users (first_name, last_name, email, password) VALUES (%(fn)s, %(ln)s, %(em)s, %(pass)s)"
        new_user_id = mysql.query_db(query,data)
        session.clear()
        session['id'] = new_user_id
        session["first_name"] = request.form['first_name']
        session["last_name"] = request.form['last_name']
        return redirect("/dashboard")
    else:
        return redirect("/")

@app.route('/login', methods=['POST'])
def login():
    if len(request.form['username']) <1:
        flash("Please enter an username")
    if len(request.form['password']) <1:
        flash("Please enter a password")
    if '_flashes' in session:
            return redirect('/')
    mysql = connectToMySQL(database)
    query = "SELECT * FROM users WHERE email = %(username)s;"
    data = { "username" : request.form["username"]}
    result = mysql.query_db(query, data)
    print(result)
    if len(result) == 0:
        flash("Invalid username or password")
        return redirect("/")
    if len(result) > 0:
        if bcrypt.check_password_hash(result[0]['password'], request.form['password']):
            session['id'] = result[0]['id']
            session['first_name'] = result[0]['first_name']
            return redirect("/dashboard")
    flash("You could not be logged in")
    return redirect("/")

@app.route("/dashboard")
def dashboard():
    if "id" in session:
        mysql = connectToMySQL(database)
        query = "SELECT * FROM wishes.wishes WHERE wishes.uploaded_by_id = %(me)s;"
        data = {
            "me": session['id']
        }
        wishes = mysql.query_db(query, data)

        for detail in wishes:
            detail["created_at"] = str(detail["created_at"].strftime("%B")) + " " + str(detail["created_at"].day) + ", " + str(detail["created_at"].year)
            
        mysql = connectToMySQL(database)
        query = "SELECT wishes.title, wishes.id, wishes.granted, wishes.created_at, wishes.date_granted, users.first_name FROM wishes JOIN users on users.id = wishes.uploaded_by_id WHERE wishes.granted > 0;"
        data = {
            "sessionid" : session['id']
        }
        granted_wishes = mysql.query_db(query, data)
        print(granted_wishes)
        for detail in granted_wishes:
            detail["date_granted"] = str(detail["date_granted"].strftime("%B")) + " " + str(detail["date_granted"].day) + ", " + str(detail["date_granted"].year)

        return render_template('dashboard.html', wishes=wishes, granted_wishes=granted_wishes)
    else:
        flash("You must be logged in in order to enter this website")
        return redirect("/", )

@app.route("/wishes/new")
def makeawishlink():
    if "id" in session:
        return render_template('makeawish.html')
    else:
        flash("You must be logged in in order to enter this website")
        return redirect("/")

@app.route("/addwish", methods=['POST'])
def addwish():
    if "id" in session:
        session["title"] = request.form['title']
        session["description"] = request.form['description']
        if len(request.form['title']) < 3:
            flash("Please enter a title for your wish")
        if len(request.form['description']) < 3:
            flash("Please describe your wish")
        
        if '_flashes' in session:
            return redirect('/wishes/new')
        if not '_flashes' in session:
            mysql =connectToMySQL(database)
            data = {
                "tit" : request.form["title"],
                "des" : request.form["description"],
                "ubi" : session["id"]
            }
            query ="INSERT INTO wishes.wishes (title, description, uploaded_by_id) VALUES (%(tit)s,%(des)s, %(ubi)s);"
            new_wish = mysql.query_db(query, data)
            return redirect("/dashboard")
    else:
        flash("You must be logged in in order to enter this website")
        return redirect("/")

@app.route("/wishes/<id>/delete")
def delete_wish(id):
    mysql = connectToMySQL(database)
    query = "DELETE FROM wishes WHERE id=%(newid)s"
    data = {
        "newid":id
    }
    info=mysql.query_db(query, data)
    return redirect("/dashboard")

@app.route("/wishes/edit/<id>")
def edit_wish(id):
    if "id" in session:
        mysql = connectToMySQL(database)
        query = "SELECT * FROM wishes.wishes WHERE id = %(newnewid)s"
        data = {
            "newnewid": id
        }
        
        info=mysql.query_db(query, data)
        return render_template("editwish.html", wishes=info)
    else:
        flash("You must be logged in in order to enter this website")
        return redirect("/")

@app.route("/wishes/update/<id>", methods=["POST"])
def update_wish(id):
    if "id" in session:
        if len(request.form['title']) < 1:
                flash("Please enter a title for your job")
        if len(request.form['description']) < 1:
                flash("Please describe your job")
        if '_flashes' in session:
                return redirect(f"/wishes/edit/{id}")
        if not '_flashes' in session.keys():
            mysql =connectToMySQL(database)
            query ="UPDATE wishes.wishes SET title=%(tit)s, description=%(des)s WHERE id = %(newid)s;"

            data = {
                "tit" : request.form["title"],
                "des" : request.form["description"],
                "newid": id
            }
            newly_edited_wish=mysql.query_db(query, data)
            return redirect("/dashboard")
    else:
        flash("You must be logged in in order to enter this website")
        return redirect("/")    

@app.route("/wishes/<id>/addtogranted", methods=["POST"])
def add_to_granted(id):
    if "id" in session:
        mysql = connectToMySQL(database)
        query = "UPDATE wishes.wishes SET granted=%(gra)s, date_granted=NOW() where id = %(wishid)s;"
        data = {
            "gra" : session['id'],
            'wishid': id
            }
        myjobs = mysql.query_db(query, data)
        print(session["id"])
        return redirect('/dashboard')
    else:
        flash("You must be logged in in order to enter this website")
        return redirect("/") 
        
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/cancel")   
def cancel():
    return redirect("/dashboard")



if __name__== "__main__":
    app.run(debug=True)