import functools
from flask import Flask, render_template, redirect, url_for, flash, abort
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


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
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
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated, current_user=current_user)


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
    return render_template('cal.html', form= form, ans=False)  
@app.route('/weblinks')
def website():
    list = ['fonts.googleapis.com', 'facebook.com', 'twitter.com', 'google.com', 'youtube.com', 's.w.org',
            'instagram.com', 'googletagmanager.com', 'linkedin.com', 'ajax.googleapis.com', 'plus.google.com',
            'gmpg.org', 'pinterest.com', 'fonts.gstatic.com', 'wordpress.org', 'en.wikipedia.org', 'youtu.be',
            'maps.google.com', 'itunes.apple.com', 'github.com', 'bit.ly', 'play.google.com', 'goo.gl',
            'docs.google.com', 'cdnjs.cloudflare.com', 'vimeo.com', 'support.google.com', 'google-analytics.com',
            'maps.googleapis.com', 'flickr.com', 'vk.com', 't.co', 'reddit.com', 'amazon.com', 'medium.com',
            'sites.google.com', 'drive.google.com', 'creativecommons.org', 'microsoft.com', 'developers.google.com',
            'adobe.com', 'soundcloud.com', 'theguardian.com', 'apis.google.com', 'ec.europa.eu',
            'lh3.googleusercontent.com', 'chrome.google.com', 'cloudflare.com', 'nytimes.com',
            'maxcdn.bootstrapcdn.com', 'support.microsoft.com', 'blogger.com', 'forbes.com', 's3.amazonaws.com',
            'code.jquery.com', 'dropbox.com', 'translate.google.com', 'paypal.com', 'apps.apple.com', 'tinyurl.com',
            'etsy.com', 'theatlantic.com', 'm.facebook.com', 'archive.org', 'amzn.to', 'cnn.com', 'policies.google.com',
            'commons.wikimedia.org', 'issuu.com', 'i.imgur.com', 'wordpress.com', 'wp.me', 'businessinsider.com',
            'yelp.com', 'mail.google.com', 'support.apple.com', 't.me', 'apple.com', 'washingtonpost.com', 'bbc.com',
            'gstatic.com', 'imgur.com', 'amazon.de', 'bbc.co.uk', 'googleads.g.doubleclick.net', 'mozilla.org',
            'eventbrite.com', 'slideshare.net', 'w3.org', 'forms.gle', 'platform.twitter.com', 'accounts.google.com',
            'telegraph.co.uk', 'messenger.com', 'web.archive.org', 'secure.gravatar.com', 'usatoday.com',
            'huffingtonpost.com', 'stackoverflow.com', 'fb.com', 'npr.org', 'techcrunch.com', 'wired.com', 'eepurl.com',
            'reuters.com', 'arxiv.org', 'i0.wp.com', 'finance.yahoo.com', 'player.vimeo.com', 'amazon.fr',
            'developer.mozilla.org', 'tumblr.com', 'cnbc.com', 'booking.com', 'zoom.us', 'tools.google.com', 'wa.me',
            'paypal.me', 'slack.com', 'adwords.google.com', 'independent.co.uk', 'discord.gg', 'open.spotify.com',
            'tripadvisor.com', 'gsuite.google.com', 'behance.net', 'thinkwithgoogle.com', 'who.int', 'cloud.google.com',
            'calendar.google.com', 'ibm.com', 'analytics.google.com', 'lh5.googleusercontent.com', 'docs.microsoft.com',
            'groups.google.com', 'mixcloud.com', 'google.co.in', 'latimes.com', 'gist.github.com',
            'download.macromedia.com', 'dailymail.co.uk', 'myaccount.google.com', 'line.me', 'unsplash.com',
            'addons.mozilla.org', 'msdn.microsoft.com', 'storage.googleapis.com', 'pagead2.googlesyndication.com',
            'cdn.jsdelivr.net', 'g.co', 'meetup.com', 'bloomberg.com', 'books.google.com', 'vox.com', 'imdb.com',
            'arstechnica.com', 'support.mozilla.org', 'amazon.co.uk', 'statista.com', 'google.ca', 'nbcnews.com',
            'steemit.com', 'upload.wikimedia.org', 'aws.amazon.com', 'amazon.co.jp', 'w3schools.com', 'weibo.com',
            'twitch.tv', 'moz.com', 'drupal.org', 'nypost.com', 'fr.wikipedia.org', 'ebay.com', 'sourceforge.net',
            'godaddy.com', 'ncbi.nlm.nih.gov', 'wsj.com', 'thenextweb.com', 'cdc.gov', 'photos.google.com',
            'trends.google.com', 'opera.com', 'ftc.gov', 'j.mp', 'about.me', 'gov.uk', 'i.ytimg.com', 'squareup.com',
            'google.co.uk', 'buzzfeed.com', 'developer.apple.com', 'pixabay.com', 'quora.com', 'cnet.com',
            'google.com.au', 'myspace.com', 'theglobeandmail.com', 'shopify.com', 'whitehouse.gov',
            'marketingplatform.google.com', 'kickstarter.com', 'freelancer.com', 'evernote.com', 'gmail.com',
            'static.wixstatic.com', 'fortune.com', 'wix.com', 'dailymotion.com', 'goodreads.com', 'podcasts.google.com',
            'google.co.jp', 'support.cloudflare.com', 'surveymonkey.com', 'cbsnews.com', 'entrepreneur.com', 'bing.com',
            'engadget.com', 'lh4.googleusercontent.com', 'tandfonline.com', 'cargocollective.com', 'join.slack.com',
            'api.whatsapp.com', 'shutterstock.com', 'pbs.twimg.com', 'blog.google', 'ads.google.com', 'time.com',
            'lifehacker.com', 'patreon.com', 'scribd.com', 'lh6.googleusercontent.com', 'feeds.feedburner.com',
            'trello.com', 'ted.com', 'helpx.adobe.com', 'researchgate.net', 'fda.gov', 'instructables.com', 'google.de',
            'digitalocean.com', 'dribbble.com', 'ssl.gstatic.com', 'variety.com', 'indiegogo.com', 'salesforce.com',
            'uk.linkedin.com', 'nasa.gov', 'codepen.io', 'newyorker.com', 'abcnews.go.com', 'snapchat.com',
            'googleadservices.com', 'sciencedirect.com', 'ft.com', 'nature.com', 'gofundme.com', '500px.com', 'qz.com',
            'dl.dropboxusercontent.com', 'store.steampowered.com', 'webmasters.googleblog.com', 'podcasts.apple.com',
            'oracle.com', 'm.youtube.com', 'gartner.com', 'web.facebook.com', 'blogs.msdn.com', 'mailchi.mp',
            'digg.com', 'skype.com', 'periscope.tv', 'google.com.br', 'googleblog.blogspot.com', 'de.wikipedia.org',
            'search.google.com', 'npmjs.com', 'motherboard.vice.com', 'aboutads.info', 'pexels.com', 'sxsw.com',
            'fiverr.com', 'code.google.com', 'cbc.ca', 'venturebeat.com', 'hangouts.google.com', 'mashable.com',
            'upwork.com', 'bitly.com', 'music.apple.com', 'loc.gov', 'news.google.com', 'spotify.com', 'netflix.com',
            'hbr.org', 'pbs.org', 'stumbleupon.com', 'walmart.com', 'foursquare.com', 'amazon.ca', 'tiny.cc',
            'services.google.com', 'xkcd.com', 'target.com', 'developers.facebook.com', 'nginx.com', 'canva.com',
            's7.addthis.com', 'elmundo.es', 'i2.wp.com', 'gizmodo.com', 'expedia.com', 'picasaweb.google.com',
            'money.cnn.com', 'timesofindia.indiatimes.com', 'yandex.ru', 'vice.com', 'de-de.facebook.com',
            'pastebin.com', 'samsung.com', 'rt.com', 'ifttt.com', 'dev.mysql.com', 'giphy.com', 'use.fontawesome.com',
            'houzz.com', 'developer.android.com', 'wikipedia.org', 'speakerdeck.com', 'productforums.google.com',
            'digitaltrends.com', 'steamcommunity.com', 'canada.ca', 'networkadvertising.org', 'linktr.ee',
            'calendly.com', 'lg.com', 'yahoo.com', 'last.fm', 'amazon.es', 'businesswire.com', 'deezer.com',
            'dx.doi.org', 'udemy.com', 'edition.cnn.com', '1.bp.blogspot.com', 'l.facebook.com', 'dl.dropbox.com',
            'store.google.com', 'gumroad.com', 'azure.microsoft.com', 'i1.wp.com', 'ubuntu.com', 'google.ru',
            'makeuseof.com', 'raw.githubusercontent.com', 'airbnb.com', 'bluehost.com', 'deviantart.com',
            'pewresearch.org', 'google.cn', 'profiles.google.com', 'login.microsoftonline.com', 'google.nl',
            'google.es', 'fastcompany.com', 'is.gd', 'telegram.me', 'mediafire.com', 'themeforest.net',
            'openstreetmap.org', 'pewinternet.org', 'photos.app.goo.gl', 'buff.ly', 'events.google.com',
            'link.springer.com', 'bizjournals.com', 'residentadvisor.net', 'golang.org', 'vogue.com',
            's3-eu-west-1.amazonaws.com', 'boardgamegeek.com', 'un.org', 'i.redd.it', 'ad.doubleclick.net', 'ow.ly',
            'get.google.com', 'pt.slideshare.net', 'buffer.com', 'mozilla.com', 'chromium.org', 'patheos.com',
            'ancestry.com', 'youtube-nocookie.com', 'barnesandnoble.com', 'amzn.com', 'hulu.com', 'greenpeace.org',
            'spiegel.de', 'apps.facebook.com', 'census.gov', 'app.box.com', 'windows.microsoft.com', 'yandex.com',
            'sketchfab.com', 'avvo.com', 'searchengineland.com', 'shareasale.com', 'abc.net.au', 'trustpilot.com',
            'plaza.rakuten.co.jp', 'marriott.com', 'amazon.it', 'ca.linkedin.com', 'uber.com', 'coursera.org',
            'adage.com', 'foxnews.com', 'flic.kr', 'developer.chrome.com', 'pl.wikipedia.org', 'change.org',
            'spreaker.com', 'filezilla-project.org', 'flipboard.com', 'pcworld.com', 'news.yahoo.com', 'pitchfork.com',
            'weforum.org', 'istockphoto.com', '9to5mac.com', '1drv.ms', 'uspto.gov', 'irs.gov', 'copyblogger.com',
            'example.com', 'maps.google.co.jp', 'fonts.google.com', 'siteground.com', 'sony.net', 'ja.wikipedia.org',
            'creativemarket.com', 'smithsonianmag.com', 'mobile.twitter.com', 'acm.org', 'accenture.com', 'git-scm.com',
            'bbb.org', 'cdn.shopify.com', 'schema.org', 'psychologytoday.com', 'redcross.org', 'nodejs.org',
            'europa.eu', 'ameblo.jp', 'gitlab.com', 'sciencemag.org', 'hollywoodreporter.com', 'freshbooks.com',
            'heise.de', 'chicagotribune.com', 'epa.gov', 'anchor.fm', 'telegram.org', 'ikea.com', 'bloglovin.com',
            'eventbrite.co.uk', 'googlewebmastercentral.blogspot.com', 'huffpost.com', 'weebly.com', 'producthunt.com',
            'google.fr', 'click.linksynergy.com', 'vanityfair.com', 'diigo.com', 'about.fb.com', 'ouest-france.fr',
            'namecheap.com', 'codecanyon.net', 'appstore.com', 'tools.ietf.org', 'rockpapershotgun.com', 'columbia.edu',
            'constantcontact.com', 'webmd.com', 'eur-lex.europa.eu', 'aliexpress.com', 'business.facebook.com',
            'material.io', 'neilpatel.com', 'discordapp.com', 'm.me', 'design.google', 'francetvinfo.fr',
            'slashgear.com', '4shared.com', 'python.org', 'amazon.com.au', 'storify.com', 'elegantthemes.com',
            'europe1.fr', 'pwc.com', 'activecampaign.com', 'freepik.com', 'ravelry.com', 'apnews.com', 'propublica.org',
            'smugmug.com', 'inc.com', 'google.it', 'zazzle.com', 'dol.gov', 'scoop.it', 'bit.do', 'yadi.sk',
            'eclipse.org', 'economist.com', 'xing.com', 'hbo.com', 'nationalgeographic.com', 'jetbrains.com',
            'iconfinder.com', 'cafepress.com', 'strava.com', 'es.wikipedia.org', 'kiva.org', 'doi.org',
            'boredpanda.com', 'justgiving.com', 'pinterest.ca', 'stats.wp.com', 'zdnet.com', 'sproutsocial.com',
            'rebrand.ly', 'ranker.com', 'a.co', 'waze.com', 'nydailynews.com', 'marketwatch.com', 'mailchimp.com',
            'livescience.com', 'flaticon.com', 'ilpost.it', 'connect.facebook.net', '4.bp.blogspot.com',
            'maps.google.co.nz', 's0.wp.com', 'amazon.com.br', 'ustream.tv', 'lulu.com', 'socialmediatoday.com',
            'market.android.com', 'rollingstone.com', 'journals.sagepub.com', 'zillow.com', 'xinhuanet.com',
            'affiliate-program.amazon.com', 'politico.com', 'pnas.org', 'laughingsquid.com', 'access.redhat.com',
            's.ytimg.com', 'it.linkedin.com', 'dashlane.com', 'copyright.gov', 'news.bbc.co.uk', 'mentalfloss.com',
            'zeit.de', 'google.cz', 'artsandculture.google.com', 'startnext.com', 'launchpad.net', 'lemonde.fr',
            'sciencedaily.com', 'edx.org', 'smashwords.com', 'philips.co.uk', 'smile.amazon.com', 'intel.com',
            'livestream.com', 'brookings.edu', 'thehill.com', 'popsci.com', 'blog.us.playstation.com', 'fb.me',
            'academic.oup.com', 'php.net', 'wetransfer.com', 'blog.livedoor.jp', 'amazon.in', 'families.google.com',
            'obsproject.com', 't.qq.com', 'android.com', 'blogs.windows.com', 'hostgator.com', 'google.gr',
            'theverge.com', 'aub.edu.lb', 'digiday.com', 'gimp.org', 'treasury.gov', 'geocities.com', 'healthline.com',
            '3.bp.blogspot.com', 'coinbase.com', 'gnu.org', 'abc.com', 'aljazeera.com', 'getresponse.com', 'dev.to',
            'thesun.co.uk', 'lynda.com', 'sellfy.com', 'prnt.sc', 'help.ubuntu.com', 'whatsapp.com', 'www8.hp.com',
            'notion.so', 'vmware.com', 'kraken.com', 'vine.co', 'marthastewart.com', 'discord.me', 'dailycaller.com',
            'mega.nz', 'media.giphy.com', 'flavors.me', 'blip.tv', 'prntscr.com', 'journals.plos.org', 'gravatar.com',
            'discogs.com', 'europarl.europa.eu', 'redhat.com', 'bugs.chromium.org', 'vanmiubeauty.com', 'metro.co.uk',
            'google.ie', 'relapse.com', 'earth.google.com', 'bandcamp.com', 'br.linkedin.com', 'gopro.com', 't.ly',
            'get.adobe.com', 'news.mit.edu', 'billboard.com', 'britannica.com', 'onlinelibrary.wiley.com',
            'techsmith.com', 'sfgate.com', 'redbubble.com', 'kstatic.googleusercontent.com', 'repubblica.it',
            'disqus.com', 'khanacademy.org', 'skfb.ly', 'androidauthority.com', 'accessify.com', 'tensorflow.org',
            'chrisjdavis.org', 'box.net', 'poetryfoundation.org', 'law.cornell.edu', 'penguinrandomhouse.com',
            'refinery29.com', 'starwars.com', 'fr.linkedin.com', 'video.google.com', 'prnewswire.com', 'springer.com',
            'zalo.me', 'reverbnation.com', 'getpocket.com', 'webdesign.about.com', 'goo.gle', 'note.mu',
            'thetimes.co.uk', 'fao.org', 'bol.com', 'yoursite.com', 'sophos.com', 'automattic.com', 'podbean.com',
            'sublimetext.com', 'archives.gov', 'vizio.com', 'thelancet.com', 'guardian.co.uk',
            'news.nationalgeographic.com', 'tunein.com', 'stitcher.com', 'coinmarketcap.com', 'amnestyusa.org',
            'docs.wixstatic.com', 'cambridge.org', 'validator.w3.org', 'asus.com', 'problogger.net', 'worldbank.org',
            'ticketportal.cz', 'dw.com', 'static.googleusercontent.com', 'www-01.ibm.com', 'business.google.com',
            'es.linkedin.com', 'songkick.com', 'adweek.com', 'lifehack.org', 'apple.co', 'sutterhealth.org',
            'globalnews.ca', 'breitbart.com', 'thumbtack.com', 'eff.org', 'snopes.com', 'crowdrise.com', 'hkrsa.asia',
            'metmuseum.org', 'pixlr.com', 'institutvajrayogini.fr', 'rhtlbn.mosgorcredit.ru', 'itchyfeetonthecheap.com',
            'reacts.ru', 'db.tt', 'udacity.com', 'we.tl', 'blogtalkradio.com', 'audacityteam.org', 'youcaring.com',
            'hp.com', '0.gravatar.com', 'health.harvard.edu', 'meta.wikimedia.org', 'google.ch', 'nhs.uk', 'mixi.jp',
            'symfony.com', 'business.linkedin.com', 'mtv.com', '1.gravatar.com', 'cyber.law.harvard.edu',
            'bitcointalk.org', 'esa.int', 'slate.com', 'oecd.org', 'raspberrypi.org', 'sfexaminer.com',
            'warriorforum.com', 'g.page', 'bhphotovideo.com', 'axios.com', 'pinterest.co.uk', 'unesco.org', 'msn.com',
            'code.visualstudio.com', 'netbeans.org', 'blockchain.info', 'untappd.com', 'espn.com', 'cbs.com',
            'michigan.gov', 'oprah.com', 'ok.ru', 'mhlw.go.jp', 'newegg.com', '2.bp.blogspot.com', 'pipes.yahoo.com',
            'themarthablog.com', 'yummly.com', 'bitpay.com', 'buymeacoffee.com', 'deepl.com',
            'blogs.scientificamerican.com', 'audible.com', 'bitbucket.org', 'it.wikipedia.org', 'in.linkedin.com',
            'cse.google.com', 'use.typekit.net', 'ru.wikipedia.org', 'faz.net', 'adf.ly', 'cancerresearchuk.org',
            'moma.org', 'bigthink.com', 'bandsintown.com', 'addthis.com', 'support.office.com', 'upi.com',
            'zen.yandex.ru', 'collegehumor.com', 'lefigaro.fr', 'gplus.to', 'themify.me', 'rtve.es', 'nba.com',
            'myfitnesspal.com', 'chris.pirillo.com', 'eonline.com', 'science.sciencemag.org', 'ietf.org', 'ko-fi.com',
            'otto.de', 'tkqlhce.com', 'unity3d.com', 'blog.naver.com', 'scratch.mit.edu', 'freewebs.com', 'drift.com',
            'postmates.com', 'geek.com', 'geocities.jp', 'beian.gov.cn', 'meet.google.com', 'flattr.com', 'webroot.com',
            'thoughtcatalog.com', 'google.pl', 'seroundtable.com', 'checkpoint.com', 'form.jotform.com', 'xbox.com',
            'infusionsoft.com', 'g1.globo.com', 'capterra.com', 'ea.com', 'hawaii.edu', 'stock.adobe.com', 'osha.gov',
            'buzzfeednews.com', 'jstor.org', 'adssettings.google.com', 'iheart.com', 'en-gb.facebook.com',
            'foodnetwork.com', 'eventim.de', 'economictimes.indiatimes.com', 'presseportal.de', 'google.se',
            'skillshare.com', 'puu.sh', 'examiner.com', 'stripe.com', 'firstdata.com', 'en.advertisercommunity.com',
            'download.microsoft.com', 's-media-cache-ak0.pinimg.com', 'ctt.ec', 'cia.gov', 'docker.com',
            'homedepot.com', 'humblebundle.com', 'chiark.greenend.org.uk', 'pandora.com', 'google.co.za', 'payhip.com',
            'thingiverse.com', 'inkscape.org', 'adobe.ly', 'css-tricks.com', 'ja-jp.facebook.com', 'jamanetwork.com',
            'maps.gstatic.com', 'wattpad.com', 'chase.com', 'cisco.com', 'bmj.com', 'louvre.fr', 'aclu.org',
            'squarespace.com', 'gum.co', 'idealo.de', 'imore.com', 'rakuten.com', 'fbi.gov', 'united.com', 'google.pt',
            'event.on24.com', 'nejm.org', 'colorado.edu', 'franchising.com', 'logitech.com', 'redbull.com', 'tf1.fr',
            'keep.google.com', 'hostinger.com', 'nbc.com', 'stats.g.doubleclick.net', 'ign.com', 'blog.hubspot.com',
            '1.envato.market', 'accessdata.fda.gov', 'google.be', 'help.apple.com', 'technorati.com', 'pond5.com',
            'ucl.ac.uk', 'a2hosting.com', 'amzn.asia', 'nicovideo.jp', 'indiewire.com', 'mp.weixin.qq.com',
            'codeproject.com', '1.usa.gov', 'gleam.io', 'space.com', 'gitter.im', 'lh5.ggpht.com', 'leparisien.fr',
            'kotaku.com', 'img.youtube.com', 'huffingtonpost.co.uk', 'agoda.com', 'flow.microsoft.com', 'chronicle.com',
            'createspace.com', 'lh3.ggpht.com', 'verizon.com', 'teespring.com', 'data.worldbank.org', 'blog.goo.ne.jp',
            'kobo.com', 'globalsign.com', 'money.yandex.ru', 'animoto.com', 'google.co.nz', 'privacy.microsoft.com',
            'online.wsj.com', 'patft.uspto.gov', 'rottentomatoes.com', 'cell.com', 'de.linkedin.com', 'health.com',
            'geni.us', 'news.harvard.edu', 'lesechos.fr', 'fas.org', 'smashingmagazine.com', '7-zip.org', 'realvnc.com',
            'news.discovery.com', 'mlb.com', 'autodesk.com', 'popularmechanics.com', 'forms.office.com', 'rdio.com',
            'sendspace.com', 'synology.com', 'angelfire.com', 'france24.com', 'us.battle.net', 'stjude.org',
            'denverpost.com', 'japantimes.co.jp', 'stocktwits.com', 'blogs.adobe.com', 'envato.com', 'airtable.com',
            'ticketmaster.com', 'ocw.mit.edu', 'whc.unesco.org', 'neh.gov', 'purl.org', 'nfl.com', 'monster.com',
            'codex.wordpress.org', 'dafont.com', 'tesla.com', 'lmgtfy.com', 'olympic.org', 'technet.microsoft.com',
            'baidu.com', 'desktop.github.com', 'overcast.fm', 'allmusic.com', 'cdbaby.com', 'vsco.co', 'nvidia.com',
            'stadt-bremerhaven.de', 'faa.gov', 'blogs.yahoo.co.jp', 'bild.de', 'lenovo.com', 'funnyordie.com',
            'ssl.google-analytics.com', 'abebooks.com', 'spectrum.ieee.org', 'thinkgeek.com', 'snip.ly', 'pixiv.net',
            'buzzsprout.com', 'patents.google.com', 'orcid.org', 'cdn.ampproject.org', 'blog.feedspot.com',
            'vr.google.com', 'opinionator.blogs.nytimes.com', 'ericsson.com']
    web = random.choice(list)
    return render_template('web.html',weblink=web)  
if __name__ == "__main__":
    app.run(debug=True)
