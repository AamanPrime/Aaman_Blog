import functools
import time

from flask import Flask, render_template, redirect, url_for, flash, abort, request,send_file
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TextField, IntegerField, SelectField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor, CKEditorField
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from sqlalchemy.orm import relationship
import os
import flask_gravatar
import random
from fpdf import FPDF

app = Flask(__name__)
app.config['SECRET_KEY'] = "sadasdadbjd"
ckeditor = CKEditor(app)
Bootstrap(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///posts.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app=app)

gravatar = flask_gravatar.Gravatar(app,
                                   size=50,
                                   rating='g',
                                   default='retro',
                                   force_default=False,
                                   force_lower=False,
                                   use_ssl=False,
                                   base_url=None)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_only(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


# CONFIGURE TABLE


# WTForm
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("E-mail", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")


class CommentForm(FlaskForm):
    comment = CKEditorField("Leave A Comment", validators=[DataRequired()])
    submit = SubmitField("Add Comment")


class ContactForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired()]),
    email = StringField('E-mail', validators=[DataRequired()]),
    message = TextField('Message', validators=[DataRequired()]),
    submit = SubmitField('Submit')


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    comment_author = relationship("User", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


class CalcForm(FlaskForm):
    method = SelectField(label='Function!', choices=['n!', 'ncr', 'npr'])
    n = IntegerField('Input n')
    r = IntegerField('Input r')
    submit = SubmitField('Calculate')


class InvoiceForm(FlaskForm):
    item1 = StringField("Item Description", validators=[DataRequired()])
    qty1 = StringField("Enter Quantity")
    rate1 = StringField("Enter Rate")

    item2 = StringField("Item Description", validators=[DataRequired()])
    qty2 = StringField("Enter Quantity")
    rate2 = StringField("Enter Rate")

    item3 = StringField("Item Description", validators=[DataRequired()])
    qty3 = StringField("Enter Quantity")
    rate3 = StringField("Enter Rate")

    submit = SubmitField("Submit")


class InvoiceFormSubmit(FlaskForm):
    submit = SubmitField("Submit")


db.create_all()


def fact(n):
    result = 1
    for a in range(1, n + 1):
        result = result * a
    return result


def ncr(n, r):
    return fact(n) / (fact(r) * fact(n - r))


def npr(n, r):
    return ncr(n, r) * fact(r)


@app.route('/')
def get_all_posts():
    posts = db.session.query(BlogPost).all()
    posts.reverse()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated,
                           current_user=current_user)


@app.route("/post/<int:index>", methods=['POST', 'GET'])
def show_post(index):
    requested_post = BlogPost.query.get(index)
    form = CommentForm()
    comment = Comment.query.get(index)
    print(comment)
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text=form.comment.data,
                comment_author=current_user,
                parent_post=requested_post
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(
                url_for("show_post", post=requested_post, logged_in=current_user.is_authenticated, form=form,
                        index=index))
        else:
            flash("Registered User are allowed to comment")
            return redirect(url_for('login'))
    return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated, form=form,
                           gravatar=gravatar, current_user=current_user)


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)

@app.route("/aptitude")
def aptitude():
    return render_template("aptitude.html")


@app.route("/contact")
def contact():
    form = ContactForm()
    return render_template("contact.html", logged_in=current_user.is_authenticated, form=form)


@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    form_reg = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Invalid E-mail Please Register")
            return redirect(url_for('register', logged_in=current_user.is_authenticated, form=form_reg))
        elif not check_password_hash(user.password, password):
            flash("Incorrect Password")
            return render_template('login.html', logged_in=current_user.is_authenticated, form=form)
        else:
            login_user(user)
            return redirect(url_for('get_all_posts', logged_in=current_user.is_authenticated))
    return render_template("login.html", logged_in=current_user.is_authenticated, form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts', logged_in=current_user.is_authenticated))


@app.route('/new-post', methods=['POST', 'GET'])
@admin_only
def new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            author=current_user,
            img_url=form.img_url.data,
            body=form.body.data,
            date=datetime.datetime.today().strftime("%d %b, %Y"),
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("get_all_posts", logged_in=current_user.is_authenticated))
    return render_template("make-post.html", form=form, status="New Post", logged_in=current_user.is_authenticated)


@app.route('/edit-post/<post_id>', methods=['POST', 'GET'])
@admin_only
def edit_post(post_id):
    post = db.session.query(BlogPost).get(post_id)
    edit = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit.validate_on_submit():
        post.title = edit.title.data
        post.subtitle = edit.subtitle.data
        post.body = edit.body.data
        db.session.commit()
        return redirect(url_for('get_all_posts'))

    return render_template("make-post.html", form=edit, status="Edit Post", logged_in=current_user.is_authenticated)


@app.route('/delete/<index>', methods=['POST', 'GET'])
@admin_only
def delete(index):
    post_to_delete = db.session.query(BlogPost).get(index)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts', logged_in=current_user.is_authenticated))


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_posts', logged_in=current_user.is_authenticated))
    return render_template('register.html', form=form, logged_in=current_user.is_authenticated)


class GuessForm(FlaskForm):
    guess = IntegerField("Guess Your Number")
    submit = SubmitField('Try Your Luck')


@app.route('/game', methods=['POST', 'GET'])
def home():
    rn_num = random.randint(1, 10)
    print(rn_num)
    form = GuessForm()
    if form.validate_on_submit():
        guess = form.guess.data
        if int(guess) == rn_num:
            return render_template('index2.html', status='Congrulations, You Found It........',
                                   img="https://media0.giphy.com/media/hVb4xkJTGrtyaEBi6L/giphy.gif?cid=790b7611807e66a71391a0580e02ebc94b4142607d40da81&rid=giphy.gif&ct=g",
                                   form=form)
        elif int(guess) > rn_num:
            return render_template('index2.html', status='Please guess small number than this',
                                   img='https://media3.giphy.com/media/NsBdv1HXGSgUJFLJPC/giphy.gif?cid=ecf05e47801n9tpmpzaspxdmxedar2oai5f8w3i6c2aep7s4&rid=giphy.gif&ct=g',
                                   form=form)
        elif int(guess) < rn_num:
            return render_template('index2.html', status='Please guess large number than this',
                                   img='https://media2.giphy.com/media/j5bsZqX1KTKngMyu90/giphy.gif?cid=ecf05e47iqxy0m7j3t9v9faws95u4n16tefm9cb9tr6w50s6&rid=giphy.gif&ct=g',
                                   form=form)
    return render_template('index2.html', form=form, img='https://i.giphy.com/media/UDU4oUJIHDJgQ/giphy.webp',
                           status='To Play this game guess a number between 1 and 10')


@app.route('/calculator', methods=['POST', 'GET'])
def calc():
    form = CalcForm()

    if form.validate_on_submit():
        m = form.method.data
        n = form.n.data
        r = form.r.data
        if m == 'n!':
            result = fact(n)
            return render_template('cal.html', form=form, result=result, ans=True)
        elif m == 'ncr':
            result = ncr(n, r)
            return render_template('cal.html', form=form, result=result, ans=True)
        elif m == 'npr':
            result = npr(n, r)
            return render_template('cal.html', form=form, result=result, ans=True)
    return render_template('cal.html', form=form, ans=False)


@app.route('/invoice', methods=['GET', 'POST'])
def bill():
    width = 547
    height = 794
    if request.method == 'POST':
        projectname = request.form.get('projectname')
        projectaddress = request.form.get('projectaddress')
        projectmanager = request.form.get('projectmanager')
        date = request.form.get('date')
        pdf = FPDF('P', 'pt', 'A4')
        pdf.add_page()

        # Header
        pdf.rect(24, 24, width, height)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('arial', 'B', 12)
        pdf.cell(w=width * 0.49, h=10, txt='PAN NO. QZLPS5488G', align="L", ln=0)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('arial', 'B', 12)
        pdf.cell(w=width * 0.49, h=10, txt='Phone No. +91-9717317286', align="R", ln=1)

        pdf.set_font('arial', 'B', 28)
        pdf.set_text_color(0, 160, 56)

        pdf.cell(w=width * 0.72, h=50, txt="AAMAN SHEIKH", border=0, align="R", ln=1)
        pdf.set_font('arial', 'B', 15)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(w=width, h=5, txt="DEVELOPER", border=0, align="C", ln=1)
        pdf.cell(w=width, h=35, txt="412 STREET 7 B BLOCK ROSHAN NAGAR FARIDABAD", border=0, align='C', ln=1)
        pdf.rect(50, 125, 497, 1, style="f")

        # INFORMATION
        pdf.set_font('arial', 'B', 11)
        pdf.cell(w=100, h=40, txt=" ", border=0, align="c", ln=1)
        pdf.cell(w=22, h=15, txt=" ", ln=0)
        pdf.cell(w=100, h=25, txt="PROJECT NAME", border=1, align="C", ln=0)
        pdf.cell(w=247, h=25, txt=projectname.upper(), border=1, align="C", ln=0)
        pdf.cell(w=50, h=25, txt="DATE", border=1, align="C", ln=0)
        pdf.cell(w=100, h=25, txt=date, border=1, align="C", ln=1)
        pdf.cell(w=22, h=15, txt=" ", ln=0)
        pdf.cell(w=125, h=25, txt="PROJECT ADDRESS", border=1, align="C", ln=0)
        pdf.cell(w=372, h=25, txt=projectaddress.upper(), border=1, align="C", ln=1)
        pdf.cell(w=22, h=15, txt=" ", ln=0)
        pdf.cell(w=125, h=25, txt="PROJECT MANAGER", border=1, align="C", ln=0)
        pdf.cell(w=372, h=25, txt=projectmanager.upper(), border=1, align="C", ln=1)

        # ITEMS HEADING
        pdf.cell(w=100, h=20, txt=" ", border=0, align="C", ln=1)
        pdf.cell(w=22, h=15, txt=" ", ln=0)
        pdf.cell(w=32, h=25, txt="S.NO", border=1, align="C", ln=0)
        pdf.cell(w=250, h=25, txt="ITEM DESCRIPTION", border=1, align="C", ln=0)
        pdf.cell(w=70, h=25, txt="QTY.(SQFT)", border=1, align="C", ln=0)
        pdf.cell(w=50, h=25, txt="RATE", border=1, align="C", ln=0)
        pdf.cell(w=95, h=25, txt="AMOUNT", border=1, align="C", ln=0)

        items = [(request.form.get(f'item{i}'), request.form.get(f'qty{i}'), request.form.get(f'rate{i}')) for i in
                 range(1, 9)]
        # ITEMS
        total = 0
        for i in range(len(items)):
            pdf.set_font('arial', 'B', 10)
            amount = ''
            if len(items[i][1].strip()) != 0 and len(items[i][1].strip()) != 0:
                amount = float(float(items[i][1]) * float(items[i][2]))
            pdf.cell(w=100, h=20, txt=" ", border=0, align="C", ln=1)
            pdf.cell(w=22, h=15, txt=" ", ln=0)
            if len(items[i][1].strip()) != 0 and len(items[i][1].strip()) != 0:
                pdf.cell(w=32, h=25, txt=str(i + 1), border="LR", align="C", ln=0)
            else:
                pdf.cell(w=32, h=25, txt="", border="LR", align="C", ln=0)
            pdf.cell(w=250, h=25, txt=items[i][0].upper(), border="LR", align="C", ln=0)
            pdf.cell(w=70, h=25, txt=items[i][1], border="LR", align="C", ln=0)
            pdf.cell(w=50, h=25, txt=items[i][2], border="LR", align="C", ln=0)
            pdf.cell(w=95, h=25, txt=f"{amount}", border="LR", align="C", ln=0)
            pdf.cell(w=100, h=20, txt=" ", border=0, align="C", ln=1)
            pdf.cell(w=22, h=15, txt=" ", ln=0)
            pdf.cell(w=32, h=20, txt="", border="LR", align="C", ln=0)
            pdf.cell(w=250, h=20, txt="", border="LR", align="C", ln=0)
            pdf.cell(w=70, h=20, txt="", border="LR", align="C", ln=0)
            pdf.cell(w=50, h=20, txt="", border="LR", align="C", ln=0)
            pdf.cell(w=95, h=20, txt="", border="LR", align="C", ln=0)
            if (type(amount) == float):
                total += amount

        # TOTAL
        print(total)
        pdf.cell(w=100, h=20, txt=" ", border=0, align="C", ln=1)
        pdf.cell(w=22, h=15, txt=" ", ln=0)
        pdf.cell(w=282, h=50, txt="", border=1, ln=0)
        pdf.cell(w=120, h=50, txt="TOTAL", border=1, ln=0, align="C")
        pdf.cell(w=95, h=50, txt=f"{total}", border=1, ln=1, align="C")

        # FOOTER
        pdf.cell(w=100, h=130, txt=" ", border=0, align="C", ln=1)

        pdf.cell(w=100, h=1, txt="E-mail:- aamanprime@gmail.com", border=0, align="c", ln=1)

        pdf.output(f'templates/{projectname}.pdf')

        return send_file(f"templates/{projectname}.pdf")

    return render_template('bill.html')


if __name__ == "__main__":
    app.run(debug=True)
