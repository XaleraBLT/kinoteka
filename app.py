import json
import os
import random
from urllib.parse import unquote

from flask import Flask
from flask import render_template, request, json, redirect, url_for, flash
from flask_login import LoginManager
from flask_login import UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sentence_transformers import SentenceTransformer

import recomend_film
from search import find_best_match

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    film_title = db.Column(db.String, nullable=False)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    film_title = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)


class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())


class ViewingHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    film_title = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())


def load_films():
    with open('./instance/films.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)["movies"]
    films = {}
    for item in raw_data:
        title = item.get("title", "").strip()
        if title:
            films[title] = {key: item.get(key, "") for key in item}
    return films


films_db = load_films()


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    film_title = db.Column(db.String, nullable=False)
    rating = db.Column(db.Integer, nullable=False)


def get_random_films(films, count=8):
    return dict(random.sample(list(films.items()), count))


@app.route('/')
def home():
    if current_user.is_authenticated:
        rec_films = recomend_film.get_recommendation(current_user.id, 20)
        return render_template('index.html', films=rec_films)
    else:
        return render_template('index.html', films=None)



@app.route('/all')
def all_films():
    return render_template('all.html', films=films_db)


@app.route('/film/<string:original_title>')
def film_details(original_title):
    original_title = unquote(original_title)
    film = next((data for title, data in films_db.items()
                 if data["original_title"] == original_title), None)
    if film:
        if current_user.is_authenticated:
            # Save viewing history for the user
            new_viewing = ViewingHistory(user_id=current_user.id, film_title=original_title)
            db.session.add(new_viewing)
            db.session.commit()
        likes = Like.query.filter_by(film_title=original_title).count()
        reviews = Review.query.filter_by(film_title=original_title).all()
        user_rating = None
        if current_user.is_authenticated:
            user_rating_obj = Rating.query.filter_by(user_id=current_user.id, film_title=original_title).first()
            user_rating = user_rating_obj.rating if user_rating_obj else None
        average_rating = db.session.query(db.func.avg(Rating.rating)).filter_by(film_title=original_title).scalar()
        average_rating = round(average_rating, 1) if average_rating else "Нет оценок"
        return render_template('film.html', film=film, likes=likes, reviews=reviews, user_rating=user_rating,
                               average_rating=average_rating)
    else:
        return "Фильм не найден", 404


@app.route('/like/<string:film_title>')
@login_required
def like_film(film_title):
    like = Like.query.filter_by(user_id=current_user.id, film_title=film_title).first()
    if not like:
        new_like = Like(user_id=current_user.id, film_title=film_title)
        db.session.add(new_like)
        db.session.commit()
    return redirect(url_for('film_details', original_title=film_title))


@app.route('/review/<string:film_title>', methods=['GET', 'POST'])
@login_required
def add_review(film_title):
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_review = Review(user_id=current_user.id, film_title=film_title, title=title, content=content)
        db.session.add(new_review)
        db.session.commit()
        return redirect(url_for('film_details', original_title=film_title))
    return render_template('add_review.html', film_title=film_title)


@app.route('/rate/<string:film_title>', methods=['POST'])
@login_required
def rate_film(film_title):
    rating_value = request.form.get('rating', type=int)
    if rating_value < 1 or rating_value > 10:
        flash("Оценка должна быть от 1 до 10")
        return redirect(url_for('film_details', original_title=film_title))
    existing_rating = Rating.query.filter_by(user_id=current_user.id, film_title=film_title).first()
    if existing_rating:
        existing_rating.rating = rating_value
    else:
        new_rating = Rating(user_id=current_user.id, film_title=film_title, rating=rating_value)
        db.session.add(new_rating)
    db.session.commit()
    return redirect(url_for('film_details', original_title=film_title))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Пользователь уже существует')
            return redirect(url_for('register'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template('register.html')


@app.route('/search', methods=['GET'])
def search():

    filters = {
        "years": [int(y) for y in request.args.getlist('year') if y.isdigit()],
        "genres": request.args.getlist('genre')
    }

    query = request.args.get('query', '').strip()

    print(query)

    results = []

    if query.startswith("@ai"):
        print(query)
        query = query.replace('@ai', '').strip()

        if current_user.is_authenticated:
            # Save search history for the user
            new_search = SearchHistory(user_id=current_user.id, query=query)
            db.session.add(new_search)
            db.session.commit()

        results = find_best_match(query, k=20, filters=filters)
    else:
        query_lower = query.lower()
        results = [
            film for film in films_db.values() if query_lower in film.get('title', '').lower()
        ]
    return render_template('search.html', results=results, query=query, selected_year=filters["years"],
                           selected_genre=filters["genres"])


@app.route('/filter')
def filter_films():
    query = request.args.get('query', '').strip()
    filters = {
        "years": [int(y) for y in request.args.getlist('year') if y.isdigit()],
        "genres": [genre.lower() for genre in request.args.getlist('genre')]
    }
    if query.startswith("@ai"):
        query.replace("@ai", "")
        results = find_best_match(query, k=20, filters=filters)


        if current_user.is_authenticated:
            # Save search history for the user
            new_search = SearchHistory(user_id=current_user.id, query=query)
            db.session.add(new_search)
            db.session.commit()

    else:
        filtered_movies = films_db
        if filters:
            filtered_movies = []
            for movie in films_db.values():
                matches_genre = not filters.get("genres") or any(
                    genre in movie.get("genres", []) for genre in filters["genres"]
                )
                matches_year = not filters.get("years") or movie.get("release_date", "").split("-")[0] in map(str,
                                                                                                              filters[
                                                                                                                  "years"])

                if matches_genre and matches_year:
                    filtered_movies.append(movie)
        results = [
            film for film in filtered_movies
            if query.lower() in film.get('title', '').lower()
        ]
    return render_template('search.html', results=results, query=query, selected_year=[str(year) for year in filters["years"]],
                           selected_genre=[genre.capitalize() for genre in filters["genres"]])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Неверное имя пользователя или пароль')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == '__main__':
    if not os.path.exists('site.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
